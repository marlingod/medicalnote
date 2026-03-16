# Phase 3: Quality Checker + Telehealth + FHIR Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development to implement this plan.

**Goal:** Add clinical note quality scoring, telehealth documentation support, and FHIR EHR integration to complete the MedicalNote platform.

**Architecture:** Three new Django apps (`apps/quality/`, `apps/telehealth/`, `apps/fhir/`) extend the existing modular monolith. A new Celery worker (`workers/quality_checker.py`) evaluates notes against a rules engine in real-time. The telehealth compliance engine runs as a pure service layer (`services/compliance_service.py`), and the FHIR integration uses a client library (`services/fhir_service.py`) to push DocumentReference and Composition resources to athenahealth and eClinicalWorks endpoints. All three modules follow the existing patterns: UUID primary keys, encrypted PHI fields, practice-scoped access, append-only audit logs, and WebSocket status updates.

**Tech Stack:** Django 5.x, DRF, Celery, `fhirclient` (SMART on FHIR R4 Python client), `fhir.resources` (Pydantic FHIR R4 models), existing Claude API for quality suggestions, AWS Comprehend Medical for ICD-10/CPT validation

---

## Overview of Changes

### New Django Apps
| App | Purpose | Key Models |
|-----|---------|------------|
| `apps/quality/` | Clinical note quality scoring and compliance checking | `QualityRule`, `QualityScore`, `QualityFinding` |
| `apps/telehealth/` | Telehealth encounter fields and multi-state compliance | `TelehealthEncounter`, `StateComplianceRule` |
| `apps/fhir/` | FHIR R4 client, resource builders, EHR connector configs | `FHIRConnection`, `FHIRPushLog` |

### New Workers
| Worker | Queue | Purpose |
|--------|-------|---------|
| `workers/quality_checker.py` | `quality` | Evaluate note against rules engine, produce quality score |

### New Services
| Service | Purpose |
|---------|---------|
| `services/quality_rules_engine.py` | CMS E/M rules evaluation, completeness checks, billing optimization |
| `services/compliance_service.py` | Multi-state telehealth compliance engine |
| `services/fhir_service.py` | FHIR R4 client, resource builders, EHR push |

### New Prompts
| Prompt | Purpose |
|--------|---------|
| `prompts/quality_suggestions.py` | LLM prompt for generating improvement suggestions from quality findings |
| `prompts/telehealth_soap.py` | Telehealth-specific SOAP note formatting prompt (observed-via-video vs patient-reported) |

### Modified Existing Files
| File | Change |
|------|--------|
| `config/settings/base.py` | Add three new apps to `INSTALLED_APPS`, add FHIR/compliance settings |
| `config/urls.py` | Add URL includes for quality, telehealth, fhir apps |
| `config/celery.py` | Add `quality` queue routing |
| `requirements.txt` | Add `fhirclient`, `fhir.resources`, `us-state-abbrev` dependencies |
| `apps/audit/models.py` | Add `quality_score`, `telehealth`, `fhir_push` to `ResourceType` choices |
| `apps/audit/middleware.py` | Add URL patterns for new app endpoints |
| `apps/encounters/models.py` | Add `TELEHEALTH` to `InputMethod` choices, add `quality_checking` to `Status` choices |
| `apps/encounters/serializers.py` | Add `has_quality_score` and `has_telehealth` to detail serializer |
| `apps/notes/models.py` | Add `TELEHEALTH_SOAP` to `NoteType` choices |
| `workers/soap_note.py` | Chain to quality_checker after SOAP note generation |
| `services/llm_service.py` | Add `generate_quality_suggestions()` and `generate_telehealth_soap_note()` methods |

---

## Chunk 1: Quality App - Models and Rules Engine Foundation

### Task 1.1: Create the `apps/quality/` Django app scaffold

- [ ] **Step 1 (2 min):** Create the quality app directory structure.

```bash
mkdir -p backend/apps/quality/tests
touch backend/apps/quality/__init__.py
touch backend/apps/quality/apps.py
touch backend/apps/quality/models.py
touch backend/apps/quality/serializers.py
touch backend/apps/quality/views.py
touch backend/apps/quality/urls.py
touch backend/apps/quality/admin.py
touch backend/apps/quality/tests/__init__.py
touch backend/apps/quality/tests/test_models.py
touch backend/apps/quality/tests/test_rules_engine.py
touch backend/apps/quality/tests/test_api.py
```

- [ ] **Step 2 (1 min):** Create `apps/quality/apps.py`.

File: `backend/apps/quality/apps.py`
```python
from django.apps import AppConfig


class QualityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.quality"
    verbose_name = "Clinical Quality"
```

### Task 1.2: Create Quality models

- [ ] **Step 1 (5 min):** Write tests for Quality models.

File: `backend/apps/quality/tests/test_models.py`
```python
import uuid
from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter, Transcript
from apps.notes.models import ClinicalNote
from apps.patients.models import Patient
from apps.quality.models import QualityFinding, QualityRule, QualityScore


class QualityRuleModelTest(TestCase):
    def test_create_rule(self):
        rule = QualityRule.objects.create(
            rule_id="CMS_SOAP_SUBJECTIVE_PRESENT",
            category="completeness",
            name="Subjective section present",
            description="SOAP note must contain a non-empty subjective section",
            severity="error",
            max_points=10,
            rule_config={
                "field": "subjective",
                "check": "not_empty",
            },
            is_active=True,
        )
        assert rule.id is not None
        assert isinstance(rule.id, uuid.UUID)
        assert rule.category == "completeness"
        assert rule.severity == "error"
        assert rule.max_points == 10

    def test_rule_id_unique(self):
        QualityRule.objects.create(
            rule_id="UNIQUE_RULE_1",
            category="completeness",
            name="Test Rule",
            description="Desc",
            severity="warning",
            max_points=5,
        )
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            QualityRule.objects.create(
                rule_id="UNIQUE_RULE_1",
                category="completeness",
                name="Duplicate",
                description="Desc",
                severity="warning",
                max_points=5,
            )

    def test_rule_str(self):
        rule = QualityRule.objects.create(
            rule_id="TEST_STR",
            category="billing",
            name="Test String",
            description="Desc",
            severity="info",
            max_points=5,
        )
        assert "TEST_STR" in str(rule)


class QualityScoreModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Quality Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="quality_doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="Q", last_name="P", date_of_birth="1990-01-01"
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
            subjective="Headache",
            objective="Alert",
            assessment="Tension headache",
            plan="Ibuprofen",
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
            suggested_em_level="99214",
            findings_summary={"total_findings": 3, "errors": 0, "warnings": 2, "info": 1},
            improvement_suggestions=["Add ROS documentation", "Include HPI duration"],
        )
        assert score.id is not None
        assert score.overall_score == 85
        assert score.suggested_em_level == "99214"

    def test_quality_score_one_per_encounter(self):
        QualityScore.objects.create(
            encounter=self.encounter,
            clinical_note=self.note,
            overall_score=85,
            completeness_score=90,
            billing_score=80,
            compliance_score=85,
        )
        # update_or_create pattern - second one should update, not fail
        score, created = QualityScore.objects.update_or_create(
            encounter=self.encounter,
            defaults={
                "clinical_note": self.note,
                "overall_score": 92,
                "completeness_score": 95,
                "billing_score": 90,
                "compliance_score": 91,
            },
        )
        assert not created
        assert score.overall_score == 92


class QualityFindingModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Finding Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="finding_doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="F", last_name="P", date_of_birth="1990-01-01"
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
            subjective="Headache",
            objective="",
            assessment="Tension headache",
            plan="Ibuprofen",
            ai_generated=True,
        )
        self.score = QualityScore.objects.create(
            encounter=self.encounter,
            clinical_note=self.note,
            overall_score=70,
            completeness_score=60,
            billing_score=80,
            compliance_score=70,
        )
        self.rule = QualityRule.objects.create(
            rule_id="OBJECTIVE_PRESENT",
            category="completeness",
            name="Objective section present",
            description="SOAP note must have objective",
            severity="error",
            max_points=10,
        )

    def test_create_finding(self):
        finding = QualityFinding.objects.create(
            quality_score=self.score,
            rule=self.rule,
            passed=False,
            points_earned=0,
            points_possible=10,
            message="Objective section is empty",
            section="objective",
        )
        assert finding.id is not None
        assert finding.passed is False
        assert finding.points_earned == 0
```

- [ ] **Step 2 (5 min):** Create `apps/quality/models.py`.

File: `backend/apps/quality/models.py`
```python
import uuid

from django.db import models


class QualityRule(models.Model):
    """A single quality/compliance rule that can be evaluated against a clinical note."""

    class Category(models.TextChoices):
        COMPLETENESS = "completeness", "Completeness"
        BILLING = "billing", "Billing Optimization"
        COMPLIANCE = "compliance", "Compliance"
        CODING = "coding", "Code Validation"

    class Severity(models.TextChoices):
        ERROR = "error", "Error"
        WARNING = "warning", "Warning"
        INFO = "info", "Info"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule_id = models.CharField(max_length=100, unique=True, db_index=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    name = models.CharField(max_length=255)
    description = models.TextField()
    severity = models.CharField(max_length=10, choices=Severity.choices)
    max_points = models.IntegerField(default=10)
    rule_config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "quality_rules"
        ordering = ["category", "rule_id"]

    def __str__(self):
        return f"{self.rule_id}: {self.name}"


class QualityScore(models.Model):
    """Aggregated quality score for a clinical note."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    encounter = models.OneToOneField(
        "encounters.Encounter",
        on_delete=models.CASCADE,
        related_name="quality_score",
    )
    clinical_note = models.ForeignKey(
        "notes.ClinicalNote",
        on_delete=models.CASCADE,
        related_name="quality_scores",
    )
    overall_score = models.IntegerField(default=0)  # 0-100
    completeness_score = models.IntegerField(default=0)
    billing_score = models.IntegerField(default=0)
    compliance_score = models.IntegerField(default=0)
    suggested_em_level = models.CharField(max_length=10, blank=True, default="")
    findings_summary = models.JSONField(default=dict, blank=True)
    improvement_suggestions = models.JSONField(default=list, blank=True)
    icd10_validation = models.JSONField(default=dict, blank=True)
    cpt_validation = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "quality_scores"

    def __str__(self):
        return f"Quality {self.overall_score}/100 for {self.encounter_id}"


class QualityFinding(models.Model):
    """Individual finding from a quality rule evaluation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quality_score = models.ForeignKey(
        QualityScore,
        on_delete=models.CASCADE,
        related_name="findings",
    )
    rule = models.ForeignKey(
        QualityRule,
        on_delete=models.CASCADE,
        related_name="findings",
    )
    passed = models.BooleanField(default=False)
    points_earned = models.IntegerField(default=0)
    points_possible = models.IntegerField(default=0)
    message = models.TextField(blank=True, default="")
    section = models.CharField(max_length=50, blank=True, default="")
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "quality_findings"
        ordering = ["-created_at"]

    def __str__(self):
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.rule.rule_id}"
```

- [ ] **Step 3 (1 min):** Run the model tests.

```bash
cd backend && python -m pytest apps/quality/tests/test_models.py -v
```

