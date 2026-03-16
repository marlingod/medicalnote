from unittest.mock import MagicMock, patch
from django.test import TestCase
from services.llm_service import LLMService


class LLMServiceTest(TestCase):
    @patch("services.llm_service.anthropic.Anthropic")
    def test_generate_soap_note(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"subjective":"S","objective":"O","assessment":"A","plan":"P","icd10_codes":["R51.9"],"cpt_codes":["99214"]}')]
        mock_client.messages.create.return_value = mock_response

        service = LLMService()
        result = service.generate_soap_note("Patient has headache.", "1.0.0")
        assert result["subjective"] == "S"
        assert "R51.9" in result["icd10_codes"]

    @patch("services.llm_service.anthropic.Anthropic")
    def test_generate_patient_summary(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"summary_en":"You visited the doctor.","summary_es":"Visitaste al doctor.","medical_terms_explained":[]}')]
        mock_client.messages.create.return_value = mock_response

        service = LLMService()
        result = service.generate_patient_summary(
            subjective="S", objective="O", assessment="A", plan="P",
            reading_level="grade_8", language="en",
        )
        assert "visited" in result["summary_en"]

    @patch("services.llm_service.anthropic.Anthropic")
    def test_invalid_json_raises(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="not valid json")]
        mock_client.messages.create.return_value = mock_response

        service = LLMService()
        with self.assertRaises(ValueError):
            service.generate_soap_note("text", "1.0.0")
