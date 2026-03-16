from unittest.mock import MagicMock, patch
from django.test import TestCase, override_settings
from services.llm_service import LLMService


@override_settings(LLM_PROVIDER="claude", ANTHROPIC_API_KEY="test-key")
class LLMServiceTest(TestCase):
    @patch("anthropic.Anthropic")
    def test_generate_soap_note(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"subjective":"S","objective":"O","assessment":"A","plan":"P","icd10_codes":["R51.9"],"cpt_codes":["99214"]}')]
        mock_client.messages.create.return_value = mock_response

        service = LLMService(provider="claude")
        result = service.generate_soap_note("Patient has headache.", "1.0.0")
        assert result["subjective"] == "S"
        assert "R51.9" in result["icd10_codes"]

    @patch("anthropic.Anthropic")
    def test_generate_patient_summary(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"summary_en":"You visited the doctor.","summary_es":"Visitaste al doctor.","medical_terms_explained":[]}')]
        mock_client.messages.create.return_value = mock_response

        service = LLMService(provider="claude")
        result = service.generate_patient_summary(
            subjective="S", objective="O", assessment="A", plan="P",
            reading_level="grade_8", language="en",
        )
        assert "visited" in result["summary_en"]

    @patch("anthropic.Anthropic")
    def test_invalid_json_raises(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="not valid json")]
        mock_client.messages.create.return_value = mock_response

        service = LLMService(provider="claude")
        with self.assertRaises(ValueError):
            service.generate_soap_note("text", "1.0.0")

    @patch("anthropic.Anthropic")
    def test_provider_routing_claude_only(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"summary_en":"Summary","summary_es":"","medical_terms_explained":[]}')]
        mock_client.messages.create.return_value = mock_response

        service = LLMService(provider="claude")
        result = service.generate_patient_summary(
            subjective="S", objective="O", assessment="A", plan="P",
        )
        assert result["summary_en"] == "Summary"
        mock_client.messages.create.assert_called_once()

    @patch("google.generativeai.GenerativeModel")
    @patch("google.generativeai.configure")
    def test_provider_routing_gemini_only(self, mock_configure, mock_model_cls):
        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model
        mock_response = MagicMock()
        mock_response.text = '{"subjective":"S","objective":"O","assessment":"A","plan":"P","icd10_codes":[],"cpt_codes":[]}'
        mock_model.generate_content.return_value = mock_response

        service = LLMService(provider="gemini")
        result = service.generate_soap_note("Patient has headache.", "1.0.0")
        assert result["subjective"] == "S"

    @patch("google.generativeai.GenerativeModel")
    @patch("google.generativeai.configure")
    @patch("anthropic.Anthropic")
    def test_provider_routing_claude_plus_gemini(self, mock_anthropic_cls, mock_configure, mock_model_cls):
        # Claude for SOAP
        mock_claude = MagicMock()
        mock_anthropic_cls.return_value = mock_claude
        mock_claude_resp = MagicMock()
        mock_claude_resp.content = [MagicMock(text='{"subjective":"S","objective":"O","assessment":"A","plan":"P","icd10_codes":[],"cpt_codes":[]}')]
        mock_claude.messages.create.return_value = mock_claude_resp

        # Gemini for summary
        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model
        mock_gemini_resp = MagicMock()
        mock_gemini_resp.text = '{"summary_en":"Gemini summary","summary_es":"","medical_terms_explained":[]}'
        mock_model.generate_content.return_value = mock_gemini_resp

        service = LLMService(provider="claude+gemini")

        # SOAP should use Claude
        soap = service.generate_soap_note("text", "1.0.0")
        assert soap["subjective"] == "S"
        mock_claude.messages.create.assert_called_once()

        # Summary should use Gemini
        summary = service.generate_patient_summary(
            subjective="S", objective="O", assessment="A", plan="P",
        )
        assert summary["summary_en"] == "Gemini summary"
        mock_model.generate_content.assert_called_once()
