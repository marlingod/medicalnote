from datetime import date
from unittest.mock import patch
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote
from apps.patients.models import Patient
from apps.quality.models import QualityScore


class QualityScoreViewTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.practice2 = Practice.objects.create(name="Other Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="testpass123!", role="doctor", practice=self.practice
        )
        self.doctor2 = User.objects.create_user(
            email="doc2@test.com", password="testpass123!", role="doctor", practice=self.practice2
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D", date_of_birth="1990-01-01"
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor, patient=self.patient,
            encounter_date=date.today(), input_method="paste",
        )
        self.note = ClinicalNote.objects.create(
            encounter=self.encounter, note_type="soap",
            subjective="Headache for 3 days",
            objective="Alert and oriented",
            assessment="Tension headache",
            plan="Ibuprofen PRN. Follow-up in 2 weeks.",
            icd10_codes=["R51.9"],
            cpt_codes=["99213"],
        )
        self.quality_score = QualityScore.objects.create(
            clinical_note=self.note,
            encounter=self.encounter,
            overall_score=72,
            completeness_score=60,
            billing_score=80,
            compliance_score=70,
            suggested_em_level="99213",
            suggestions=["Add ROS"],
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.doctor)

    def test_get_quality_score(self):
        resp = self.client.get(f"/api/v1/encounters/{self.encounter.id}/quality/")
        assert resp.status_code == 200
        assert resp.data["overall_score"] == 72
        assert resp.data["suggested_em_level"] == "99213"

    def test_quality_score_404_when_no_score(self):
        encounter2 = Encounter.objects.create(
            doctor=self.doctor, patient=self.patient,
            encounter_date=date.today(), input_method="paste",
        )
        resp = self.client.get(f"/api/v1/encounters/{encounter2.id}/quality/")
        assert resp.status_code == 404

    def test_quality_score_requires_same_practice(self):
        self.client.force_authenticate(user=self.doctor2)
        resp = self.client.get(f"/api/v1/encounters/{self.encounter.id}/quality/")
        assert resp.status_code == 404

    @patch("workers.quality_checker.quality_checker_task")
    def test_trigger_quality_recheck(self, mock_task):
        resp = self.client.post(f"/api/v1/encounters/{self.encounter.id}/quality/recheck/")
        assert resp.status_code == 202
        assert resp.data["status"] == "rechecking"
        mock_task.delay.assert_called_once_with(str(self.encounter.id))

    def test_trigger_quality_recheck_no_note(self):
        encounter2 = Encounter.objects.create(
            doctor=self.doctor, patient=self.patient,
            encounter_date=date.today(), input_method="paste",
        )
        resp = self.client.post(f"/api/v1/encounters/{encounter2.id}/quality/recheck/")
        assert resp.status_code == 400
