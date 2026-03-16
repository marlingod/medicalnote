import json
import logging

import anthropic
from django.conf import settings

logger = logging.getLogger(__name__)

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


class LLMService:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"

    def _call_claude(self, system_prompt: str, user_content: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        return response.content[0].text

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

    def generate_soap_note(self, transcript_text: str, prompt_version: str) -> dict:
        raw = self._call_claude(SOAP_SYSTEM_PROMPT, transcript_text)
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
        raw = self._call_claude(system, note_text)
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
        raw = self._call_claude(TELEHEALTH_SOAP_PROMPT, transcript_text + context_text)
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
        raw = self._call_claude(QUALITY_SUGGESTIONS_PROMPT, note_text)
        result = self._parse_json(raw)
        result.setdefault("suggestions", [])
        result.setdefault("recommended_em_level", "")
        return result