### Task 1.3: Create the rules engine service

- [ ] **Step 1 (8 min):** Write tests for the quality rules engine.

File: `backend/services/tests/test_quality_rules_engine.py`
```python
from django.test import TestCase

from services.quality_rules_engine import QualityRulesEngine


class QualityRulesEngineTest(TestCase):
    def setUp(self):
        self.engine = QualityRulesEngine()

    def test_complete_soap_scores_high(self):
        note_data = {
            "subjective": "Patient presents with chest pain for 2 days. Pain is substernal, worse with exertion. "
                          "No shortness of breath. No nausea or vomiting. Duration: 2 days. Severity: 7/10. "
                          "Location: substernal. Quality: pressure-like. Context: occurs during walking. "
                          "Modifying factors: rest improves it. Associated signs: mild diaphoresis.",
            "objective": "BP 140/90, HR 88, RR 16, Temp 98.6F, SpO2 98%. "
                         "General: Alert, oriented, mild distress. "
                         "CV: Regular rate rhythm, no murmurs. "
                         "Lungs: Clear bilaterally. "
                         "Abdomen: Soft, non-tender.",
            "assessment": "1. Chest pain, unspecified (R07.9) - concerning for ACS given exertional nature. "
                          "2. Hypertension (I10) - elevated BP today.",
            "plan": "1. EKG and troponin stat. 2. Aspirin 325mg now. 3. Cardiology consult. "
                    "4. Continue lisinopril 10mg daily. 5. Follow up in 1 week.",
            "icd10_codes": ["R07.9", "I10"],
            "cpt_codes": ["99214"],
        }
        result = self.engine.evaluate(note_data)
        assert result["overall_score"] >= 70
        assert result["completeness_score"] >= 70
        assert isinstance(result["findings"], list)

    def test_empty_objective_loses_points(self):
        note_data = {
            "subjective": "Patient has headache.",
            "objective": "",
            "assessment": "Tension headache",
            "plan": "Ibuprofen",
            "icd10_codes": [],
            "cpt_codes": [],
        }
        result = self.engine.evaluate(note_data)
        assert result["overall_score"] < 50
        failed_rules = [f for f in result["findings"] if not f["passed"]]
        rule_ids = [f["rule_id"] for f in failed_rules]
        assert "SOAP_OBJECTIVE_PRESENT" in rule_ids

    def test_missing_all_sections_scores_zero(self):
        note_data = {
            "subjective": "",
            "objective": "",
            "assessment": "",
            "plan": "",
            "icd10_codes": [],
            "cpt_codes": [],
        }
        result = self.engine.evaluate(note_data)
        assert result["overall_score"] < 20

    def test_hpi_elements_detection(self):
        note_data = {
            "subjective": "Patient presents with headache for 3 days. Pain is throbbing, 8/10 severity, "
                          "located in bilateral temporal region. Worse with light exposure. "
                          "Improves with rest in dark room. Associated with nausea.",
            "objective": "Alert, oriented. No focal neuro deficits.",
            "assessment": "Migraine without aura",
            "plan": "Sumatriptan 50mg PRN. Dark room rest.",
            "icd10_codes": ["G43.009"],
            "cpt_codes": ["99213"],
        }
        result = self.engine.evaluate(note_data)
        hpi_finding = next(
            (f for f in result["findings"] if f["rule_id"] == "HPI_ELEMENTS_COUNT"), None
        )
        assert hpi_finding is not None
        assert hpi_finding["points_earned"] > 0

    def test_em_level_suggestion(self):
        note_data = {
            "subjective": "Complex history with multiple problems.",
            "objective": "Comprehensive exam with 12 body systems reviewed.",
            "assessment": "1. DM2 poorly controlled. 2. HTN. 3. CKD stage 3. Multiple decision points.",
            "plan": "Medication adjustments, labs, referrals, extensive counseling.",
            "icd10_codes": ["E11.65", "I10", "N18.3"],
            "cpt_codes": ["99213"],
        }
        result = self.engine.evaluate(note_data)
        assert result["suggested_em_level"] in ("99213", "99214", "99215")

    def test_ros_documentation_check(self):
        note_data = {
            "subjective": "Headache. ROS: Denies fever, chills, vision changes, nausea, "
                          "vomiting, neck stiffness, weakness, numbness.",
            "objective": "Alert, oriented.",
            "assessment": "Tension headache",
            "plan": "Ibuprofen",
            "icd10_codes": ["R51.9"],
            "cpt_codes": ["99213"],
        }
        result = self.engine.evaluate(note_data)
        ros_finding = next(
            (f for f in result["findings"] if f["rule_id"] == "ROS_DOCUMENTED"), None
        )
        assert ros_finding is not None
        assert ros_finding["passed"] is True

    def test_icd10_format_validation(self):
        note_data = {
            "subjective": "Headache",
            "objective": "Alert",
            "assessment": "Tension headache",
            "plan": "Ibuprofen",
            "icd10_codes": ["R51.9", "INVALID_CODE", "Z99"],
            "cpt_codes": ["99213"],
        }
        result = self.engine.evaluate(note_data)
        coding_findings = [f for f in result["findings"] if f["rule_id"] == "ICD10_FORMAT_VALID"]
        assert len(coding_findings) > 0
```

- [ ] **Step 2 (12 min):** Create `services/quality_rules_engine.py`.

