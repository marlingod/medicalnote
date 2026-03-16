import uuid
from django.db import models


class MedicalSpecialty(models.TextChoices):
    PRIMARY_CARE = "primary_care", "Primary Care"
    DERMATOLOGY = "dermatology", "Dermatology"
    PSYCHIATRY = "psychiatry", "Psychiatry"
    CARDIOLOGY = "cardiology", "Cardiology"
    ORTHOPEDICS = "orthopedics", "Orthopedics"
    PEDIATRICS = "pediatrics", "Pediatrics"
    NEUROLOGY = "neurology", "Neurology"
    GASTROENTEROLOGY = "gastroenterology", "Gastroenterology"
    GENERAL = "general", "General"


class NoteTemplate(models.Model):
    """A clinical note template with structured sections and specialty-specific fields."""

    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        PRACTICE = "practice", "Practice"
        PUBLIC = "public", "Public (Marketplace)"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    specialty = models.CharField(
        max_length=30, choices=MedicalSpecialty.choices, default=MedicalSpecialty.GENERAL
    )
    note_type = models.CharField(
        max_length=20,
        choices=[("soap", "SOAP"), ("free_text", "Free Text"), ("h_and_p", "H&P")],
        default="soap",
    )

    # Template schema: sections, fields, conditional logic, default values
    schema = models.JSONField(default=dict)

    # Ownership and visibility
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="created_templates"
    )
    practice = models.ForeignKey(
        "accounts.Practice", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="templates"
    )
    visibility = models.CharField(
        max_length=10, choices=Visibility.choices, default=Visibility.PRIVATE
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT
    )

    # Version control
    version = models.PositiveIntegerField(default=1)
    parent_template = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="derived_templates"
    )

    # Marketplace metadata
    tags = models.JSONField(default=list, blank=True)
    use_count = models.PositiveIntegerField(default=0)
    clone_count = models.PositiveIntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "note_templates"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["specialty", "status"]),
            models.Index(fields=["visibility", "status"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.specialty})"


class TemplateRating(models.Model):
    """Doctor ratings for marketplace templates."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        NoteTemplate, on_delete=models.CASCADE, related_name="ratings"
    )
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="template_ratings"
    )
    score = models.PositiveSmallIntegerField()  # 1-5
    review = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "template_ratings"
        unique_together = [("template", "user")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Rating {self.score}/5 for {self.template.name} by {self.user.email}"


class TemplateFavorite(models.Model):
    """Bookmarked/favorited templates for quick access."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        NoteTemplate, on_delete=models.CASCADE, related_name="favorites"
    )
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="template_favorites"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "template_favorites"
        unique_together = [("template", "user")]
