import sys
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings


def _install_vertexai_mocks():
    """Insert mock vertexai modules into sys.modules so that
    `import vertexai` and `from vertexai.generative_models import ...`
    succeed even when the google-cloud-aiplatform package is not installed."""
    mock_vertexai = MagicMock()
    mock_generative_models = MagicMock()
    mock_vertexai.generative_models = mock_generative_models
    sys.modules.setdefault("vertexai", mock_vertexai)
    sys.modules.setdefault("vertexai.generative_models", mock_generative_models)
    return mock_vertexai, mock_generative_models


# Install mocks at module load so @patch decorators can resolve the paths.
_mock_vertexai, _mock_generative_models = _install_vertexai_mocks()


@override_settings(
    GCP_PROJECT_ID="test-project-id",
    GCP_LOCATION="us-central1",
    GEMINI_MODEL="gemini-2.5-flash",
)
class GeminiClientVertexAITest(TestCase):
    """Test the GeminiClient backed by Vertex AI (HIPAA-eligible)."""

    @override_settings(GCP_PROJECT_ID="")
    @patch("vertexai.init")
    def test_raises_value_error_if_gcp_project_id_not_set(self, mock_vertexai_init):
        """GeminiClient must raise ValueError when GCP_PROJECT_ID is empty."""
        from services.llm_service import GeminiClient

        with self.assertRaises(ValueError) as ctx:
            GeminiClient()

        assert "GCP_PROJECT_ID is required" in str(ctx.exception)
        mock_vertexai_init.assert_not_called()

    @patch("vertexai.generative_models.GenerativeModel")
    @patch("vertexai.init")
    def test_initializes_with_vertexai_init(self, mock_vertexai_init, mock_model_cls):
        """GeminiClient should call vertexai.init() with project and location."""
        from services.llm_service import GeminiClient

        client = GeminiClient()

        mock_vertexai_init.assert_called_once_with(
            project="test-project-id", location="us-central1"
        )
        assert client.model_name == "gemini-2.5-flash"

    @patch("vertexai.generative_models.GenerationConfig")
    @patch("vertexai.generative_models.GenerativeModel")
    @patch("vertexai.init")
    def test_call_invokes_generate_content(
        self, mock_vertexai_init, mock_model_cls, mock_gen_config_cls
    ):
        """GeminiClient.call() should create a GenerativeModel and call generate_content."""
        from services.llm_service import GeminiClient

        mock_model_instance = MagicMock()
        mock_model_cls.return_value = mock_model_instance
        mock_response = MagicMock()
        mock_response.text = '{"result": "test output"}'
        mock_model_instance.generate_content.return_value = mock_response

        client = GeminiClient()
        result = client.call("You are a helper.", "What is 2+2?", max_tokens=1024)

        assert result == '{"result": "test output"}'
        mock_model_instance.generate_content.assert_called_once_with("What is 2+2?")

    @patch("vertexai.generative_models.GenerationConfig")
    @patch("vertexai.generative_models.GenerativeModel")
    @patch("vertexai.init")
    def test_call_passes_system_instruction_and_config(
        self, mock_vertexai_init, mock_model_cls, mock_gen_config_cls
    ):
        """GeminiClient.call() should pass system_instruction and generation_config
        to the GenerativeModel constructor."""
        from services.llm_service import GeminiClient

        mock_model_instance = MagicMock()
        mock_model_cls.return_value = mock_model_instance
        mock_response = MagicMock()
        mock_response.text = "output"
        mock_model_instance.generate_content.return_value = mock_response

        mock_gen_config = MagicMock()
        mock_gen_config_cls.return_value = mock_gen_config

        client = GeminiClient()
        client.call("System prompt", "User content", max_tokens=2048)

        mock_model_cls.assert_called_once_with(
            model_name="gemini-2.5-flash",
            system_instruction="System prompt",
            generation_config=mock_gen_config,
        )
        mock_gen_config_cls.assert_called_once_with(
            max_output_tokens=2048,
            temperature=0.3,
        )


@override_settings(ANTHROPIC_API_KEY="test-key")
class ClaudeClientBAAWarningTest(TestCase):
    """Test ClaudeClient BAA compliance warning."""

    @override_settings(ANTHROPIC_BAA_CONFIRMED=False)
    @patch("anthropic.Anthropic")
    def test_logs_warning_if_baa_not_confirmed(self, mock_anthropic_cls):
        """ClaudeClient should log a warning when ANTHROPIC_BAA_CONFIRMED is not true."""
        from services.llm_service import ClaudeClient

        with self.assertLogs("services.llm_service", level="WARNING") as cm:
            ClaudeClient()

        warning_messages = [msg for msg in cm.output if "ANTHROPIC_BAA_CONFIRMED" in msg]
        assert len(warning_messages) >= 1
        assert "BAA" in warning_messages[0]

    @override_settings(ANTHROPIC_BAA_CONFIRMED=True)
    @patch("anthropic.Anthropic")
    def test_no_warning_if_baa_confirmed(self, mock_anthropic_cls):
        """ClaudeClient should NOT log a warning when ANTHROPIC_BAA_CONFIRMED is true."""
        from services.llm_service import ClaudeClient

        import logging

        logger = logging.getLogger("services.llm_service")
        with patch.object(logger, "warning") as mock_warn:
            ClaudeClient()
            mock_warn.assert_not_called()
