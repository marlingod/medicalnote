import json
import logging
from enum import Enum

from django.conf import settings

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    CLAUDE = "claude"
    GEMINI = "gemini"


# ── Prompts ────────────────────────────────────────────────────────────────────

SOAP_SYSTEM_PROMPT = """You are a medical documentation assistant. Given a clinical transcript or note text, produce a structured SOAP note as JSON.

Output format (strict JSON, no markdown):
{
  "subjective": "...",
  "objective": "...",
  "assessment": "...",
  "plan": "...",
  "icd10_codes": ["..."],
  "cpt_codes": ["..."]
}"""

SUMMARY_SYSTEM_PROMPT = """Convert the following clinical SOAP note into a patient-friendly summary.

Rules:
- Write at a {reading_level} reading level
- Explain all medical terms in plain language
- Include a list of medical terms with explanations
- Do NOT include medical advice beyond what the doctor documented
- Generate in {language}

Output format (strict JSON, no markdown):
{{
  "summary_en": "...",
  "summary_es": "..." or "",
  "medical_terms_explained": [{{"term": "...", "explanation": "..."}}]
}}"""


# ── Provider Clients ───────────────────────────────────────────────────────────

class ClaudeClient:
    """Anthropic Claude API client."""

    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = getattr(settings, "CLAUDE_MODEL", "claude-sonnet-4-20250514")

    def call(self, system_prompt: str, user_content: str, max_tokens: int = 4096) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        return response.content[0].text


class GeminiClient:
    """Google Gemini API client."""

    def __init__(self):
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")

    def call(self, system_prompt: str, user_content: str, max_tokens: int = 4096) -> str:
        import google.generativeai as genai
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.3,
            ),
        )
        response = model.generate_content(user_content)
        return response.text


# ── LLM Service ────────────────────────────────────────────────────────────────

