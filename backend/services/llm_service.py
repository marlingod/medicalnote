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
