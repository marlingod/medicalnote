from datetime import date

from django.test import TestCase

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote
from apps.patients.models import Patient
from apps.quality.models import QualityFinding, QualityRule, QualityScore


class QualityRuleModelTest(TestCase):
    def test_create_rule(self):
        rule = QualityRule.objects.create(
            rule_code="COMP_001",
            name="Subjective section present",
            description="Check that subjective section is non-empty",
            category="completeness",
            severity="error",
            points=15,
        )
        assert rule.id is not None
        assert rule.rule_code == "COMP_001"
        assert rule.is_active is True

    def test_rule_str(self):
        rule = QualityRule.objects.create(
            rule_code="BILL_001",
            name="ICD-10 codes present",
        )
        assert "BILL_001" in str(rule)


class QualityScoreModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(
            name="Quality Clinic", subscription_tier="solo"
        )
        self.doctor = User.objects.create_user(
            email="quality_doc@test.com",
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
            subjective="S",
            objective="O",
            assessment="A",
            plan="P",
            ai_generated=True,
        )

    def test_create_quality_score(self):
        score = QualityScore.objects.create(
            encounter=self.encounter,
            clinical_note=self.note,
            overall_score=85,
            completeness_score=90,
            billing_score=80,
            compliance_score=85,
            suggested_em_level="99213",
        )
        assert score.id is not None
        assert score.overall_score == 85

    def test_quality_score_str(self):
        score = QualityScore.objects.create(
            encounter=self.encounter,
            clinical_note=self.note,
            overall_score=72,
        )
        assert "72" in str(score)


class QualityFindingModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(
            name="Finding Clinic", subscription_tier="solo"
        )
        self.doctor = User.objects.create_user(
            email="finding_doc@test.com",
            password="test",
            role="doctor",
            practice=self.practice,
        )
        self.patient = Patient.objects.create(
            practice=self.practice,
            first_name="F",
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
            subjective="S",
            objective="O",
            assessment="A",
            plan="P",
            ai_generated=True,
        )
        self.score = QualityScore.objects.create(
            encounter=self.encounter,
            clinical_note=self.note,
            overall_score=85,
        )
        self.rule = QualityRule.objects.create(
            rule_code="TEST_001",
            name="Test Rule",
        )

    def test_create_finding(self):
        finding = QualityFinding.objects.create(
            quality_score=self.score,
            rule=self.rule,
            passed=True,
            message="Section present",
        )
        assert finding.id is not None
        assert finding.passed is True

    def test_finding_str(self):
        finding = QualityFinding.objects.create(
            quality_score=self.score,
            rule=self.rule,
            passed=False,
            message="Missing",
        )
        assert "FAIL" in str(finding)