class LLMService:
    """
    Multi-provider LLM service for medical documentation.

    Configuration via Django settings:

        # Option 1: Claude only (default)
        LLM_PROVIDER = "claude"

        # Option 2: Gemini only (cheapest)
        LLM_PROVIDER = "gemini"

        # Option 3: Claude + Gemini (best quality/cost ratio)
        LLM_PROVIDER = "claude+gemini"
        # Uses Claude for SOAP notes + quality (best structured output)
        # Uses Gemini for summaries + term explanations (cheapest)
    """

    def __init__(self, provider: str = None, practice=None):
        """
        Initialize with explicit provider, practice-level setting, or global default.
        Priority: explicit provider > practice.llm_provider > settings.LLM_PROVIDER > "claude"
        """
        if provider:
            self.provider_config = provider
        elif practice and hasattr(practice, "llm_provider") and practice.llm_provider:
            self.provider_config = practice.llm_provider
        else:
            self.provider_config = getattr(settings, "LLM_PROVIDER", "claude")
        self._clients = {}

    def _get_client(self, provider: LLMProvider):
        """Lazy-initialize and cache provider clients."""
        if provider not in self._clients:
            if provider == LLMProvider.CLAUDE:
                self._clients[provider] = ClaudeClient()
            elif provider == LLMProvider.GEMINI:
                self._clients[provider] = GeminiClient()
        return self._clients[provider]

    def _resolve_provider(self, task: str) -> LLMProvider:
        """
        Resolve which provider to use for a given task.

        claude       -> Claude for everything
        gemini       -> Gemini for everything
        claude+gemini -> Claude for SOAP/quality/telehealth, Gemini for summaries/terms
        """
        if self.provider_config == "gemini":
            return LLMProvider.GEMINI
        elif self.provider_config == "claude+gemini":
            # Claude handles structured medical reasoning
            # Gemini handles text simplification (cheaper)
            claude_tasks = {"soap_note", "quality_suggestions", "telehealth_soap", "template_auto_complete"}
            gemini_tasks = {"patient_summary", "medical_terms"}
            if task in gemini_tasks:
                return LLMProvider.GEMINI
            return LLMProvider.CLAUDE
        else:
            # Default: claude only
            return LLMProvider.CLAUDE

    def _call_llm(self, task: str, system_prompt: str, user_content: str, max_tokens: int = 4096) -> str:
        """Route the call to the appropriate provider."""
        provider = self._resolve_provider(task)
        client = self._get_client(provider)
        logger.info(f"LLM call: task={task}, provider={provider.value}")
        return client.call(system_prompt, user_content, max_tokens)

    def _parse_json(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}\nResponse: {text[:500]}")
            raise ValueError(f"LLM returned invalid JSON: {e}")

    # ── Public Methods ─────────────────────────────────────────────────────────

    def generate_soap_note(self, transcript_text: str, prompt_version: str) -> dict:
        raw = self._call_llm("soap_note", SOAP_SYSTEM_PROMPT, transcript_text)
        result = self._parse_json(raw)
        required_keys = {"subjective", "objective", "assessment", "plan"}
        missing = required_keys - set(result.keys())
        if missing:
            raise ValueError(f"SOAP note missing required fields: {missing}")
        result.setdefault("icd10_codes", [])
        result.setdefault("cpt_codes", [])
        return result

    def generate_patient_summary(
        self, subjective: str, objective: str, assessment: str, plan: str,
        reading_level: str = "grade_8", language: str = "en",
    ) -> dict:
        system = SUMMARY_SYSTEM_PROMPT.format(
            reading_level=reading_level.replace("_", " "),
            language="English and Spanish" if language == "en" else language,
        )
        note_text = f"Subjective: {subjective}\nObjective: {objective}\nAssessment: {assessment}\nPlan: {plan}"
        raw = self._call_llm("patient_summary", system, note_text)
        result = self._parse_json(raw)
        if "summary_en" not in result:
            raise ValueError("Summary missing 'summary_en' field.")
        result.setdefault("summary_es", "")
        result.setdefault("medical_terms_explained", [])
        return result

    def generate_telehealth_soap_note(
        self, transcript_text: str, telehealth_context: dict, prompt_version: str
    ) -> dict:
        from prompts.telehealth_soap import TELEHEALTH_SOAP_PROMPT

        context_text = (
            f"\nTELEHEALTH CONTEXT:\n"
            f"Modality: {telehealth_context.get('modality', 'audio_video')}\n"
            f"Patient Location: {telehealth_context.get('patient_location', 'Unknown')}\n"
            f"Provider Location: {telehealth_context.get('provider_location', 'Unknown')}\n"
            f"Platform: {telehealth_context.get('platform', 'Unknown')}\n"
        )
        raw = self._call_llm("telehealth_soap", TELEHEALTH_SOAP_PROMPT, transcript_text + context_text)
        result = self._parse_json(raw)

        required_keys = {"subjective", "objective", "assessment", "plan"}
        missing = required_keys - set(result.keys())
        if missing:
            raise ValueError(f"Telehealth SOAP note missing required fields: {missing}")

        result.setdefault("icd10_codes", [])
        result.setdefault("cpt_codes", [])
        result.setdefault("exam_limitations", [])
        result.setdefault("requires_in_person_followup", False)
        result.setdefault("in_person_followup_reason", "")
        return result

    def generate_quality_suggestions(
        self, subjective: str, objective: str, assessment: str, plan: str,
        findings: list,
    ) -> dict:
        from prompts.quality_suggestions import QUALITY_SUGGESTIONS_PROMPT

        findings_text = "\n".join(
            f"- [{f['severity'].upper()}] {f['message']}"
            for f in findings
            if not f.get("passed", True)
        )
        note_text = (
            f"SOAP NOTE:\nSubjective: {subjective}\nObjective: {objective}\n"
            f"Assessment: {assessment}\nPlan: {plan}\n\n"
            f"QUALITY FINDINGS:\n{findings_text}"
        )
        raw = self._call_llm("quality_suggestions", QUALITY_SUGGESTIONS_PROMPT, note_text)
        result = self._parse_json(raw)
        result.setdefault("suggestions", [])
        result.setdefault("recommended_em_level", "")
        return result
