from unittest.mock import MagicMock, patch
from django.test import TestCase
from services.ocr_service import OCRService


class OCRServiceTest(TestCase):
    @patch("services.ocr_service.boto3.client")
    def test_extract_text(self, mock_boto):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.detect_document_text.return_value = {
            "Blocks": [
                {"BlockType": "LINE", "Text": "Patient Name: John Doe"},
                {"BlockType": "LINE", "Text": "Chief Complaint: Headache"},
            ]
        }
        service = OCRService()
        result = service.extract_text_from_s3("s3://bucket/scan.jpg")
        assert "John Doe" in result
        assert "Headache" in result