File: `backend/services/quality_rules_engine.py`
```python
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# HPI elements per CMS 1995/1997 guidelines
HPI_ELEMENTS = {
    "location": [
        r"locat\w*", r"bilateral", r"left\s+\w+", r"right\s+\w+",
        r"substernal", r"temporal", r"frontal", r"occipital", r"epigastric",
        r"lower\s+(back|extremit)", r"upper\s+(back|extremit)",
    ],
    "quality": [
        r"sharp", r"dull", r"throbbing", r"burning", r"aching",
        r"pressure", r"stabbing", r"cramping", r"radiating",
    ],
    "severity": [
        r"\d+\s*/\s*10", r"mild", r"moderate", r"severe", r"intensity",
        r"worst\s+pain", r"tolerable", r"excruciating",
    ],
    "duration": [
        r"\d+\s*(day|week|month|hour|year|min)", r"since\s+\w+",
        r"for\s+\d+", r"onset\s+\d+", r"x\s*\d+\s*(day|week|month)",
    ],
    "timing": [
        r"constant", r"intermittent", r"morning", r"evening", r"night",
        r"after\s+meal", r"at\s+rest", r"during\s+\w+", r"postprandial",
    ],
    "context": [
        r"while\s+\w+", r"during\s+\w+", r"after\s+\w+", r"exertion",
        r"at\s+work", r"lifting", r"bending", r"walking", r"eating",
    ],
    "modifying_factors": [
        r"improv\w*\s+with", r"worse\s+with", r"alleviat\w*",
        r"exacerbat\w*", r"relief\s+with", r"aggravat\w*",
        r"better\s+with", r"rest\s+improv",
    ],
    "associated_signs": [
        r"associat\w*\s+with", r"accompani\w*", r"also\s+report",
        r"denies", r"no\s+(fever|nausea|vomiting|shortness|dizziness)",
        r"nausea", r"vomiting", r"diaphoresis", r"numbness",
    ],
}

# ROS systems per CMS guidelines
ROS_SYSTEMS = [
    "constitutional", "eyes", "ent", "ear", "nose", "throat",
    "cardiovascular", "respiratory", "gi", "gastrointestinal",
    "gu", "genitourinary", "musculoskeletal", "skin",
    "neurological", "psychiatric", "endocrine",
    "hematologic", "lymphatic", "allergic", "immunologic",
]

ROS_KEYWORDS = [
    r"ros\s*:", r"review\s+of\s+systems?\s*:",
    r"denies\s+\w+", r"no\s+(fever|chills|weight|fatigue|night\s+sweat)",
    r"constitutional", r"eyes?\s*:", r"(ent|ear|nose|throat)\s*:",
    r"cardiovascular\s*:", r"respiratory\s*:", r"gastrointestinal\s*:",
    r"genitourinary\s*:", r"musculoskeletal\s*:", r"skin\s*:",
    r"neurolog\w*\s*:", r"psychiatr\w*\s*:", r"endocrine\s*:",
]

# ICD-10 code format: letter followed by 2 digits, optional dot and 1-4 alphanumeric
ICD10_PATTERN = re.compile(r"^[A-Z]\d{2}(\.\d{1,4})?$")

# CPT code format: 5 digits, optionally followed by modifier
CPT_PATTERN = re.compile(r"^\d{5}(-\d{2})?$")

# E/M level criteria (simplified 2021+ CMS MDM-based leveling)
EM_CRITERIA = {
    "99211": {"min_problems": 0, "min_data": 0, "min_risk": 0},
    "99212": {"min_problems": 1, "min_data": 0, "min_risk": 1},
    "99213": {"min_problems": 1, "min_data": 1, "min_risk": 1},
    "99214": {"min_problems": 2, "min_data": 2, "min_risk": 2},
    "99215": {"min_problems": 3, "min_data": 3, "min_risk": 3},
}


class QualityRulesEngine:
    """Evaluate a clinical note against CMS E/M documentation requirements."""

    def evaluate(self, note_data: dict[str, Any]) -> dict[str, Any]:
        """
        Evaluate a clinical note dictionary and return a quality score.

        Args:
            note_data: dict with keys subjective, objective, assessment, plan,
                       icd10_codes, cpt_codes

        Returns:
            dict with overall_score, completeness_score, billing_score,
            compliance_score, suggested_em_level, findings, findings_summary
        """
        findings = []

        # --- Completeness Rules ---
        findings.extend(self._check_soap_sections_present(note_data))
        findings.extend(self._check_hpi_elements(note_data))
        findings.extend(self._check_ros_documented(note_data))
        findings.extend(self._check_plan_specificity(note_data))

        # --- Billing Rules ---
        findings.extend(self._check_codes_present(note_data))
        findings.extend(self._check_icd10_format(note_data))
        findings.extend(self._check_cpt_format(note_data))

        # --- Compliance Rules ---
        findings.extend(self._check_assessment_plan_linkage(note_data))

        # Calculate scores
        completeness_findings = [f for f in findings if f["category"] == "completeness"]
        billing_findings = [f for f in findings if f["category"] == "billing"]
        compliance_findings = [f for f in findings if f["category"] == "compliance"]

        completeness_score = self._calculate_category_score(completeness_findings)
        billing_score = self._calculate_category_score(billing_findings)
        compliance_score = self._calculate_category_score(compliance_findings)

        # Weighted overall score: completeness 40%, billing 30%, compliance 30%
        overall_score = int(
            completeness_score * 0.4 + billing_score * 0.3 + compliance_score * 0.3
        )

        # Suggest E/M level
        suggested_em_level = self._suggest_em_level(note_data, findings)

        errors = len([f for f in findings if not f["passed"] and f["severity"] == "error"])
        warnings = len([f for f in findings if not f["passed"] and f["severity"] == "warning"])
        info_count = len([f for f in findings if not f["passed"] and f["severity"] == "info"])

        return {
            "overall_score": overall_score,
            "completeness_score": completeness_score,
            "billing_score": billing_score,
            "compliance_score": compliance_score,
            "suggested_em_level": suggested_em_level,
            "findings": findings,
            "findings_summary": {
                "total_findings": len(findings),
                "errors": errors,
                "warnings": warnings,
                "info": info_count,
                "passed": len([f for f in findings if f["passed"]]),
            },
        }

    def _check_soap_sections_present(self, note_data: dict) -> list[dict]:
        findings = []
        sections = [
            ("subjective", "SOAP_SUBJECTIVE_PRESENT", "Subjective section"),
            ("objective", "SOAP_OBJECTIVE_PRESENT", "Objective section"),
            ("assessment", "SOAP_ASSESSMENT_PRESENT", "Assessment section"),
            ("plan", "SOAP_PLAN_PRESENT", "Plan section"),
        ]
        for field, rule_id, label in sections:
            content = note_data.get(field, "").strip()
            passed = len(content) > 10
            findings.append({
                "rule_id": rule_id,
                "category": "completeness",
                "severity": "error",
                "passed": passed,
                "points_earned": 10 if passed else 0,
                "points_possible": 10,
                "message": f"{label} is present and substantive" if passed
                           else f"{label} is missing or too brief",
                "section": field,
            })
        return findings

    def _check_hpi_elements(self, note_data: dict) -> list[dict]:
        subjective = note_data.get("subjective", "").lower()
        elements_found = []
        for element_name, patterns in HPI_ELEMENTS.items():
            for pattern in patterns:
                if re.search(pattern, subjective, re.IGNORECASE):
                    elements_found.append(element_name)
                    break

        count = len(elements_found)
        # CMS: 1-3 elements = brief, 4+ = extended
        max_points = 15
        if count >= 7:
            points = 15
        elif count >= 4:
            points = 12
        elif count >= 2:
            points = 8
        elif count >= 1:
            points = 4
        else:
            points = 0

        return [{
            "rule_id": "HPI_ELEMENTS_COUNT",
            "category": "completeness",
            "severity": "warning" if count < 4 else "info",
            "passed": count >= 4,
            "points_earned": points,
            "points_possible": max_points,
            "message": f"HPI contains {count}/8 elements: {', '.join(elements_found)}"
                       if elements_found else "No HPI elements detected",
            "section": "subjective",
            "details": {"elements_found": elements_found, "count": count},
        }]

    def _check_ros_documented(self, note_data: dict) -> list[dict]:
        subjective = note_data.get("subjective", "").lower()
        ros_present = False
        systems_count = 0

        for keyword_pattern in ROS_KEYWORDS:
            if re.search(keyword_pattern, subjective, re.IGNORECASE):
                ros_present = True
                break

        if ros_present:
            for system in ROS_SYSTEMS:
                if system in subjective:
                    systems_count += 1
            # Also count "denies" statements as ROS coverage
            denies_count = len(re.findall(r"denies?\s+\w+", subjective, re.IGNORECASE))
            no_count = len(re.findall(
                r"no\s+(fever|chills|weight|nausea|vomiting|shortness|dizziness|chest\s+pain|headache)",
                subjective, re.IGNORECASE,
            ))
            systems_count = max(systems_count, denies_count + no_count)

        max_points = 10
        if systems_count >= 10:
            points = 10
        elif systems_count >= 2:
            points = 7
        elif ros_present:
            points = 4
        else:
            points = 0

        return [{
            "rule_id": "ROS_DOCUMENTED",
            "category": "completeness",
            "severity": "warning" if not ros_present else "info",
            "passed": ros_present,
            "points_earned": points,
            "points_possible": max_points,
            "message": f"ROS documented with ~{systems_count} systems reviewed"
                       if ros_present else "No ROS documentation detected",
            "section": "subjective",
            "details": {"ros_present": ros_present, "systems_counted": systems_count},
        }]

    def _check_plan_specificity(self, note_data: dict) -> list[dict]:
        plan = note_data.get("plan", "").strip()
        # Count numbered items or separate sentences
        items = re.findall(r"\d+\.\s", plan)
        if not items:
            items = [s for s in plan.split(". ") if s.strip()]

        max_points = 10
        count = len(items)
        if count >= 3:
            points = 10
        elif count >= 2:
            points = 7
        elif count >= 1:
            points = 4
        else:
            points = 0

        return [{
            "rule_id": "PLAN_SPECIFICITY",
            "category": "completeness",
            "severity": "warning" if count < 2 else "info",
            "passed": count >= 2,
            "points_earned": points,
            "points_possible": max_points,
            "message": f"Plan contains {count} action items" if count > 0
                       else "Plan lacks specific action items",
            "section": "plan",
            "details": {"action_items_count": count},
        }]

    def _check_codes_present(self, note_data: dict) -> list[dict]:
        findings = []
        icd_codes = note_data.get("icd10_codes", [])
        cpt_codes = note_data.get("cpt_codes", [])

        findings.append({
            "rule_id": "ICD10_CODES_PRESENT",
            "category": "billing",
            "severity": "error" if not icd_codes else "info",
            "passed": len(icd_codes) > 0,
            "points_earned": 15 if icd_codes else 0,
            "points_possible": 15,
            "message": f"{len(icd_codes)} ICD-10 code(s) assigned"
                       if icd_codes else "No ICD-10 codes assigned",
            "section": "coding",
        })

        findings.append({
            "rule_id": "CPT_CODES_PRESENT",
            "category": "billing",
            "severity": "error" if not cpt_codes else "info",
            "passed": len(cpt_codes) > 0,
            "points_earned": 15 if cpt_codes else 0,
            "points_possible": 15,
            "message": f"{len(cpt_codes)} CPT code(s) assigned"
                       if cpt_codes else "No CPT codes assigned",
            "section": "coding",
        })
        return findings

    def _check_icd10_format(self, note_data: dict) -> list[dict]:
        codes = note_data.get("icd10_codes", [])
        if not codes:
            return []

        valid = [c for c in codes if ICD10_PATTERN.match(c)]
        invalid = [c for c in codes if not ICD10_PATTERN.match(c)]
        all_valid = len(invalid) == 0

        return [{
            "rule_id": "ICD10_FORMAT_VALID",
            "category": "billing",
            "severity": "warning" if invalid else "info",
            "passed": all_valid,
            "points_earned": 10 if all_valid else 5,
            "points_possible": 10,
            "message": f"All {len(valid)} ICD-10 codes have valid format"
                       if all_valid else f"Invalid ICD-10 format: {', '.join(invalid)}",
            "section": "coding",
            "details": {"valid": valid, "invalid": invalid},
        }]

    def _check_cpt_format(self, note_data: dict) -> list[dict]:
        codes = note_data.get("cpt_codes", [])
        if not codes:
            return []

        valid = [c for c in codes if CPT_PATTERN.match(c)]
        invalid = [c for c in codes if not CPT_PATTERN.match(c)]
        all_valid = len(invalid) == 0

        return [{
            "rule_id": "CPT_FORMAT_VALID",
            "category": "billing",
            "severity": "warning" if invalid else "info",
            "passed": all_valid,
            "points_earned": 10 if all_valid else 5,
            "points_possible": 10,
            "message": f"All {len(valid)} CPT codes have valid format"
                       if all_valid else f"Invalid CPT format: {', '.join(invalid)}",
            "section": "coding",
            "details": {"valid": valid, "invalid": invalid},
        }]

    def _check_assessment_plan_linkage(self, note_data: dict) -> list[dict]:
        assessment = note_data.get("assessment", "").strip()
        plan = note_data.get("plan", "").strip()

        if not assessment or not plan:
            return [{
                "rule_id": "ASSESSMENT_PLAN_LINKED",
                "category": "compliance",
                "severity": "error",
                "passed": False,
                "points_earned": 0,
                "points_possible": 15,
                "message": "Cannot evaluate A/P linkage: assessment or plan is missing",
                "section": "assessment",
            }]

        # Check if numbered assessment items have corresponding plan items
        assessment_items = re.findall(r"\d+\.", assessment)
        plan_items = re.findall(r"\d+\.", plan)

        has_structure = len(assessment_items) > 0 and len(plan_items) > 0
        balanced = abs(len(assessment_items) - len(plan_items)) <= 1 if has_structure else False

        if has_structure and balanced:
            points = 15
            passed = True
            message = f"Assessment ({len(assessment_items)} items) and Plan ({len(plan_items)} items) are well-linked"
        elif has_structure:
            points = 10
            passed = True
            message = f"Assessment ({len(assessment_items)}) and Plan ({len(plan_items)}) items present but counts differ"
        elif len(assessment) > 20 and len(plan) > 20:
            points = 7
            passed = True
            message = "Assessment and Plan both contain content but lack numbered structure"
        else:
            points = 3
            passed = False
            message = "Assessment and/or Plan lack sufficient structure for linkage"

        return [{
            "rule_id": "ASSESSMENT_PLAN_LINKED",
            "category": "compliance",
            "severity": "warning" if not passed else "info",
            "passed": passed,
            "points_earned": points,
            "points_possible": 15,
            "message": message,
            "section": "assessment",
        }]

    def _suggest_em_level(self, note_data: dict, findings: list[dict]) -> str:
        """Suggest E/M level based on documentation completeness and MDM complexity."""
        # Count problems in assessment
        assessment = note_data.get("assessment", "")
        problem_count = max(len(re.findall(r"\d+\.", assessment)), 1 if assessment.strip() else 0)

        # Data complexity: count data elements referenced
        objective = note_data.get("objective", "")
        data_elements = 0
        if re.search(r"(lab|blood|CBC|BMP|CMP|A1c|troponin|BNP)", objective, re.IGNORECASE):
            data_elements += 1
        if re.search(r"(x-?ray|CT|MRI|EKG|ECG|ultrasound|imaging)", objective, re.IGNORECASE):
            data_elements += 1
        if re.search(r"(consult|referr)", note_data.get("plan", ""), re.IGNORECASE):
            data_elements += 1

        # Risk: higher for medications, prescribing, surgeries
        plan = note_data.get("plan", "")
        risk_level = 0
        if re.search(r"(prescription|prescribe|medication|mg\s+daily|prn)", plan, re.IGNORECASE):
            risk_level += 1
        if re.search(r"(surgery|procedure|biopsy|injection)", plan, re.IGNORECASE):
            risk_level += 2
        if re.search(r"(ER|emergency|hospital|admit)", plan, re.IGNORECASE):
            risk_level += 2
        if re.search(r"(follow.?up|return|RTC)", plan, re.IGNORECASE):
            risk_level += 1

        # Map to E/M level
        if problem_count >= 3 and (data_elements >= 3 or risk_level >= 3):
            return "99215"
        elif problem_count >= 2 and (data_elements >= 2 or risk_level >= 2):
            return "99214"
        elif problem_count >= 1 and (data_elements >= 1 or risk_level >= 1):
            return "99213"
        elif problem_count >= 1:
            return "99212"
        else:
            return "99211"

    def _calculate_category_score(self, findings: list[dict]) -> int:
        total_possible = sum(f["points_possible"] for f in findings)
        total_earned = sum(f["points_earned"] for f in findings)
        if total_possible == 0:
            return 0
        return int((total_earned / total_possible) * 100)
```

