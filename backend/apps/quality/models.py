import uuid

from django.db import models


class QualityRule(models.Model):
    """Configurable quality/compliance rule for note evaluation."""

    class Category(models.TextChoices):
        COMPLETENESS = "completeness", "Completeness"
        BILLING = "billing", "Billing Optimization"
        COMPLIANCE = "compliance", "CMS Compliance"
        CODING = "coding", "Code Validation"

    class Severity(models.TextChoices):
        ERROR = "error", "Error"
        WARNING = "warning", "Warning"
        INFO = "info", "Info"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule_code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.COMPLETENESS
    )
    severity = models.CharField(
        max_length=10, choices=Severity.choices, default=Severity.WARNING
    )
    points = models.IntegerField(
        default=10,
        help_text="Points deducted when this rule fails",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "quality_rules"
        ordering = ["category", "rule_code"]

    def __str__(self):
        return f"{self.rule_code}: {self.name}"


class QualityScore(models.Model):
    """Aggregated quality score for a clinical note."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    encounter = models.OneToOneField(
        "encounters.Encounter",
        on_delete=models.CASCADE,
        related_name="quality_score",
    )
    clinical_note = models.OneToOneField(
        "notes.ClinicalNote",
        on_delete=models.CASCADE,
        related_name="quality_score",
    )
    overall_score = models.IntegerField(default=0)
    completeness_score = models.IntegerField(default=0)
    billing_score = models.IntegerField(default=0)
    compliance_score = models.IntegerField(default=0)
    suggested_em_level = models.CharField(max_length=10, blank=True, default="")
    suggestions = models.JSONField(default=list, blank=True)
    evaluated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "quality_scores"

    def __str__(self):
        return f"Quality {self.overall_score}/100 for {self.encounter_id}"


class QualityFinding(models.Model):
    """Individual rule evaluation result."""

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
    passed = models.BooleanField(default=True)
    message = models.TextField(blank=True, default="")
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "quality_findings"
        ordering = ["-created_at"]

    def __str__(self):
        status = "PASS" if self.passed else "FAIL"
        return f"{status}: {self.rule.rule_code}"
