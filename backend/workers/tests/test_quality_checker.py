from datetime import date
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote
from apps.patients.models import Patient
from apps.quality.models import QualityScore
from workers.quality_checker import quality_checker_task


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class QualityCheckerTaskTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(
            name="QC Clinic", subscription_tier="solo"
        )
        self.doctor = User.objects.create_user(
            email="qc_doc@test.com",
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

    @patch("workers.quality_checker._send_ws_update")
    def test_quality_checker_good_note(self, mock_ws):
        ClinicalNote.objects.create(
            encounter=self.encounter,
            note_type="soap",
            subjective=(
                "Patient presents with sharp headache in the temporal "
                "region. Onset 2 days ago after exercise. Severity 7/10. "
                "Worse with bright light. Associated nausea."
            ),
            objective=(
                "Alert and oriented x3. Neurological exam normal. "
                "BP 128/82. Constitutional: well-appearing."
            ),
            assessment="1. Tension headache (R51.9). Likely stress-related.",
            plan="1. Ibuprofen 400mg q8h PRN. 2. Rest. 3. Follow up 1 week.",
            ai_generated=True,
            icd10_codes=["R51.9"],
            cpt_codes=["99213"],
        )
        quality_checker_task(str(self.encounter.id))
        score = QualityScore.objects.get(encounter=self.encounter)
        self.assertGreater(score.overall_score, 50)
        self.assertGreater(score.completeness_score, 50)

    @patch("workers.quality_checker._send_ws_update")
    def test_quality_checker_poor_note(self, mock_ws):
        ClinicalNote.objects.create(
            encounter=self.encounter,
            note_type="soap",
            subjective="HA",
            objective="OK",
            assessment="HA",
            plan="Med",
            ai_generated=True,
        )
        quality_checker_task(str(self.encounter.id))
        score = QualityScore.objects.get(encounter=self.encounter)
        self.assertLess(score.overall_score, 80)

    @patch("workers.quality_checker._send_ws_update")
    def test_quality_checker_recheck(self, mock_ws):
        ClinicalNote.objects.create(
            encounter=self.encounter,
            note_type="soap",
            subjective="Patient reports headache for 3 days with nausea",
            objective="Alert and oriented. Neurological exam normal.",
            assessment="Tension headache",
            plan="Ibuprofen 400mg",
            ai_generated=True,
            icd10_codes=["R51.9"],
        )
        # Run twice - second should replace first
        quality_checker_task(str(self.encounter.id))
        quality_checker_task(str(self.encounter.id))
        scores = QualityScore.objects.filter(encounter=self.encounter)
        self.assertEqual(scores.count(), 1)