- [ ] **Step 3 (1 min):** Run the rules engine tests.

```bash
cd backend && python -m pytest services/tests/test_quality_rules_engine.py -v
```

### Task 1.4: Create the quality checker Celery worker

- [ ] **Step 1 (5 min):** Write tests for the quality checker worker.

File: `backend/workers/tests/test_quality_checker.py`
```python
from datetime import date
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter, Transcript
from apps.notes.models import ClinicalNote, PromptVersion
from apps.patients.models import Patient
from apps.quality.models import QualityScore


class QualityCheckerTaskTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="QC Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="qc_doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="Q", last_name="P", date_of_birth="1990-01-01"
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="paste",
            status="generating_summary",
        )
        self.note = ClinicalNote.objects.create(
            encounter=self.encounter,
            note_type="soap",
            subjective="Patient presents with headache for 3 days. Throbbing pain, 7/10.",
            objective="Alert, oriented. BP 130/85. Neuro exam normal.",
            assessment="1. Tension headache (R51.9)",
            plan="1. Ibuprofen 400mg q6h PRN. 2. Follow up in 1 week.",
            icd10_codes=["R51.9"],
            cpt_codes=["99213"],
            ai_generated=True,
        )

    def test_quality_checker_creates_score(self):
        from workers.quality_checker import quality_checker_task

        quality_checker_task(str(self.encounter.id))

        assert QualityScore.objects.filter(encounter=self.encounter).exists()
        score = QualityScore.objects.get(encounter=self.encounter)
        assert 0 <= score.overall_score <= 100
        assert score.clinical_note == self.note
        assert score.findings.count() > 0

    def test_quality_checker_handles_missing_encounter(self):
        from workers.quality_checker import quality_checker_task

        # Should not raise
        quality_checker_task("00000000-0000-0000-0000-000000000000")

    def test_quality_checker_handles_missing_note(self):
        from workers.quality_checker import quality_checker_task

        self.note.delete()
        # Should not raise
        quality_checker_task(str(self.encounter.id))

    @patch("workers.quality_checker.LLMService")
    def test_quality_checker_generates_suggestions(self, mock_llm_cls):
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        mock_llm.generate_quality_suggestions.return_value = [
            "Add more HPI elements (timing, context)",
            "Include ROS documentation",
        ]

        from workers.quality_checker import quality_checker_task

        quality_checker_task(str(self.encounter.id))

        score = QualityScore.objects.get(encounter=self.encounter)
        assert isinstance(score.improvement_suggestions, list)
```

- [ ] **Step 2 (5 min):** Create `workers/quality_checker.py`.

File: `backend/workers/quality_checker.py`
```python
import logging

from celery import shared_task
from django.db import transaction

from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote
from apps.quality.models import QualityFinding, QualityRule, QualityScore
from services.quality_rules_engine import QualityRulesEngine

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=5,
    retry_backoff=True,
    retry_backoff_max=30,
    time_limit=60,
    name="workers.quality_checker.quality_checker_task",
)
def quality_checker_task(self, encounter_id: str):
    try:
        encounter = Encounter.objects.get(id=encounter_id)
        note = ClinicalNote.objects.get(encounter=encounter)
    except (Encounter.DoesNotExist, ClinicalNote.DoesNotExist):
        logger.error(f"Encounter or note not found for quality check: {encounter_id}")
        return

    try:
        engine = QualityRulesEngine()
        note_data = {
            "subjective": note.subjective,
            "objective": note.objective,
            "assessment": note.assessment,
            "plan": note.plan,
            "icd10_codes": note.icd10_codes or [],
            "cpt_codes": note.cpt_codes or [],
        }
        result = engine.evaluate(note_data)

        # Generate improvement suggestions via LLM
        suggestions = []
        failed_findings = [f for f in result["findings"] if not f["passed"]]
        if failed_findings:
            try:
                from services.llm_service import LLMService

                llm = LLMService()
                suggestions = llm.generate_quality_suggestions(
                    note_data, failed_findings
                )
            except Exception as e:
                logger.warning(f"LLM suggestions failed for {encounter_id}: {e}")
                suggestions = [f["message"] for f in failed_findings[:5]]

        with transaction.atomic():
            score, _ = QualityScore.objects.update_or_create(
                encounter=encounter,
                defaults={
                    "clinical_note": note,
                    "overall_score": result["overall_score"],
                    "completeness_score": result["completeness_score"],
                    "billing_score": result["billing_score"],
                    "compliance_score": result["compliance_score"],
                    "suggested_em_level": result["suggested_em_level"],
                    "findings_summary": result["findings_summary"],
                    "improvement_suggestions": suggestions,
                },
            )

            # Clear old findings and create new ones
            QualityFinding.objects.filter(quality_score=score).delete()

            # Ensure QualityRule records exist for each finding
            for finding_data in result["findings"]:
                rule, _ = QualityRule.objects.get_or_create(
                    rule_id=finding_data["rule_id"],
                    defaults={
                        "category": finding_data["category"],
                        "name": finding_data["rule_id"].replace("_", " ").title(),
                        "description": finding_data["message"],
                        "severity": finding_data["severity"],
                        "max_points": finding_data["points_possible"],
                    },
                )
                QualityFinding.objects.create(
                    quality_score=score,
                    rule=rule,
                    passed=finding_data["passed"],
                    points_earned=finding_data["points_earned"],
                    points_possible=finding_data["points_possible"],
                    message=finding_data["message"],
                    section=finding_data.get("section", ""),
                    details=finding_data.get("details", {}),
                )

        _send_ws_update(encounter_id, "quality_check_complete", {
            "overall_score": result["overall_score"],
            "suggested_em_level": result["suggested_em_level"],
        })
        logger.info(
            f"Quality check complete for {encounter_id}: score={result['overall_score']}/100"
        )

    except Exception as exc:
        logger.error(f"Quality checker failed for {encounter_id}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)


def _send_ws_update(encounter_id: str, status: str, extra: dict | None = None):
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        message = {
            "type": "job_status_update",
            "status": status,
            "encounter_id": encounter_id,
        }
        if extra:
            message.update(extra)
        async_to_sync(channel_layer.group_send)(
            f"encounter_{encounter_id}", message
        )
    except Exception as e:
        logger.warning(f"WebSocket update failed: {e}")
```

- [ ] **Step 3 (1 min):** Run the quality checker worker tests.

```bash
cd backend && python -m pytest workers/tests/test_quality_checker.py -v
```

### Task 1.5: Chain quality checker into the SOAP note pipeline

- [ ] **Step 1 (3 min):** Modify `workers/soap_note.py` to chain quality checker after SOAP note generation.

Add after the `generate_summary_task.delay(encounter_id)` call in `generate_soap_note_task`:

```python
# In workers/soap_note.py, inside generate_soap_note_task, after summary dispatch:
from workers.quality_checker import quality_checker_task
quality_checker_task.delay(encounter_id)
```

The full updated block (lines 58-62 of the existing file) becomes:

```python
        from workers.summary import generate_summary_task
        generate_summary_task.delay(encounter_id)

        # Run quality check in parallel with summary generation
        from workers.quality_checker import quality_checker_task
        quality_checker_task.delay(encounter_id)

        _send_ws_update(encounter_id, "generating_summary")
```

- [ ] **Step 2 (2 min):** Update `config/celery.py` to add the quality queue routing.

Add to `app.conf.task_routes`:
```python
    "workers.quality_checker.*": {"queue": "quality"},
```

- [ ] **Step 3 (2 min):** Add `"apps.quality"` to `INSTALLED_APPS` in `config/settings/base.py`.

- [ ] **Step 4 (1 min):** Run migrations and verify.

```bash
cd backend && python manage.py makemigrations quality && python manage.py migrate
```

### Task 1.6: Create Quality API endpoints

- [ ] **Step 1 (3 min):** Create `apps/quality/serializers.py`.

File: `backend/apps/quality/serializers.py`
```python
from rest_framework import serializers

from apps.quality.models import QualityFinding, QualityRule, QualityScore


class QualityRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualityRule
        fields = ["id", "rule_id", "category", "name", "description", "severity", "max_points"]
        read_only_fields = fields


class QualityFindingSerializer(serializers.ModelSerializer):
    rule_detail = QualityRuleSerializer(source="rule", read_only=True)

    class Meta:
        model = QualityFinding
        fields = [
            "id", "rule", "rule_detail", "passed", "points_earned",
            "points_possible", "message", "section", "details", "created_at",
        ]
        read_only_fields = fields


class QualityScoreSerializer(serializers.ModelSerializer):
    findings = QualityFindingSerializer(many=True, read_only=True)

    class Meta:
        model = QualityScore
        fields = [
            "id", "encounter", "clinical_note", "overall_score",
            "completeness_score", "billing_score", "compliance_score",
            "suggested_em_level", "findings_summary", "improvement_suggestions",
            "icd10_validation", "cpt_validation", "findings",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class QualityScoreSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer without findings for list views."""

    class Meta:
        model = QualityScore
        fields = [
            "id", "encounter", "overall_score", "completeness_score",
            "billing_score", "compliance_score", "suggested_em_level",
            "findings_summary", "created_at",
        ]
        read_only_fields = fields
```

- [ ] **Step 2 (3 min):** Create `apps/quality/views.py`.

File: `backend/apps/quality/views.py`
```python
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.permissions import IsDoctorOrAdmin
from apps.encounters.models import Encounter
from apps.quality.models import QualityScore
from apps.quality.serializers import QualityScoreSerializer


@api_view(["GET"])
@permission_classes([IsDoctorOrAdmin])
def encounter_quality_score(request, encounter_id):
    try:
        encounter = Encounter.objects.get(
            id=encounter_id,
            doctor__practice=request.user.practice,
        )
    except Encounter.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    try:
        score = encounter.quality_score
    except QualityScore.DoesNotExist:
        return Response(
            {"error": "No quality score available. Note may still be processing."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = QualityScoreSerializer(score)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsDoctorOrAdmin])
def recheck_quality(request, encounter_id):
    """Manually trigger a quality re-check for an encounter."""
    try:
        encounter = Encounter.objects.get(
            id=encounter_id,
            doctor__practice=request.user.practice,
        )
    except Encounter.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if not hasattr(encounter, "clinical_note"):
        return Response(
            {"error": "No clinical note exists for this encounter."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from workers.quality_checker import quality_checker_task

    quality_checker_task.delay(str(encounter.id))

    return Response(
        {"status": "quality_check_queued", "encounter_id": str(encounter.id)},
        status=status.HTTP_202_ACCEPTED,
    )
```

- [ ] **Step 3 (1 min):** Create `apps/quality/urls.py`.

File: `backend/apps/quality/urls.py`
```python
from django.urls import path

# Quality scores are accessed through encounter URLs via encounters/urls.py
urlpatterns = []
```

- [ ] **Step 4 (2 min):** Add quality routes to `apps/encounters/urls.py`. Add to the urlpatterns list:

```python
    path("<uuid:encounter_id>/quality/", encounter_quality_score, name="encounter-quality"),
    path("<uuid:encounter_id>/quality/recheck/", recheck_quality, name="encounter-quality-recheck"),
```

