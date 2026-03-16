from datetime import date
from unittest.mock import MagicMock, patch
from django.test import TestCase
from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter, Recording
from apps.patients.models import Patient


class TranscriptionTaskTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D", date_of_birth="1990-01-01"
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor, patient=self.patient,
            encounter_date=date.today(), input_method="recording", status="transcribing",
        )
        self.recording = Recording.objects.create(
            encounter=self.encounter, storage_url="s3://bucket/audio.wav",
            duration_seconds=600, file_size_bytes=5000000, format="wav",
            transcription_status="pending",
        )

    @patch("workers.transcription.STTService")
    @patch("workers.soap_note.generate_soap_note_task")
    def test_transcription_success(self, mock_soap_task, mock_stt_cls):
        mock_stt = MagicMock()
        mock_stt_cls.return_value = mock_stt
        mock_stt.start_transcription.return_value = {"job_name": "job-1", "status": "COMPLETED"}
        mock_stt.get_transcription_result.return_value = {
            "status": "COMPLETED",
            "transcript_uri": "s3://out/transcript.json",
        }

        from workers.transcription import transcription_task
        with patch("workers.transcription.StorageService") as mock_storage_cls:
            mock_storage = MagicMock()
            mock_storage_cls.return_value = mock_storage
            mock_storage.get_presigned_url.return_value = "https://presigned"

            with patch("workers.transcription.json.loads") as mock_json:
                mock_json.return_value = {
                    "results": {
                        "transcripts": [{"transcript": "Doctor: How are you?"}],
                        "speaker_labels": {"segments": []},
                    }
                }
                with patch("workers.transcription.requests.get") as mock_get:
                    mock_resp = MagicMock()
                    mock_resp.text = "{}"
                    mock_get.return_value = mock_resp

                    transcription_task(str(self.encounter.id))

        self.encounter.refresh_from_db()
        assert self.encounter.status == "generating_note"
