from datetime import date
from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote, PromptVersion
from apps.patients.models import Patient
from apps.summaries.models import PatientSummary


class FullPasteFlowIntegrationTest(TestCase):
    """End-to-end test: doctor creates encounter, pastes text, pipeline runs, review, approve, deliver."""

    def setUp(self):
        self.client = APIClient()
        self.practice = Practice.objects.create(name="Test Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@integration.test", password="SecurePass123!",
            role="doctor", first_name="Jane", last_name="Smith",
            practice=self.practice,
        )
        PromptVersion.objects.create(
            prompt_name="soap_note", version="1.0.0", template_text="p", is_active=True
        )
        PromptVersion.objects.create(
            prompt_name="patient_summary", version="1.0.0", template_text="p", is_active=True
        )
        self.client.force_authenticate(user=self.doctor)

    @patch("workers.summary.LLMService")
    @patch("workers.soap_note.LLMService")
    def test_paste_flow_end_to_end(self, mock_soap_llm_cls, mock_summary_llm_cls):
        # Mock LLM responses
        mock_soap_llm = MagicMock()
        mock_soap_llm_cls.return_value = mock_soap_llm
        mock_soap_llm.generate_soap_note.return_value = {
            "subjective": "Patient reports headache x3 days",
            "objective": "BP 120/80, alert and oriented",
            "assessment": "Tension headache",
            "plan": "Ibuprofen 400mg PRN, follow up 2 weeks",
            "icd10_codes": ["R51.9"],
            "cpt_codes": ["99214"],
        }

        mock_summary_llm = MagicMock()
        mock_summary_llm_cls.return_value = mock_summary_llm
        mock_summary_llm.generate_patient_summary.return_value = {
            "summary_en": "You visited Dr. Smith today for a headache.",
            "summary_es": "Visitaste al Dr. Smith hoy por dolor de cabeza.",
            "medical_terms_explained": [
                {"term": "tension headache", "explanation": "a common headache caused by stress"}
            ],
        }

        # 1. Create patient
        resp = self.client.post("/api/v1/patients/", {
            "first_name": "John", "last_name": "Doe",
            "date_of_birth": "1990-01-15", "phone": "+15551234567",
        }, format="json")
        assert resp.status_code == 201
        patient_id = resp.data["id"]

        # 2. Create encounter
        resp = self.client.post("/api/v1/encounters/", {
            "patient": patient_id,
            "encounter_date": "2026-03-15",
            "input_method": "paste",
        }, format="json")
        assert resp.status_code == 201
        encounter_id = resp.data["id"]

        # 3. Paste text (triggers SOAP note + summary workers synchronously in test mode)
        resp = self.client.post(
            f"/api/v1/encounters/{encounter_id}/paste/",
            {"text": "Patient presents with tension headache for 3 days. No fever. BP 120/80."},
            format="json",
        )
        assert resp.status_code == 202

        # 4. Verify note was generated
        encounter = Encounter.objects.get(id=encounter_id)
        assert encounter.status == "ready_for_review"
        note = ClinicalNote.objects.get(encounter=encounter)
        assert note.subjective == "Patient reports headache x3 days"
        assert note.ai_generated is True

        # 5. Verify summary was generated
        summary = PatientSummary.objects.get(encounter=encounter)
        assert "Dr. Smith" in summary.summary_en

        # 6. Doctor reviews and approves note
        resp = self.client.post(f"/api/v1/encounters/{encounter_id}/note/approve/")
        assert resp.status_code == 200
        encounter.refresh_from_db()
        assert encounter.status == "approved"

        # 7. Doctor sends summary
        resp = self.client.post(
            f"/api/v1/encounters/{encounter_id}/summary/send/",
            {"delivery_method": "app"},
            format="json",
        )
        assert resp.status_code == 200
        encounter.refresh_from_db()
        assert encounter.status == "delivered"
        summary.refresh_from_db()
        assert summary.delivery_status == "sent"