And add imports:
```python
from apps.quality.views import encounter_quality_score, recheck_quality
```

- [ ] **Step 5 (2 min):** Update `EncounterDetailSerializer` in `apps/encounters/serializers.py` to add `has_quality_score`:

```python
    has_quality_score = serializers.SerializerMethodField()
    # In Meta.fields, add "has_quality_score"

    def get_has_quality_score(self, obj):
        return hasattr(obj, "quality_score")
```

- [ ] **Step 6 (3 min):** Write API tests.

File: `backend/apps/quality/tests/test_api.py`
```python
from datetime import date
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote, PromptVersion
from apps.patients.models import Patient
from apps.quality.models import QualityScore


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class QualityScoreAPITest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Quality API Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="quality_api_doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="Q", last_name="P", date_of_birth="1990-01-01"
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
            subjective="Headache for 3 days",
            objective="Alert, BP 130/85",
            assessment="Tension headache",
            plan="Ibuprofen",
            ai_generated=True,
            icd10_codes=["R51.9"],
            cpt_codes=["99213"],
        )
        self.score = QualityScore.objects.create(
            encounter=self.encounter,
            clinical_note=self.note,
            overall_score=75,
            completeness_score=80,
            billing_score=70,
            compliance_score=75,
            suggested_em_level="99213",
            findings_summary={"total_findings": 5, "errors": 1, "warnings": 2, "info": 2},
            improvement_suggestions=["Add ROS documentation"],
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.doctor)

    def test_get_quality_score(self):
        resp = self.client.get(f"/api/v1/encounters/{self.encounter.id}/quality/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["overall_score"], 75)
        self.assertEqual(resp.data["suggested_em_level"], "99213")

    def test_get_quality_score_not_found(self):
        self.score.delete()
        resp = self.client.get(f"/api/v1/encounters/{self.encounter.id}/quality/")
        self.assertEqual(resp.status_code, 404)

    def test_recheck_quality(self):
        resp = self.client.post(f"/api/v1/encounters/{self.encounter.id}/quality/recheck/")
        self.assertEqual(resp.status_code, 202)

    def test_other_practice_cannot_access(self):
        other_practice = Practice.objects.create(name="Other", subscription_tier="solo")
        other_doc = User.objects.create_user(
            email="other@test.com", password="test", role="doctor", practice=other_practice
        )
        other_client = APIClient()
        other_client.force_authenticate(user=other_doc)
        resp = other_client.get(f"/api/v1/encounters/{self.encounter.id}/quality/")
        self.assertEqual(resp.status_code, 404)
```

- [ ] **Step 7 (1 min):** Run all quality tests.

```bash
cd backend && python -m pytest apps/quality/ workers/tests/test_quality_checker.py services/tests/test_quality_rules_engine.py -v
```

### Task 1.7: Add LLM quality suggestion generation

- [ ] **Step 1 (2 min):** Create the quality suggestions prompt.

File: `backend/prompts/quality_suggestions.py`
```python
QUALITY_SUGGESTIONS_PROMPT = """You are a medical documentation quality advisor. Given a clinical note and a list of quality findings (rule violations), generate 3-5 specific, actionable improvement suggestions.

Each suggestion should:
- Reference the specific section of the note that needs improvement
- Provide a concrete example of what to add or change
- Explain the billing/compliance impact

Output strict JSON only (no markdown, no explanation):
{
  "suggestions": ["suggestion 1", "suggestion 2", ...]
}"""
```

- [ ] **Step 2 (3 min):** Add `generate_quality_suggestions()` to `services/llm_service.py`.

Add this method to the `LLMService` class:

```python
    def generate_quality_suggestions(
        self, note_data: dict, failed_findings: list[dict]
    ) -> list[str]:
        from prompts.quality_suggestions import QUALITY_SUGGESTIONS_PROMPT

        findings_text = "\n".join(
            f"- [{f['severity'].upper()}] {f['rule_id']}: {f['message']}"
            for f in failed_findings
        )
        note_text = (
            f"Subjective: {note_data.get('subjective', '')}\n"
            f"Objective: {note_data.get('objective', '')}\n"
            f"Assessment: {note_data.get('assessment', '')}\n"
            f"Plan: {note_data.get('plan', '')}"
        )
        user_content = f"CLINICAL NOTE:\n{note_text}\n\nQUALITY FINDINGS:\n{findings_text}"

        raw = self._call_claude(QUALITY_SUGGESTIONS_PROMPT, user_content)
        result = self._parse_json(raw)
        return result.get("suggestions", [])
```

- [ ] **Step 3 (1 min):** Run the full quality pipeline test.

```bash
cd backend && python -m pytest apps/quality/ workers/tests/test_quality_checker.py services/tests/test_quality_rules_engine.py -v
```

### Task 1.8: Create Quality admin

- [ ] **Step 1 (2 min):** Create `apps/quality/admin.py`.

File: `backend/apps/quality/admin.py`
```python
from django.contrib import admin

from apps.quality.models import QualityFinding, QualityRule, QualityScore


@admin.register(QualityRule)
class QualityRuleAdmin(admin.ModelAdmin):
    list_display = ["rule_id", "category", "name", "severity", "max_points", "is_active"]
    list_filter = ["category", "severity", "is_active"]
    search_fields = ["rule_id", "name"]


class QualityFindingInline(admin.TabularInline):
    model = QualityFinding
    extra = 0
    readonly_fields = ["rule", "passed", "points_earned", "points_possible", "message", "section"]


@admin.register(QualityScore)
class QualityScoreAdmin(admin.ModelAdmin):
    list_display = ["encounter", "overall_score", "completeness_score", "billing_score",
                    "compliance_score", "suggested_em_level", "created_at"]
    list_filter = ["suggested_em_level"]
    readonly_fields = ["encounter", "clinical_note", "overall_score", "completeness_score",
                       "billing_score", "compliance_score", "suggested_em_level",
                       "findings_summary", "improvement_suggestions"]
    inlines = [QualityFindingInline]
```

---

## Chunk 2: Telehealth App - Models, Compliance Engine, API

### Task 2.1: Create the `apps/telehealth/` Django app scaffold

- [ ] **Step 1 (2 min):** Create directory structure.

```bash
mkdir -p backend/apps/telehealth/tests
touch backend/apps/telehealth/__init__.py
touch backend/apps/telehealth/apps.py
touch backend/apps/telehealth/models.py
touch backend/apps/telehealth/serializers.py
touch backend/apps/telehealth/views.py
touch backend/apps/telehealth/urls.py
touch backend/apps/telehealth/admin.py
touch backend/apps/telehealth/tests/__init__.py
touch backend/apps/telehealth/tests/test_models.py
touch backend/apps/telehealth/tests/test_compliance.py
touch backend/apps/telehealth/tests/test_api.py
```

- [ ] **Step 2 (1 min):** Create `apps/telehealth/apps.py`.

File: `backend/apps/telehealth/apps.py`
```python
from django.apps import AppConfig


class TelehealthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.telehealth"
    verbose_name = "Telehealth Documentation"
```

### Task 2.2: Create Telehealth models

- [ ] **Step 1 (5 min):** Write model tests.

File: `backend/apps/telehealth/tests/test_models.py`
```python
import uuid
from datetime import date

from django.test import TestCase

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.patients.models import Patient
from apps.telehealth.models import StateComplianceRule, TelehealthEncounter


class TelehealthEncounterModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Tele Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="tele_doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="T", last_name="P", date_of_birth="1990-01-01"
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="recording",
            status="uploading",
        )

    def test_create_telehealth_encounter(self):
        tele = TelehealthEncounter.objects.create(
            encounter=self.encounter,
            patient_location_state="FL",
            patient_location_city="Jacksonville",
            patient_location_setting="home",
            provider_location_state="NY",
            provider_location_city="New York",
            modality="audio_video",
            platform="Zoom for Healthcare",
            consent_type="verbal",
            consent_obtained=True,
            consent_statute="FL Stat. 456.47",
            pos_code="10",
            cpt_modifier="-95",
            technology_adequate=True,
        )
        assert tele.id is not None
        assert isinstance(tele.id, uuid.UUID)
        assert tele.patient_location_state == "FL"
        assert tele.pos_code == "10"

    def test_telehealth_one_per_encounter(self):
        TelehealthEncounter.objects.create(
            encounter=self.encounter,
            patient_location_state="FL",
            provider_location_state="NY",
            modality="audio_video",
        )
        tele, created = TelehealthEncounter.objects.update_or_create(
            encounter=self.encounter,
            defaults={
                "patient_location_state": "CA",
                "provider_location_state": "NY",
                "modality": "audio_only",
            },
        )
        assert not created
        assert tele.patient_location_state == "CA"


class StateComplianceRuleModelTest(TestCase):
    def test_create_state_rule(self):
        rule = StateComplianceRule.objects.create(
            state_code="FL",
            state_name="Florida",
            consent_type="verbal",
            consent_required=True,
            consent_statute="FL Stat. 456.47",
            recording_consent="one_party",
            prescribing_restrictions="No controlled substances via telehealth without prior in-person visit",
            interstate_compact=True,
            medicaid_coverage=True,
            additional_rules={
                "min_age_without_parent": 18,
                "mental_health_parity": True,
            },
        )
        assert rule.id is not None
        assert rule.state_code == "FL"
        assert rule.consent_type == "verbal"

    def test_state_code_unique(self):
        StateComplianceRule.objects.create(state_code="FL", state_name="Florida")
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            StateComplianceRule.objects.create(state_code="FL", state_name="Florida 2")
```

- [ ] **Step 2 (5 min):** Create `apps/telehealth/models.py`.

