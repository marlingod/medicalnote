from datetime import date
from unittest.mock import MagicMock, patch
from django.test import TestCase
from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote, PromptVersion
from apps.patients.models import Patient
from apps.summaries.models import PatientSummary


class SummaryTaskTest(TestCase):
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
            encounter_date=date.today(), input_method="paste", status="generating_summary",
        )
        self.pv = PromptVersion.objects.create(
            prompt_name="patient_summary", version="1.0.0", template_text="t", is_active=True,
        )
        self.note = ClinicalNote.objects.create(
            encounter=self.encounter, note_type="soap",
            subjective="S", objective="O", assessment="A", plan="P",
            ai_generated=True, prompt_version=self.pv,
        )

    @patch("workers.summary.LLMService")
    def test_summary_success(self, mock_llm_cls):
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        mock_llm.generate_patient_summary.return_value = {
            "summary_en": "You visited the doctor today.",
            "summary_es": "Visitaste al doctor hoy.",
            "medical_terms_explained": [{"term": "headache", "explanation": "pain in head"}],
        }

        from workers.summary import generate_summary_task
        generate_summary_task(str(self.encounter.id))

        self.encounter.refresh_from_db()
        assert self.encounter.status == "ready_for_review"
        summary = PatientSummary.objects.get(encounter=self.encounter)
        assert "visited" in summary.summary_en
