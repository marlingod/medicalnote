from datetime import date
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter, Transcript
from apps.notes.models import PromptVersion
from apps.patients.models import Patient


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class VoiceTranscriptTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(
            name="Voice Clinic", subscription_tier="solo"
        )
        self.doctor = User.objects.create_user(
            email="voice_doc@test.com",
            password="test",
            role="doctor",
            practice=self.practice,
        )
        self.patient = Patient.objects.create(
            practice=self.practice,
            first_name="V",
            last_name="P",
            date_of_birth="1990-01-01",
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="dictation",
            status="uploading",
        )
        PromptVersion.objects.create(
            prompt_name="soap_note",
            version="1.0.0",
            template_text="p",
            is_active=True,
        )
        PromptVersion.objects.create(
            prompt_name="patient_summary",
            version="1.0.0",
            template_text="p",
            is_active=True,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.doctor)

    @patch("workers.quality_checker._send_ws_update")
    @patch("workers.summary.LLMService")
    @patch("workers.soap_note.LLMService")
    def test_voice_transcript_creates_transcript_and_triggers_pipeline(
        self, mock_soap_cls, mock_summary_cls, mock_ws
    ):
        mock_soap = MagicMock()
        mock_soap_cls.return_value = mock_soap
        mock_soap.generate_soap_note.return_value = {
            "subjective": "Voice S",
            "objective": "Voice O",
            "assessment": "Voice A",
            "plan": "Voice P",
            "icd10_codes": [],
            "cpt_codes": [],
        }
        mock_summary = MagicMock()
        mock_summary_cls.return_value = mock_summary
        mock_summary.generate_patient_summary.return_value = {
            "summary_en": "Voice summary.",
            "summary_es": "",
            "medical_terms_explained": [],
        }

        resp = self.api.post(
            f"/api/v1/encounters/{self.encounter.id}/voice-transcript/",
            {
                "text": (
                    "Patient presents with chest pain for two days. "
                    "No shortness of breath."
                ),
                "confidence": 0.92,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 202)

        transcript = Transcript.objects.get(encounter=self.encounter)
        self.assertIn("chest pain", transcript.raw_text)
        self.assertEqual(transcript.confidence_score, 0.92)

    def test_voice_transcript_too_short(self):
        resp = self.api.post(
            f"/api/v1/encounters/{self.encounter.id}/voice-transcript/",
            {"text": "Short"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
