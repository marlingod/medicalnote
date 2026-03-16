from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote
from apps.patients.models import Patient
from apps.quality.models import QualityRule, QualityScore


class QualityAPITest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(
            name="Quality API Clinic", subscription_tier="solo"
        )
        self.doctor = User.objects.create_user(
            email="quality_api@test.com",
            password="test",
            role="doctor",
            practice=self.practice,
        )
        self.patient = Patient.objects.create(
            practice=self.practice,
            first_name="Q",
            last_name="P",
            date_of_birth="1990-01-01",
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="paste",
            status="ready_for_review",
        )
        self.note = ClinicalNote.objects.create(
            encounter=self.encounter,
            note_type="soap",
            subjective="Patient reports headache",
            objective="Alert and oriented",
            assessment="Tension headache",
            plan="Ibuprofen 400mg PRN",
            ai_generated=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.doctor)

    def test_get_quality_score(self):
        QualityScore.objects.create(
            encounter=self.encounter,
            clinical_note=self.note,
            overall_score=85,
            completeness_score=90,
            billing_score=80,
            compliance_score=85,
        )
        resp = self.client.get(
            f"/api/v1/encounters/{self.encounter.id}/quality/"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["overall_score"], 85)

    def test_get_quality_not_found(self):
        resp = self.client.get(
            f"/api/v1/encounters/{self.encounter.id}/quality/"
        )
        self.assertEqual(resp.status_code, 404)

    def test_recheck_quality(self):
        resp = self.client.post(
            f"/api/v1/encounters/{self.encounter.id}/quality/recheck/"
        )
        self.assertEqual(resp.status_code, 202)
        self.assertEqual(resp.data["status"], "rechecking")
