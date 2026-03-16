from datetime import date

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote, PromptVersion
from apps.patients.models import Patient


class NoteAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D", date_of_birth="1990-01-01"
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="paste",
            status="ready_for_review",
        )
        self.prompt_version = PromptVersion.objects.create(
            prompt_name="soap_note",
            version="1.0.0",
            template_text="prompt",
            is_active=True,
        )
        self.note = ClinicalNote.objects.create(
            encounter=self.encounter,
            note_type="soap",
            subjective="S",
            objective="O",
            assessment="A",
            plan="P",
            ai_generated=True,
            prompt_version=self.prompt_version,
        )
        self.client.force_authenticate(user=self.doctor)

    def test_get_note_for_encounter(self):
        response = self.client.get(f"/api/v1/encounters/{self.encounter.id}/note/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["subjective"] == "S"

    def test_edit_note(self):
        response = self.client.patch(
            f"/api/v1/encounters/{self.encounter.id}/note/",
            {"subjective": "Updated subjective text", "doctor_edited": True},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        self.note.refresh_from_db()
        assert self.note.subjective == "Updated subjective text"
        assert self.note.doctor_edited is True

    def test_approve_note(self):
        response = self.client.post(
            f"/api/v1/encounters/{self.encounter.id}/note/approve/"
        )
        assert response.status_code == status.HTTP_200_OK
        self.note.refresh_from_db()
        assert self.note.approved_at is not None
        assert self.note.approved_by == self.doctor
        self.encounter.refresh_from_db()
        assert self.encounter.status == "approved"
