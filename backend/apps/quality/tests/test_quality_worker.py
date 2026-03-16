from datetime import date
from unittest.mock import patch
from django.test import TestCase
from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote
from apps.patients.models import Patient
from apps.quality.models import QualityFinding, QualityScore


class QualityCheckerWorkerTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="testpass123!", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D", date_of_birth="1990-01-01"
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor, patient=self.patient,
            encounter_date=date.today(), input_method="paste",
        )
        self.note = ClinicalNote.objects.create(
            encounter=self.encounter,
            note_type="soap",
            subjective="Patient presents with headache for 3 days, moderate severity. Past medical history: none.",
            objective="BP 120/80, heart rate 72. Alert and oriented. Lungs clear.",
            assessment="Tension headache. Consider migraine differential diagnosis.",
            plan="Prescribe ibuprofen. Follow-up in 2 weeks. Risk low.",
            icd10_codes=["R51.9"],
            cpt_codes=["99213"],
        )

    def test_quality_checker_task_creates_score(self):
        from workers.quality_checker import quality_checker_task
        quality_checker_task(str(self.encounter.id))

        assert QualityScore.objects.filter(encounter=self.encounter).exists()
        score = QualityScore.objects.get(encounter=self.encounter)
        assert score.overall_score > 0
        assert score.clinical_note == self.note
        # Should have created findings
        assert QualityFinding.objects.filter(quality_score=score).exists()

    def test_quality_checker_task_handles_missing_note(self):
        encounter2 = Encounter.objects.create(
            doctor=self.doctor, patient=self.patient,
            encounter_date=date.today(), input_method="paste",
        )
        from workers.quality_checker import quality_checker_task
        quality_checker_task(str(encounter2.id))
        assert not QualityScore.objects.filter(encounter=encounter2).exists()

    def test_quality_checker_task_handles_missing_encounter(self):
        from workers.quality_checker import quality_checker_task
        quality_checker_task("00000000-0000-0000-0000-000000000000")

    @patch("workers.quality_checker._send_ws_update")
    def test_quality_checker_sends_ws_update(self, mock_ws):
        from workers.quality_checker import quality_checker_task
        quality_checker_task(str(self.encounter.id))
        mock_ws.assert_called_once()
        args = mock_ws.call_args[0]
        assert args[0] == str(self.encounter.id)
        assert args[1] == "quality_checked"

    def test_quality_checker_task_updates_existing_score(self):
        from workers.quality_checker import quality_checker_task
        quality_checker_task(str(self.encounter.id))
        initial_score = QualityScore.objects.get(encounter=self.encounter).overall_score

        self.note.subjective = "Minimal."
        self.note.objective = "Ok."
        self.note.assessment = "Fine."
        self.note.plan = "Nothing."
        self.note.icd10_codes = []
        self.note.cpt_codes = []
        self.note.save()

        quality_checker_task(str(self.encounter.id))
        updated_score = QualityScore.objects.get(encounter=self.encounter).overall_score

        assert updated_score != initial_score
        assert QualityScore.objects.filter(encounter=self.encounter).count() == 1
