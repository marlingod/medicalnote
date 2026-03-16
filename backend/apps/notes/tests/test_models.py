import uuid
from datetime import date

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote, PromptVersion
from apps.patients.models import Patient


class PromptVersionModelTest(TestCase):
    def test_create_prompt_version(self):
        pv = PromptVersion.objects.create(
            prompt_name="soap_note",
            version="1.0.0",
            template_text="You are a medical documentation assistant...",
            is_active=True,
        )
        assert pv.id is not None
        assert isinstance(pv.id, uuid.UUID)
        assert pv.is_active is True

    def test_prompt_version_str(self):
        pv = PromptVersion.objects.create(
            prompt_name="patient_summary",
            version="2.1.0",
            template_text="Convert this clinical note...",
            is_active=False,
        )
        assert "patient_summary" in str(pv)
        assert "2.1.0" in str(pv)


class ClinicalNoteModelTest(TestCase):
    def setUp(self):
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
            status="generating_note",
        )
        self.prompt_version = PromptVersion.objects.create(
            prompt_name="soap_note",
            version="1.0.0",
            template_text="You are a medical documentation assistant...",
            is_active=True,
        )

    def test_create_clinical_note(self):
        note = ClinicalNote.objects.create(
            encounter=self.encounter,
            note_type="soap",
            subjective="Patient complains of headache for 3 days.",
            objective="BP 120/80, Temp 98.6F, alert and oriented.",
            assessment="Tension headache, likely stress-related.",
            plan="Ibuprofen 400mg as needed. Follow up in 2 weeks.",
            icd10_codes=["R51.9"],
            cpt_codes=["99214"],
            ai_generated=True,
            doctor_edited=False,
            prompt_version=self.prompt_version,
        )
        assert note.id is not None
        assert note.note_type == "soap"
        assert note.ai_generated is True
        assert note.approved_at is None

    def test_approve_clinical_note(self):
        note = ClinicalNote.objects.create(
            encounter=self.encounter,
            note_type="soap",
            subjective="S",
            objective="O",
            assessment="A",
            plan="P",
            ai_generated=True,
            prompt_version=self.prompt_version,
        )
        now = timezone.now()
        note.approved_at = now
        note.approved_by = self.doctor
        note.save()
        note.refresh_from_db()
        assert note.approved_at is not None
        assert note.approved_by == self.doctor

    def test_note_type_choices(self):
        for note_type in ["soap", "free_text", "h_and_p"]:
            note = ClinicalNote(
                encounter=self.encounter,
                note_type=note_type,
                prompt_version=self.prompt_version,
            )
            note.full_clean()  # Should not raise
