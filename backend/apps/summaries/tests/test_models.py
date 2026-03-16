import uuid
from datetime import date

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote, PromptVersion
from apps.patients.models import Patient
from apps.summaries.models import PatientSummary


class PatientSummaryModelTest(TestCase):
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
            status="generating_summary",
        )
        self.prompt_version = PromptVersion.objects.create(
            prompt_name="patient_summary",
            version="1.0.0",
            template_text="Convert...",
            is_active=True,
        )
        self.note = ClinicalNote.objects.create(
            encounter=self.encounter,
            note_type="soap",
            subjective="S",
            objective="O",
            assessment="A",
            plan="P",
            prompt_version=self.prompt_version,
        )

    def test_create_patient_summary(self):
        summary = PatientSummary.objects.create(
            encounter=self.encounter,
            clinical_note=self.note,
            summary_en="You visited the doctor today. Your blood pressure was normal.",
            summary_es="Visitaste al doctor hoy. Tu presion arterial fue normal.",
            reading_level="grade_8",
            medical_terms_explained=[
                {"term": "hypertension", "explanation": "high blood pressure"}
            ],
            disclaimer_text="This summary is for informational purposes only.",
            delivery_status="pending",
            prompt_version=self.prompt_version,
        )
        assert summary.id is not None
        assert isinstance(summary.id, uuid.UUID)
        assert summary.delivery_status == "pending"
        assert len(summary.medical_terms_explained) == 1

    def test_summary_delivery_lifecycle(self):
        summary = PatientSummary.objects.create(
            encounter=self.encounter,
            clinical_note=self.note,
            summary_en="Summary text.",
            reading_level="grade_8",
            disclaimer_text="Disclaimer.",
            delivery_status="pending",
            prompt_version=self.prompt_version,
        )
        # Send
        summary.delivery_status = "sent"
        summary.delivered_at = timezone.now()
        summary.delivery_method = "app"
        summary.save()
        summary.refresh_from_db()
        assert summary.delivery_status == "sent"
        assert summary.delivered_at is not None

        # View
        summary.delivery_status = "viewed"
        summary.viewed_at = timezone.now()
        summary.save()
        summary.refresh_from_db()
        assert summary.delivery_status == "viewed"
        assert summary.viewed_at is not None

    def test_reading_level_choices(self):
        for level in ["grade_5", "grade_8", "grade_12"]:
            summary = PatientSummary(
                encounter=self.encounter,
                clinical_note=self.note,
                summary_en="Test",
                reading_level=level,
                delivery_status="pending",
                prompt_version=self.prompt_version,
            )
            summary.full_clean()  # Should not raise
