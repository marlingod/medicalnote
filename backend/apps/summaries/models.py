import uuid

from django.db import models
from encrypted_model_fields.fields import EncryptedTextField

from apps.core.fields import EncryptedJSONField


class PatientSummary(models.Model):
    class ReadingLevel(models.TextChoices):
        GRADE_5 = "grade_5", "Grade 5"
        GRADE_8 = "grade_8", "Grade 8"
        GRADE_12 = "grade_12", "Grade 12"

    class DeliveryStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        VIEWED = "viewed", "Viewed"
        FAILED = "failed", "Failed"

    class DeliveryMethod(models.TextChoices):
        APP = "app", "App"
        WIDGET = "widget", "Widget"
        SMS_LINK = "sms_link", "SMS Link"
        EMAIL_LINK = "email_link", "Email Link"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    encounter = models.OneToOneField(
        "encounters.Encounter",
        on_delete=models.CASCADE,
        related_name="patient_summary",
    )
    clinical_note = models.ForeignKey(
        "notes.ClinicalNote",
        on_delete=models.CASCADE,
        related_name="summaries",
    )
    summary_en = EncryptedTextField()
    summary_es = EncryptedTextField(blank=True, default="")
    reading_level = models.CharField(
        max_length=10,
        choices=ReadingLevel.choices,
        default=ReadingLevel.GRADE_8,
    )
    medical_terms_explained = EncryptedJSONField(default=list, blank=True)
    disclaimer_text = models.TextField(
        default="This summary is for informational purposes only and does not constitute medical advice."
    )
    delivery_status = models.CharField(
        max_length=10,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
    )
    delivered_at = models.DateTimeField(null=True, blank=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    delivery_method = models.CharField(
        max_length=20,
        choices=DeliveryMethod.choices,
        blank=True,
        default="",
    )
    prompt_version = models.ForeignKey(
        "notes.PromptVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patient_summaries",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "patient_summaries"
        verbose_name_plural = "Patient summaries"

    def __str__(self):
        return f"Summary for {self.encounter_id}"
