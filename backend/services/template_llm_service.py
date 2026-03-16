import json
import logging

from django.conf import settings
from services.llm_service import LLMService

logger = logging.getLogger(__name__)

TEMPLATE_AUTO_COMPLETE_SYSTEM = """You are a medical documentation assistant specialized in auto-completing clinical note template sections.

You are working within a {specialty} clinical note template.

Template AI instructions: {ai_instructions}

Given the encounter context and the section/field being filled, generate appropriate clinical content.

Rules:
- Use proper medical terminology for the specialty
- Be concise but thorough
- Follow standard documentation conventions
- Generate content appropriate for the specific field type
- If partial content is provided, continue from where it left off
- Output ONLY the text content for the field, no JSON wrapping unless the field is structured

Output strict JSON:
{{
  "content": "generated text content",
  "confidence": 0.0-1.0,
  "suggestions": ["optional alternative phrasings"]
}}"""


class TemplateLLMService:
    """Template auto-completion service. Uses the multi-provider LLMService under the hood."""

    def __init__(self):
        self._llm = LLMService()

    def auto_complete_section(
        self,
        template_schema: dict,
        section_key: str,
        field_key: str,
        encounter_context: dict,
        partial_content: str,
        specialty: str,
    ) -> dict:
        """Auto-complete a template section/field using AI."""

        # Find the section and field in schema
        section = None
        target_field = None
        for s in template_schema.get("sections", []):
            if s["key"] == section_key:
                section = s
                if field_key:
                    for f in s.get("fields", []):
                        if f["key"] == field_key:
                            target_field = f
                            break
                break

        if not section:
            return {"content": "", "confidence": 0, "error": "Section not found"}

        ai_instructions = template_schema.get("ai_instructions", "")
        field_ai_prompt = target_field.get("ai_prompt", "") if target_field else ""

        system = TEMPLATE_AUTO_COMPLETE_SYSTEM.format(
            specialty=specialty.replace("_", " ").title(),
            ai_instructions=ai_instructions,
        )

        # Build the user prompt with context
        context_parts = []
        if encounter_context.get("transcript_text"):
            context_parts.append(f"Transcript: {encounter_context['transcript_text'][:3000]}")
        if encounter_context.get("chief_complaint"):
            context_parts.append(f"Chief Complaint: {encounter_context['chief_complaint']}")
        if encounter_context.get("patient_age"):
            context_parts.append(f"Patient Age: {encounter_context['patient_age']}")
        if encounter_context.get("patient_sex"):
            context_parts.append(f"Patient Sex: {encounter_context['patient_sex']}")
        if encounter_context.get("existing_sections"):
            for key, value in encounter_context["existing_sections"].items():
                context_parts.append(f"Already documented - {key}: {value[:500]}")

        context_text = "\n".join(context_parts) if context_parts else "No additional context provided."

        user_prompt = f"""
Section: {section.get('label', section_key)}
Field: {target_field.get('label', field_key) if target_field else 'entire section'}
Field type: {target_field.get('type', 'textarea') if target_field else 'textarea'}
Field-specific instructions: {field_ai_prompt}

Encounter context:
{context_text}

{'Partial content to continue: ' + partial_content if partial_content else 'Generate fresh content.'}
"""

        try:
            raw = self._llm._call_llm("template_auto_complete", system, user_prompt, max_tokens=2048)
            return self._parse_json(raw)
        except Exception as e:
            logger.error(f"Template auto-complete failed: {e}")
            return {"content": "", "confidence": 0, "error": str(e)}

    def _parse_json(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse template LLM JSON: {e}")
            return {"content": text, "confidence": 0.5, "suggestions": []}
