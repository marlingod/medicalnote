from datetime import date
from unittest.mock import MagicMock

from django.test import TestCase

from services.quality_rules_engine import QualityRulesEngine


class QualityRulesEngineTest(TestCase):
    def setUp(self):
        self.engine = QualityRulesEngine()

    def _make_note(self, **kwargs):
        """Create a mock note with given fields."""
        note = MagicMock()
        note.subjective = kwargs.get("subjective", "")
        note.objective = kwargs.get("objective", "")
        note.assessment = kwargs.get("assessment", "")
        note.plan = kwargs.get("plan", "")
        note.icd10_codes = kwargs.get("icd10_codes", [])
        note.cpt_codes = kwargs.get("cpt_codes", [])
        return note

    def test_evaluate_complete_note(self):
        note = self._make_note(
            subjective=(
                "Patient reports sharp headache in temporal region. "
                "Onset 2 days ago. Severity 7/10. Worse with light. "
                "Associated nausea. No prior history."
            ),
            objective=(
                "Alert and oriented x3. Constitutional: well-appearing. "
                "Neurological: cranial nerves intact. BP 128/82."
            ),
            assessment=(
                "1. Tension headache (R51.9). Likely stress-related. "
                "Medical decision making: moderate complexity."
            ),
            plan=(
                "1. Ibuprofen 400mg q8h PRN pain. "
                "2. Stress management techniques. "
                "3. Follow up in 1 week if not improved."
            ),
            icd10_codes=["R51.9"],
            cpt_codes=["99213"],
        )
        result = self.engine.evaluate_note(note)
        self.assertGreater(result["overall_score"], 60)
        self.assertGreater(result["completeness_score"], 60)
        self.assertIn(result["suggested_em_level"], ["99213", "99214"])

    def test_evaluate_empty_note(self):
        note = self._make_note(
            subjective="",
            objective="",
            assessment="",
            plan="",
        )
        result = self.engine.evaluate_note(note)
        self.assertLess(result["overall_score"], 50)

    def test_evaluate_partial_note(self):
        note = self._make_note(
            subjective="Patient has a headache for two days",
            objective="Physical exam is normal",
            assessment="Headache",
            plan="Take medicine",
        )
        result = self.engine.evaluate_note(note)
        self.assertGreater(result["overall_score"], 30)
        self.assertLess(result["overall_score"], 90)

    def test_billing_score_with_codes(self):
        note = self._make_note(
            subjective="Patient with headache onset yesterday",
            objective="Neurological exam normal",
            assessment="Tension headache",
            plan="Ibuprofen PRN, follow up 1 week",
            icd10_codes=["R51.9"],
            cpt_codes=["99213"],
        )
        result = self.engine.evaluate_note(note)
        self.assertGreater(result["billing_score"], 50)

    def test_billing_score_without_codes(self):
        note = self._make_note(
            subjective="Patient with headache onset yesterday",
            objective="Neurological exam normal",
            assessment="Tension headache",
            plan="Ibuprofen PRN",
        )
        result = self.engine.evaluate_note(note)
        self.assertLess(result["billing_score"], 100)
