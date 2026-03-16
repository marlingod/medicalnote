from datetime import date
from unittest.mock import patch, MagicMock

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.patients.models import Patient


class EncounterAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D", date_of_birth="1990-01-01"
        )
        self.client.force_authenticate(user=self.doctor)

    def test_create_encounter(self):
        response = self.client.post(
            "/api/v1/encounters/",
            {
                "patient": str(self.patient.id),
                "encounter_date": "2026-03-15",
                "input_method": "paste",
                "consent_recording": False,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "uploading"

    def test_list_encounters_filtered_by_practice(self):
        Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="paste",
        )
        response = self.client.get("/api/v1/encounters/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

    def test_get_encounter_detail(self):
        encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="paste",
        )
        response = self.client.get(f"/api/v1/encounters/{encounter.id}/")
        assert response.status_code == status.HTTP_200_OK

    @patch("workers.soap_note.LLMService")
    @patch("workers.summary.LLMService")
    def test_paste_text_input(self, mock_summary_llm, mock_soap_llm):
        mock_soap = MagicMock()
        mock_soap_llm.return_value = mock_soap
        mock_soap.generate_soap_note.return_value = {
            "subjective": "S", "objective": "O", "assessment": "A", "plan": "P",
            "icd10_codes": [], "cpt_codes": [],
        }
        mock_sum = MagicMock()
        mock_summary_llm.return_value = mock_sum
        mock_sum.generate_patient_summary.return_value = {
            "summary_en": "Summary.", "summary_es": "", "medical_terms_explained": [],
        }
        from apps.notes.models import PromptVersion
        PromptVersion.objects.create(
            prompt_name="soap_note", version="1.0.0", template_text="p", is_active=True
        )
        PromptVersion.objects.create(
            prompt_name="patient_summary", version="1.0.0", template_text="p", is_active=True
        )
        encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="paste",
            status="uploading",
        )
        response = self.client.post(
            f"/api/v1/encounters/{encounter.id}/paste/",
            {"text": "Patient presents with acute headache..."},
            format="json",
        )
        assert response.status_code == status.HTTP_202_ACCEPTED

    def test_update_encounter_status(self):
        encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="paste",
            status="ready_for_review",
        )
        response = self.client.patch(
            f"/api/v1/encounters/{encounter.id}/",
            {"status": "approved"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_cannot_access_other_practice_encounter(self):
        other_practice = Practice.objects.create(name="Other", subscription_tier="solo")
        other_doctor = User.objects.create_user(
            email="other@test.com", password="test", role="doctor", practice=other_practice
        )
        other_patient = Patient.objects.create(
            practice=other_practice, first_name="X", last_name="Y", date_of_birth="1990-01-01"
        )
        encounter = Encounter.objects.create(
            doctor=other_doctor,
            patient=other_patient,
            encounter_date=date.today(),
            input_method="paste",
        )
        response = self.client.get(f"/api/v1/encounters/{encounter.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