File: `backend/apps/telehealth/models.py`
```python
import uuid

from django.db import models
from encrypted_model_fields.fields import EncryptedCharField


class TelehealthEncounter(models.Model):
    """Telehealth-specific fields extending an encounter."""

    class Modality(models.TextChoices):
        AUDIO_VIDEO = "audio_video", "Audio + Video"
        AUDIO_ONLY = "audio_only", "Audio Only"
        STORE_FORWARD = "store_forward", "Store and Forward"

    class PatientSetting(models.TextChoices):
        HOME = "home", "Patient Home"
        OFFICE = "office", "Office/Workplace"
        FACILITY = "facility", "Healthcare Facility"
        OTHER = "other", "Other"

    class ConsentType(models.TextChoices):
        VERBAL = "verbal", "Verbal"
        WRITTEN = "written", "Written"
        DIGITAL = "digital", "Digital/Electronic"
        NONE_REQUIRED = "none_required", "Not Required"

    class POSCode(models.TextChoices):
        POS_02 = "02", "02 - Telehealth (Facility)"
        POS_10 = "10", "10 - Telehealth (Patient Home)"

    class CPTModifier(models.TextChoices):
        MOD_95 = "-95", "-95 (Synchronous Telehealth)"
        MOD_GT = "-GT", "-GT (Legacy Telehealth)"
        MOD_GQ = "-GQ", "-GQ (Asynchronous Telehealth)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    encounter = models.OneToOneField(
        "encounters.Encounter",
        on_delete=models.CASCADE,
        related_name="telehealth",
    )

    # Location fields
    patient_location_state = models.CharField(max_length=2)
    patient_location_city = EncryptedCharField(max_length=100, blank=True, default="")
    patient_location_setting = models.CharField(
        max_length=20, choices=PatientSetting.choices, default=PatientSetting.HOME
    )
    provider_location_state = models.CharField(max_length=2, blank=True, default="")
    provider_location_city = EncryptedCharField(max_length=100, blank=True, default="")

    # Modality
    modality = models.CharField(max_length=20, choices=Modality.choices, default=Modality.AUDIO_VIDEO)
    platform = models.CharField(max_length=100, blank=True, default="")

    # Consent
    consent_type = models.CharField(
        max_length=20, choices=ConsentType.choices, blank=True, default=""
    )
    consent_obtained = models.BooleanField(default=False)
    consent_timestamp = models.DateTimeField(null=True, blank=True)
    consent_statute = models.CharField(max_length=255, blank=True, default="")

    # Billing
    pos_code = models.CharField(max_length=2, choices=POSCode.choices, blank=True, default="")
    cpt_modifier = models.CharField(max_length=5, choices=CPTModifier.choices, blank=True, default="")

    # Technology verification
    technology_adequate = models.BooleanField(default=True)
    technology_notes = models.TextField(blank=True, default="")

    # Compliance
    compliance_warnings = models.JSONField(default=list, blank=True)
    prescribing_restrictions_acknowledged = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "telehealth_encounters"

    def __str__(self):
        return f"Telehealth {self.modality} for {self.encounter_id}"


class StateComplianceRule(models.Model):
    """State-specific telehealth compliance rules. Updated without code changes."""

    class RecordingConsent(models.TextChoices):
        ONE_PARTY = "one_party", "One-Party Consent"
        TWO_PARTY = "two_party", "Two-Party Consent (All-Party)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    state_code = models.CharField(max_length=2, unique=True, db_index=True)
    state_name = models.CharField(max_length=100, blank=True, default="")
    consent_type = models.CharField(
        max_length=20,
        choices=TelehealthEncounter.ConsentType.choices,
        blank=True,
        default="verbal",
    )
    consent_required = models.BooleanField(default=True)
    consent_statute = models.CharField(max_length=255, blank=True, default="")
    recording_consent = models.CharField(
        max_length=20,
        choices=RecordingConsent.choices,
        default=RecordingConsent.ONE_PARTY,
    )
    prescribing_restrictions = models.TextField(blank=True, default="")
    interstate_compact = models.BooleanField(default=False)
    medicaid_coverage = models.BooleanField(default=True)
    additional_rules = models.JSONField(default=dict, blank=True)
    effective_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "state_compliance_rules"
        ordering = ["state_code"]

    def __str__(self):
        return f"{self.state_code} - {self.state_name}"
```

- [ ] **Step 3 (1 min):** Run model tests.

```bash
cd backend && python -m pytest apps/telehealth/tests/test_models.py -v
```

### Task 2.3: Create the compliance service

- [ ] **Step 1 (5 min):** Write compliance service tests.

File: `backend/services/tests/test_compliance_service.py`
```python
from django.test import TestCase

from apps.telehealth.models import StateComplianceRule
from services.compliance_service import ComplianceService


class ComplianceServiceTest(TestCase):
    def setUp(self):
        self.service = ComplianceService()
        StateComplianceRule.objects.create(
            state_code="FL",
            state_name="Florida",
            consent_type="verbal",
            consent_required=True,
            consent_statute="FL Stat. 456.47",
            recording_consent="one_party",
            prescribing_restrictions="No CS via telehealth without prior in-person",
            interstate_compact=True,
            medicaid_coverage=True,
        )
        StateComplianceRule.objects.create(
            state_code="CA",
            state_name="California",
            consent_type="verbal",
            consent_required=True,
            consent_statute="Cal. Bus. & Prof. Code 2290.5",
            recording_consent="two_party",
            prescribing_restrictions="",
            interstate_compact=False,
            medicaid_coverage=True,
        )
        StateComplianceRule.objects.create(
            state_code="NY",
            state_name="New York",
            consent_type="written",
            consent_required=True,
            consent_statute="NY PHL 2999-cc",
            recording_consent="one_party",
            prescribing_restrictions="",
            interstate_compact=True,
            medicaid_coverage=True,
        )

    def test_determine_pos_code_home(self):
        pos = self.service.determine_pos_code("home")
        assert pos == "10"

    def test_determine_pos_code_facility(self):
        pos = self.service.determine_pos_code("facility")
        assert pos == "02"

    def test_determine_cpt_modifier_audio_video(self):
        modifier = self.service.determine_cpt_modifier("audio_video")
        assert modifier == "-95"

    def test_determine_cpt_modifier_store_forward(self):
        modifier = self.service.determine_cpt_modifier("store_forward")
        assert modifier == "-GQ"

    def test_get_consent_requirements(self):
        result = self.service.get_consent_requirements("FL")
        assert result["consent_required"] is True
        assert result["consent_type"] == "verbal"
        assert "456.47" in result["consent_statute"]

    def test_get_consent_unknown_state(self):
        result = self.service.get_consent_requirements("ZZ")
        assert result["consent_required"] is True
        assert result["consent_type"] == "verbal"

    def test_check_recording_consent(self):
        result = self.service.check_recording_consent("FL", "NY")
        assert result["recording_consent"] == "one_party"

    def test_check_recording_consent_two_party_wins(self):
        result = self.service.check_recording_consent("CA", "NY")
        assert result["recording_consent"] == "two_party"

    def test_generate_compliance_report(self):
        report = self.service.generate_compliance_report(
            patient_state="FL",
            provider_state="NY",
            patient_setting="home",
            modality="audio_video",
        )
        assert report["pos_code"] == "10"
        assert report["cpt_modifier"] == "-95"
        assert report["consent"]["consent_required"] is True
        assert isinstance(report["warnings"], list)

    def test_compliance_report_cross_state_warning(self):
        report = self.service.generate_compliance_report(
            patient_state="CA",
            provider_state="NY",
            patient_setting="home",
            modality="audio_video",
        )
        warnings = report["warnings"]
        cross_state = [w for w in warnings if "interstate" in w.lower() or "cross-state" in w.lower()]
        assert len(cross_state) > 0
```

- [ ] **Step 2 (5 min):** Create `services/compliance_service.py`.

File: `backend/services/compliance_service.py`
```python
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Default consent rules for states not in the database
DEFAULT_CONSENT = {
    "consent_required": True,
    "consent_type": "verbal",
    "consent_statute": "Check applicable state law",
    "recording_consent": "one_party",
}


class ComplianceService:
    """Multi-state telehealth compliance engine."""

    def determine_pos_code(self, patient_setting: str) -> str:
        """Determine Place of Service code based on patient location setting."""
        if patient_setting in ("home", "office", "other"):
            return "10"  # Telehealth in patient home
        elif patient_setting == "facility":
            return "02"  # Telehealth in facility
        return "10"  # Default to home

    def determine_cpt_modifier(self, modality: str) -> str:
        """Determine CPT modifier based on telehealth modality."""
        if modality == "audio_video":
            return "-95"  # Synchronous telehealth
        elif modality == "audio_only":
            return "-95"  # Also -95 per current CMS guidance
        elif modality == "store_forward":
            return "-GQ"  # Asynchronous telehealth
        return "-95"

    def get_consent_requirements(self, state_code: str) -> dict[str, Any]:
        """Get telehealth consent requirements for a state."""
        from apps.telehealth.models import StateComplianceRule

        try:
            rule = StateComplianceRule.objects.get(state_code=state_code, is_active=True)
            return {
                "consent_required": rule.consent_required,
                "consent_type": rule.consent_type,
                "consent_statute": rule.consent_statute,
                "prescribing_restrictions": rule.prescribing_restrictions,
                "medicaid_coverage": rule.medicaid_coverage,
                "interstate_compact": rule.interstate_compact,
            }
        except StateComplianceRule.DoesNotExist:
            logger.warning(f"No compliance rule found for state {state_code}, using defaults")
            return DEFAULT_CONSENT.copy()

    def check_recording_consent(
        self, patient_state: str, provider_state: str
    ) -> dict[str, Any]:
        """Determine recording consent requirement (most restrictive wins)."""
        from apps.telehealth.models import StateComplianceRule

        consent_level = "one_party"
        for state_code in [patient_state, provider_state]:
            try:
                rule = StateComplianceRule.objects.get(state_code=state_code, is_active=True)
                if rule.recording_consent == "two_party":
                    consent_level = "two_party"
            except StateComplianceRule.DoesNotExist:
                pass

        return {
            "recording_consent": consent_level,
            "requires_all_party_consent": consent_level == "two_party",
        }

    def generate_compliance_report(
        self,
        patient_state: str,
        provider_state: str,
        patient_setting: str,
        modality: str,
    ) -> dict[str, Any]:
        """Generate a full compliance report for a telehealth encounter."""
        warnings = []

        pos_code = self.determine_pos_code(patient_setting)
        cpt_modifier = self.determine_cpt_modifier(modality)
        consent = self.get_consent_requirements(patient_state)
        recording = self.check_recording_consent(patient_state, provider_state)

        # Cross-state warnings
        if patient_state != provider_state:
            from apps.telehealth.models import StateComplianceRule

            try:
                patient_rule = StateComplianceRule.objects.get(
                    state_code=patient_state, is_active=True
                )
                if not patient_rule.interstate_compact:
                    warnings.append(
                        f"Cross-state telehealth: {patient_state} is NOT in the Interstate "
                        f"Medical Licensure Compact. Verify provider is licensed in {patient_state}."
                    )
                else:
                    warnings.append(
                        f"Cross-state telehealth: {patient_state} IS in the Interstate "
                        f"Compact. Verify compact license is active."
                    )
            except StateComplianceRule.DoesNotExist:
                warnings.append(
                    f"Cross-state telehealth: No compliance rules found for {patient_state}. "
                    f"Verify licensing requirements manually."
                )

        # Recording consent warning
        if recording["requires_all_party_consent"]:
            warnings.append(
                "Two-party (all-party) recording consent required. "
                "Ensure explicit consent from all participants before recording."
            )

        # Prescribing restrictions
        if consent.get("prescribing_restrictions"):
            warnings.append(
                f"Prescribing restriction ({patient_state}): {consent['prescribing_restrictions']}"
            )

        # Audio-only warnings
        if modality == "audio_only":
            warnings.append(
                "Audio-only visit: Physical exam is limited to patient verbal report only. "
                "Document exam limitations accordingly."
            )

        return {
            "pos_code": pos_code,
            "cpt_modifier": cpt_modifier,
            "consent": consent,
            "recording_consent": recording,
            "warnings": warnings,
        }
```

- [ ] **Step 3 (1 min):** Run compliance tests.

```bash
cd backend && python -m pytest services/tests/test_compliance_service.py -v
```

### Task 2.4: Create Telehealth serializers, views, and URLs

- [ ] **Step 1 (3 min):** Create `apps/telehealth/serializers.py`.

