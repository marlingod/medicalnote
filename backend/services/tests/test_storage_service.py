from unittest.mock import MagicMock, patch
from io import BytesIO
from django.test import TestCase
from services.storage_service import StorageService


class StorageServiceTest(TestCase):
    @patch("services.storage_service.boto3.client")
    def test_upload_audio(self, mock_boto):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        service = StorageService()
        fake_file = MagicMock()
        fake_file.read.return_value = b"audio data"
        fake_file.name = "recording.wav"
        result = service.upload_audio(fake_file, "encounter-123")
        assert "encounter-123" in result
        mock_client.upload_fileobj.assert_called_once()
