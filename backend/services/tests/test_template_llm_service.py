from unittest.mock import MagicMock, patch
from django.test import TestCase, override_settings
from services.template_llm_service import TemplateLLMService


@override_settings(LLM_PROVIDER="claude", ANTHROPIC_API_KEY="test-key")
class TemplateLLMServiceTest(TestCase):
    def _make_schema(self):
        return {
            "sections": [
                {
                    "key": "subjective",
                    "label": "Subjective",
                    "fields": [
                        {"key": "hpi", "label": "History of Present Illness", "type": "textarea",
                         "ai_prompt": "Generate HPI based on chief complaint"},
                        {"key": "chief_complaint", "label": "Chief Complaint", "type": "text"},
                    ],
                },
                {
                    "key": "objective",
                    "label": "Objective",
                    "fields": [
                        {"key": "physical_exam", "label": "Physical Exam", "type": "textarea"},
                    ],
                },
            ],
            "ai_instructions": "Focus on primary care documentation",
        }

    @patch("anthropic.Anthropic")
    def test_auto_complete_section_returns_content(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text='{"content": "Patient presents with headache for 3 days.", "confidence": 0.9, "suggestions": []}')
        ]
        mock_client.messages.create.return_value = mock_response

        service = TemplateLLMService()
        result = service.auto_complete_section(
            template_schema=self._make_schema(),
            section_key="subjective",
            field_key="hpi",
            encounter_context={"chief_complaint": "headache"},
            partial_content="",
            specialty="primary_care",
        )
        assert result["content"] == "Patient presents with headache for 3 days."
        assert result["confidence"] == 0.9

    @patch("anthropic.Anthropic")
    def test_auto_complete_uses_specialty_context(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text='{"content": "Derm content", "confidence": 0.8, "suggestions": []}')
        ]
        mock_client.messages.create.return_value = mock_response

        service = TemplateLLMService()
        service.auto_complete_section(
            template_schema=self._make_schema(),
            section_key="subjective",
            field_key="hpi",
            encounter_context={},
            partial_content="",
            specialty="dermatology",
        )

        # Verify the system prompt included the specialty
        call_args = mock_client.messages.create.call_args
        assert "Dermatology" in call_args.kwargs["system"]

    @patch("anthropic.Anthropic")
    def test_auto_complete_handles_partial_content(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text='{"content": "...continuing from partial", "confidence": 0.7, "suggestions": []}')
        ]
        mock_client.messages.create.return_value = mock_response

        service = TemplateLLMService()
        result = service.auto_complete_section(
            template_schema=self._make_schema(),
            section_key="subjective",
            field_key="hpi",
            encounter_context={},
            partial_content="Patient reports...",
            specialty="primary_care",
        )
        assert result["content"] == "...continuing from partial"

        # Verify partial content was passed in the prompt
        call_args = mock_client.messages.create.call_args
        user_content = call_args.kwargs["messages"][0]["content"]
        assert "Patient reports..." in user_content

    @patch("anthropic.Anthropic")
    def test_auto_complete_handles_api_error(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API Error")

        service = TemplateLLMService()
        result = service.auto_complete_section(
            template_schema=self._make_schema(),
            section_key="subjective",
            field_key="hpi",
            encounter_context={},
            partial_content="",
            specialty="primary_care",
        )
        assert result["content"] == ""
        assert result["confidence"] == 0
        assert "error" in result

    def test_auto_complete_invalid_section(self):
        service = TemplateLLMService.__new__(TemplateLLMService)
        result = service.auto_complete_section(
            template_schema=self._make_schema(),
            section_key="nonexistent_section",
            field_key="",
            encounter_context={},
            partial_content="",
            specialty="general",
        )
        assert result["content"] == ""
        assert "error" in result
