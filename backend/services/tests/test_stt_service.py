from unittest.mock import MagicMock, patch
from django.test import TestCase
from services.stt_service import STTService


class STTServiceTest(TestCase):
    @patch("services.stt_service.boto3.client")
    def test_start_transcription_job(self, mock_boto):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.start_medical_scribe_job.return_value = {
            "MedicalScribeJob": {"MedicalScribeJobName": "job-123", "MedicalScribeJobStatus": "IN_PROGRESS"}
        }
        service = STTService()
        result = service.start_transcription("s3://bucket/audio.wav", "encounter-123")
        assert result["job_name"] == "job-123"

    @patch("services.stt_service.boto3.client")
    def test_get_transcription_result(self, mock_boto):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.get_medical_scribe_job.return_value = {
            "MedicalScribeJob": {
                "MedicalScribeJobStatus": "COMPLETED",
                "MedicalScribeOutput": {
                    "TranscriptFileUri": "s3://output/transcript.json",
                    "ClinicalDocumentUri": "s3://output/clinical.json",
                },
            }
        }
        service = STTService()
        result = service.get_transcription_result("job-123")
        assert result["status"] == "COMPLETED"