File: `backend/apps/telehealth/serializers.py`
```python
from rest_framework import serializers

from apps.telehealth.models import StateComplianceRule, TelehealthEncounter


class TelehealthEncounterSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelehealthEncounter
        fields = [
            "id", "encounter",
            "patient_location_state", "patient_location_city", "patient_location_setting",
            "provider_location_state", "provider_location_city",
            "modality", "platform",
            "consent_type", "consent_obtained", "consent_timestamp", "consent_statute",
            "pos_code", "cpt_modifier",
            "technology_adequate", "technology_notes",
            "compliance_warnings", "prescribing_restrictions_acknowledged",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "pos_code", "cpt_modifier", "consent_statute",
            "compliance_warnings", "created_at", "updated_at",
        ]


class TelehealthEncounterCreateSerializer(serializers.ModelSerializer):
    """Create serializer that auto-fills compliance fields."""

    class Meta:
        model = TelehealthEncounter
        fields = [
            "encounter",
            "patient_location_state", "patient_location_city", "patient_location_setting",
            "provider_location_state", "provider_location_city",
            "modality", "platform",
            "consent_obtained", "consent_timestamp",
            "technology_adequate", "technology_notes",
        ]

    def create(self, validated_data):
        from services.compliance_service import ComplianceService

        service = ComplianceService()

        patient_state = validated_data["patient_location_state"]
        provider_state = validated_data.get("provider_location_state", "")
        patient_setting = validated_data.get("patient_location_setting", "home")
        modality = validated_data.get("modality", "audio_video")

        report = service.generate_compliance_report(
            patient_state=patient_state,
            provider_state=provider_state,
            patient_setting=patient_setting,
            modality=modality,
        )

        validated_data["pos_code"] = report["pos_code"]
        validated_data["cpt_modifier"] = report["cpt_modifier"]
        validated_data["consent_type"] = report["consent"]["consent_type"]
        validated_data["consent_statute"] = report["consent"].get("consent_statute", "")
        validated_data["compliance_warnings"] = report["warnings"]

        return super().create(validated_data)


class StateComplianceRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = StateComplianceRule
        fields = [
            "id", "state_code", "state_name", "consent_type", "consent_required",
            "consent_statute", "recording_consent", "prescribing_restrictions",
            "interstate_compact", "medicaid_coverage", "additional_rules",
            "effective_date", "is_active",
        ]
        read_only_fields = fields


class ComplianceCheckSerializer(serializers.Serializer):
    """Input serializer for checking compliance before creating encounter."""

    patient_state = serializers.CharField(max_length=2)
    provider_state = serializers.CharField(max_length=2)
    patient_setting = serializers.ChoiceField(
        choices=TelehealthEncounter.PatientSetting.choices, default="home"
    )
    modality = serializers.ChoiceField(
        choices=TelehealthEncounter.Modality.choices, default="audio_video"
    )
```

- [ ] **Step 2 (4 min):** Create `apps/telehealth/views.py`.

File: `backend/apps/telehealth/views.py`
```python
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.permissions import IsDoctorOrAdmin
from apps.encounters.models import Encounter
from apps.telehealth.models import StateComplianceRule, TelehealthEncounter
from apps.telehealth.serializers import (
    ComplianceCheckSerializer,
    StateComplianceRuleSerializer,
    TelehealthEncounterCreateSerializer,
    TelehealthEncounterSerializer,
)
from services.compliance_service import ComplianceService


@api_view(["GET", "POST"])
@permission_classes([IsDoctorOrAdmin])
def encounter_telehealth(request, encounter_id):
    try:
        encounter = Encounter.objects.get(
            id=encounter_id,
            doctor__practice=request.user.practice,
        )
    except Encounter.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        try:
            telehealth = encounter.telehealth
        except TelehealthEncounter.DoesNotExist:
            return Response(
                {"error": "No telehealth data for this encounter."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = TelehealthEncounterSerializer(telehealth)
        return Response(serializer.data)

    if request.method == "POST":
        data = request.data.copy()
        data["encounter"] = str(encounter.id)
        serializer = TelehealthEncounterCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            TelehealthEncounterSerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED,
        )


@api_view(["PATCH"])
@permission_classes([IsDoctorOrAdmin])
def update_telehealth(request, encounter_id):
    try:
        encounter = Encounter.objects.get(
            id=encounter_id,
            doctor__practice=request.user.practice,
        )
    except Encounter.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    try:
        telehealth = encounter.telehealth
    except TelehealthEncounter.DoesNotExist:
        return Response(
            {"error": "No telehealth data for this encounter."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = TelehealthEncounterSerializer(telehealth, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsDoctorOrAdmin])
def check_compliance(request):
    """Pre-check compliance before creating a telehealth encounter."""
    serializer = ComplianceCheckSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    service = ComplianceService()
    report = service.generate_compliance_report(
        patient_state=serializer.validated_data["patient_state"],
        provider_state=serializer.validated_data["provider_state"],
        patient_setting=serializer.validated_data["patient_setting"],
        modality=serializer.validated_data["modality"],
    )
    return Response(report)


@api_view(["GET"])
@permission_classes([IsDoctorOrAdmin])
def list_state_rules(request):
    """List all active state compliance rules."""
    rules = StateComplianceRule.objects.filter(is_active=True)
    serializer = StateComplianceRuleSerializer(rules, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsDoctorOrAdmin])
def get_state_rule(request, state_code):
    """Get compliance rules for a specific state."""
    try:
        rule = StateComplianceRule.objects.get(state_code=state_code.upper(), is_active=True)
    except StateComplianceRule.DoesNotExist:
        return Response(
            {"error": f"No compliance rules found for state {state_code}."},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = StateComplianceRuleSerializer(rule)
    return Response(serializer.data)
```

- [ ] **Step 3 (2 min):** Create `apps/telehealth/urls.py`.

File: `backend/apps/telehealth/urls.py`
```python
from django.urls import path

from apps.telehealth.views import check_compliance, get_state_rule, list_state_rules

urlpatterns = [
    path("compliance/check/", check_compliance, name="telehealth-compliance-check"),
    path("states/", list_state_rules, name="telehealth-state-rules"),
    path("states/<str:state_code>/", get_state_rule, name="telehealth-state-rule"),
]
```

- [ ] **Step 4 (2 min):** Add telehealth routes to `apps/encounters/urls.py`:

```python
from apps.telehealth.views import encounter_telehealth, update_telehealth

# Add to urlpatterns:
    path("<uuid:encounter_id>/telehealth/", encounter_telehealth, name="encounter-telehealth"),
    path("<uuid:encounter_id>/telehealth/update/", update_telehealth, name="encounter-telehealth-update"),
```

- [ ] **Step 5 (1 min):** Add to `config/urls.py`:

```python
    path("api/v1/telehealth/", include("apps.telehealth.urls")),
```

- [ ] **Step 6 (1 min):** Add `"apps.telehealth"` to `INSTALLED_APPS` in `config/settings/base.py`.

- [ ] **Step 7 (1 min):** Run migrations.

```bash
cd backend && python manage.py makemigrations telehealth && python manage.py migrate
```

### Task 2.5: Create telehealth-specific SOAP formatting

- [ ] **Step 1 (2 min):** Create `prompts/telehealth_soap.py`.

File: `backend/prompts/telehealth_soap.py`
```python
TELEHEALTH_SOAP_PROMPT = """You are a medical documentation assistant specialized in TELEHEALTH visit documentation.

Given a transcript from a telehealth encounter, produce a structured SOAP note that:
1. Clearly distinguishes OBSERVED-VIA-VIDEO findings from PATIENT-REPORTED findings
2. Documents exam limitations inherent to virtual visits
3. Notes any items requiring in-person follow-up

In the Objective section, frame all findings appropriately:
- "Visual inspection via video reveals..." (for things doctor could observe)
- "Patient reports..." or "Patient demonstrates on camera..." (for patient-directed exam)
- "Exam limited to visual inspection via video" (for limited systems)
- Include patient-reported vitals with "(patient-reported)" label

Output strict JSON only (no markdown, no explanation):
{
  "subjective": "...",
  "objective": "...",
  "assessment": "...",
  "plan": "...",
  "icd10_codes": ["..."],
  "cpt_codes": ["..."],
  "exam_limitations": ["list of exam limitations noted"],
  "requires_in_person_followup": true/false,
  "in_person_followup_reason": "..."
}"""
```

- [ ] **Step 2 (3 min):** Add `generate_telehealth_soap_note()` to `services/llm_service.py`.

```python
    def generate_telehealth_soap_note(
        self, transcript_text: str, telehealth_context: dict, prompt_version: str
    ) -> dict:
        from prompts.telehealth_soap import TELEHEALTH_SOAP_PROMPT

        context_text = (
            f"\nTELEHEALTH CONTEXT:\n"
            f"Modality: {telehealth_context.get('modality', 'audio_video')}\n"
            f"Patient Location: {telehealth_context.get('patient_location', 'Unknown')}\n"
            f"Provider Location: {telehealth_context.get('provider_location', 'Unknown')}\n"
            f"Platform: {telehealth_context.get('platform', 'Unknown')}\n"
        )
        raw = self._call_claude(TELEHEALTH_SOAP_PROMPT, transcript_text + context_text)
        result = self._parse_json(raw)

        required_keys = {"subjective", "objective", "assessment", "plan"}
        missing = required_keys - set(result.keys())
        if missing:
            raise ValueError(f"Telehealth SOAP note missing required fields: {missing}")

        result.setdefault("icd10_codes", [])
        result.setdefault("cpt_codes", [])
        result.setdefault("exam_limitations", [])
        result.setdefault("requires_in_person_followup", False)
        result.setdefault("in_person_followup_reason", "")
        return result
```

### Task 2.6: Telehealth admin and API tests

- [ ] **Step 1 (2 min):** Create `apps/telehealth/admin.py`.

File: `backend/apps/telehealth/admin.py`
```python
from django.contrib import admin

from apps.telehealth.models import StateComplianceRule, TelehealthEncounter


@admin.register(TelehealthEncounter)
class TelehealthEncounterAdmin(admin.ModelAdmin):
    list_display = [
        "encounter", "modality", "patient_location_state",
        "provider_location_state", "pos_code", "cpt_modifier",
        "consent_obtained", "created_at",
    ]
    list_filter = ["modality", "patient_location_state", "pos_code"]
    readonly_fields = ["pos_code", "cpt_modifier", "consent_statute", "compliance_warnings"]


@admin.register(StateComplianceRule)
class StateComplianceRuleAdmin(admin.ModelAdmin):
    list_display = [
        "state_code", "state_name", "consent_type", "consent_required",
        "recording_consent", "interstate_compact", "medicaid_coverage", "is_active",
    ]
    list_filter = ["consent_type", "recording_consent", "interstate_compact", "is_active"]
    search_fields = ["state_code", "state_name"]
```

- [ ] **Step 2 (5 min):** Create `apps/telehealth/tests/test_api.py`.

