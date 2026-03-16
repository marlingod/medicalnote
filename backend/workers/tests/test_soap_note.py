from datetime import date
from unittest.mock import MagicMock, patch
from django.test import TestCase
from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter, Transcript
from apps.notes.models import PromptVersion
from apps.patients.models import Patient


class SOAPNoteTaskTest(TestCase):
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
            encounter_date=date.today(), input_method="paste", status="generating_note",
        )
        self.transcript = Transcript.objects.create(
            encounter=self.encounter, raw_text="Patient has headache for 3 days.",
            confidence_score=1.0,
        )
        self.prompt = PromptVersion.objects.create(
            prompt_name="soap_note", version="1.0.0",
            template_text="prompt", is_active=True,
        )

    @patch("workers.soap_note.LLMService")
    @patch("workers.summary.generate_summary_task")
    def test_soap_note_success(self, mock_summary_task, mock_llm_cls):
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        mock_llm.generate_soap_note.return_value = {
            "subjective": "Headache x3 days",
            "objective": "Alert, oriented",
            "assessment": "Tension headache",
            "plan": "Ibuprofen PRN",
            "icd10_codes": ["R51.9"],
            "cpt_codes": ["99214"],
        }

        from workers.soap_note import generate_soap_note_task
        generate_soap_note_task(str(self.encounter.id))

        self.encounter.refresh_from_db()
        assert self.encounter.status == "generating_summary"
        assert hasattr(self.encounter, "clinical_note")
        assert self.encounter.clinical_note.subjective == "Headache x3 days"
        mock_summary_task.delay.assert_called_once_with(str(self.encounter.id))