File: `backend/apps/telehealth/tests/test_api.py`
```python
from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.patients.models import Patient
from apps.telehealth.models import StateComplianceRule, TelehealthEncounter


class TelehealthAPITest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Tele API Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="tele_api@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="T", last_name="P", date_of_birth="1990-01-01"
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="recording",
            status="uploading",
        )
        StateComplianceRule.objects.create(
            state_code="FL", state_name="Florida",
            consent_type="verbal", consent_required=True,
            consent_statute="FL Stat. 456.47",
            recording_consent="one_party",
            interstate_compact=True,
        )
        StateComplianceRule.objects.create(
            state_code="NY", state_name="New York",
            consent_type="written", consent_required=True,
            consent_statute="NY PHL 2999-cc",
            recording_consent="one_party",
            interstate_compact=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.doctor)

    def test_create_telehealth_encounter(self):
        resp = self.client.post(
            f"/api/v1/encounters/{self.encounter.id}/telehealth/",
            {
                "patient_location_state": "FL",
                "patient_location_city": "Jacksonville",
                "patient_location_setting": "home",
                "provider_location_state": "NY",
                "provider_location_city": "New York",
                "modality": "audio_video",
                "platform": "Zoom for Healthcare",
                "consent_obtained": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["pos_code"], "10")
        self.assertEqual(resp.data["cpt_modifier"], "-95")
        self.assertEqual(resp.data["consent_statute"], "FL Stat. 456.47")
        self.assertIsInstance(resp.data["compliance_warnings"], list)

    def test_get_telehealth_encounter(self):
        TelehealthEncounter.objects.create(
            encounter=self.encounter,
            patient_location_state="FL",
            provider_location_state="NY",
            modality="audio_video",
            pos_code="10",
            cpt_modifier="-95",
        )
        resp = self.client.get(f"/api/v1/encounters/{self.encounter.id}/telehealth/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["patient_location_state"], "FL")

    def test_compliance_check(self):
        resp = self.client.post("/api/v1/telehealth/compliance/check/", {
            "patient_state": "FL",
            "provider_state": "NY",
            "patient_setting": "home",
            "modality": "audio_video",
        }, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["pos_code"], "10")
        self.assertEqual(resp.data["cpt_modifier"], "-95")

    def test_list_state_rules(self):
        resp = self.client.get("/api/v1/telehealth/states/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)

    def test_get_state_rule(self):
        resp = self.client.get("/api/v1/telehealth/states/FL/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["state_code"], "FL")
```

- [ ] **Step 3 (1 min):** Run all telehealth tests.

```bash
cd backend && python -m pytest apps/telehealth/ services/tests/test_compliance_service.py -v
```

### Task 2.7: Seed initial state compliance rules

- [ ] **Step 1 (3 min):** Create a management command for seeding state rules.

File: `backend/apps/telehealth/management/__init__.py`
```python
```

File: `backend/apps/telehealth/management/commands/__init__.py`
```python
```

File: `backend/apps/telehealth/management/commands/seed_state_rules.py`
```python
from django.core.management.base import BaseCommand

from apps.telehealth.models import StateComplianceRule

# Initial seed data for all 50 states + DC (subset shown; full list in production)
STATE_RULES = [
    {"state_code": "AL", "state_name": "Alabama", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "AK", "state_name": "Alaska", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": False},
    {"state_code": "AZ", "state_name": "Arizona", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "CA", "state_name": "California", "consent_type": "verbal", "consent_statute": "Cal. Bus. & Prof. Code 2290.5", "recording_consent": "two_party", "interstate_compact": False},
    {"state_code": "CO", "state_name": "Colorado", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "CT", "state_name": "Connecticut", "consent_type": "verbal", "recording_consent": "two_party", "interstate_compact": False},
    {"state_code": "DC", "state_name": "District of Columbia", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "FL", "state_name": "Florida", "consent_type": "verbal", "consent_statute": "FL Stat. 456.47", "recording_consent": "two_party", "interstate_compact": True},
    {"state_code": "GA", "state_name": "Georgia", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "IL", "state_name": "Illinois", "consent_type": "verbal", "recording_consent": "two_party", "interstate_compact": True},
    {"state_code": "MA", "state_name": "Massachusetts", "consent_type": "written", "recording_consent": "two_party", "interstate_compact": False},
    {"state_code": "MD", "state_name": "Maryland", "consent_type": "verbal", "recording_consent": "two_party", "interstate_compact": True},
    {"state_code": "MI", "state_name": "Michigan", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "MN", "state_name": "Minnesota", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "NJ", "state_name": "New Jersey", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "NY", "state_name": "New York", "consent_type": "written", "consent_statute": "NY PHL 2999-cc", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "PA", "state_name": "Pennsylvania", "consent_type": "verbal", "recording_consent": "two_party", "interstate_compact": True},
    {"state_code": "TX", "state_name": "Texas", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "WA", "state_name": "Washington", "consent_type": "verbal", "recording_consent": "two_party", "interstate_compact": True},
]


class Command(BaseCommand):
    help = "Seed initial state telehealth compliance rules"

    def handle(self, *args, **options):
        created_count = 0
        for rule_data in STATE_RULES:
            _, created = StateComplianceRule.objects.update_or_create(
                state_code=rule_data["state_code"],
                defaults={
                    "state_name": rule_data.get("state_name", ""),
                    "consent_type": rule_data.get("consent_type", "verbal"),
                    "consent_required": True,
                    "consent_statute": rule_data.get("consent_statute", ""),
                    "recording_consent": rule_data.get("recording_consent", "one_party"),
                    "interstate_compact": rule_data.get("interstate_compact", False),
                    "medicaid_coverage": True,
                    "is_active": True,
                },
            )
            if created:
                created_count += 1
        self.stdout.write(
            self.style.SUCCESS(f"Seeded {created_count} new state rules ({len(STATE_RULES)} total)")
        )
```

---

## Chunk 3: FHIR Integration Layer

### Task 3.1: Create the `apps/fhir/` Django app scaffold

- [ ] **Step 1 (2 min):** Create directory structure.

```bash
mkdir -p backend/apps/fhir/tests
touch backend/apps/fhir/__init__.py
touch backend/apps/fhir/apps.py
touch backend/apps/fhir/models.py
touch backend/apps/fhir/serializers.py
touch backend/apps/fhir/views.py
touch backend/apps/fhir/urls.py
touch backend/apps/fhir/admin.py
touch backend/apps/fhir/tests/__init__.py
touch backend/apps/fhir/tests/test_models.py
touch backend/apps/fhir/tests/test_fhir_service.py
touch backend/apps/fhir/tests/test_api.py
```

- [ ] **Step 2 (1 min):** Create `apps/fhir/apps.py`.

File: `backend/apps/fhir/apps.py`
```python
from django.apps import AppConfig


class FHIRConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.fhir"
    verbose_name = "FHIR Integration"
```

### Task 3.2: Create FHIR models

- [ ] **Step 1 (4 min):** Write model tests.

File: `backend/apps/fhir/tests/test_models.py`
```python
import uuid
from datetime import date

from django.test import TestCase

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.fhir.models import FHIRConnection, FHIRPushLog
from apps.notes.models import ClinicalNote
from apps.patients.models import Patient


class FHIRConnectionModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="FHIR Clinic", subscription_tier="solo")

    def test_create_connection(self):
        conn = FHIRConnection.objects.create(
            practice=self.practice,
            ehr_system="athenahealth",
            display_name="Athena Production",
            fhir_base_url="https://api.athenahealth.com/fhir/r4",
            client_id="test_client_id",
            client_secret="test_secret",
            auth_type="client_credentials",
            scopes="patient/*.read system/*.write",
            is_active=True,
        )
        assert conn.id is not None
        assert conn.ehr_system == "athenahealth"
        assert conn.is_active is True

    def test_connection_str(self):
        conn = FHIRConnection.objects.create(
            practice=self.practice,
            ehr_system="eclinicalworks",
            display_name="eCW",
            fhir_base_url="https://fhir.eclinicalworks.com/r4",
        )
        assert "eCW" in str(conn)


class FHIRPushLogModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Push Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="push_doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="P", last_name="L", date_of_birth="1990-01-01"
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="paste",
            status="approved",
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
        self.connection = FHIRConnection.objects.create(
            practice=self.practice,
            ehr_system="athenahealth",
            display_name="Athena",
            fhir_base_url="https://api.athenahealth.com/fhir/r4",
            is_active=True,
        )

    def test_create_push_log(self):
        log = FHIRPushLog.objects.create(
            connection=self.connection,
            encounter=self.encounter,
            clinical_note=self.note,
            resource_type="DocumentReference",
            fhir_resource_id="doc-ref-123",
            status="success",
            response_code=201,
            response_body={"id": "doc-ref-123", "resourceType": "DocumentReference"},
        )
        assert log.id is not None
        assert log.status == "success"
        assert log.response_code == 201

    def test_push_log_failure(self):
        log = FHIRPushLog.objects.create(
            connection=self.connection,
            encounter=self.encounter,
            clinical_note=self.note,
            resource_type="DocumentReference",
            status="failed",
            response_code=401,
            error_message="Authentication failed",
        )
        assert log.status == "failed"
        assert log.error_message == "Authentication failed"
```

- [ ] **Step 2 (5 min):** Create `apps/fhir/models.py`.

File: `backend/apps/fhir/models.py`
```python
import uuid

from django.db import models
from encrypted_model_fields.fields import EncryptedCharField, EncryptedTextField


class FHIRConnection(models.Model):
    """Configuration for a FHIR EHR connection per practice."""

    class EHRSystem(models.TextChoices):
        ATHENAHEALTH = "athenahealth", "athenahealth"
        ECLINICALWORKS = "eclinicalworks", "eClinicalWorks"
        EPIC = "epic", "Epic"
        CERNER = "cerner", "Cerner"
        NEXTGEN = "nextgen", "NextGen"
        OTHER = "other", "Other"

    class AuthType(models.TextChoices):
        CLIENT_CREDENTIALS = "client_credentials", "Client Credentials"
        AUTHORIZATION_CODE = "authorization_code", "Authorization Code (SMART)"
        BACKEND_SERVICE = "backend_service", "Backend Service"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    practice = models.ForeignKey(
        "accounts.Practice",
        on_delete=models.CASCADE,
        related_name="fhir_connections",
    )
    ehr_system = models.CharField(max_length=20, choices=EHRSystem.choices)
    display_name = models.CharField(max_length=255)
    fhir_base_url = models.URLField(max_length=500)
    client_id = EncryptedCharField(max_length=500, blank=True, default="")
    client_secret = EncryptedCharField(max_length=500, blank=True, default="")
    auth_type = models.CharField(
        max_length=30, choices=AuthType.choices, default=AuthType.CLIENT_CREDENTIALS
    )
    scopes = models.TextField(blank=True, default="")
    access_token = EncryptedTextField(blank=True, default="")
    refresh_token = EncryptedTextField(blank=True, default="")
    token_expires_at = models.DateTimeField(null=True, blank=True)

    # SMART on FHIR fields
    smart_authorize_url = models.URLField(max_length=500, blank=True, default="")
    smart_token_url = models.URLField(max_length=500, blank=True, default="")

    is_active = models.BooleanField(default=False)
    last_connected_at = models.DateTimeField(null=True, blank=True)
    connection_status = models.CharField(max_length=20, default="disconnected")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fhir_connections"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.display_name} ({self.ehr_system})"


class FHIRPushLog(models.Model):
    """Audit log