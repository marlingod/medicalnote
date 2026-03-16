import uuid

from django.db import models
from encrypted_model_fields.fields import EncryptedTextField


class PromptVersion(models.Model):
    class PromptName(models.TextChoices):
        SOAP_NOTE = "soap_note", "SOAP Note"
        PATIENT_SUMMARY = "patient_summary", "Patient Summary"
        MEDICAL_TERMS = "medical_terms", "Medical Terms"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prompt_name = models.CharField(max_length=50, choices=PromptName.choices)
    version = models.CharField(max_length=20)
    template_text = models.TextField()
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "prompt_versions"
        unique_together = [("prompt_name", "version")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.prompt_name} v{self.version}"


class ClinicalNote(models.Model):
    class NoteType(models.TextChoices):
        SOAP = "soap", "SOAP"
        FREE_TEXT = "free_text", "Free Text"
        H_AND_P = "h_and_p", "History & Physical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    encounter = models.OneToOneField(
        "encounters.Encounter",
        on_delete=models.CASCADE,
        related_name="clinical_note",
    )
    note_type = models.CharField(max_length=20, choices=NoteType.choices, default=NoteType.SOAP)
    subjective = EncryptedTextField(blank=True, default="")
    objective = EncryptedTextField(blank=True, default="")
    assessment = EncryptedTextField(blank=True, default="")
    plan = EncryptedTextField(blank=True, default="")
    raw_content = EncryptedTextField(blank=True, default="")
    icd10_codes = models.JSONField(default=list, blank=True)
    cpt_codes = models.JSONField(default=list, blank=True)
    ai_generated = models.BooleanField(default=False)
    doctor_edited = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_notes",
    )
    prompt_version = models.ForeignKey(
        PromptVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clinical_notes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clinical_notes"

    def __str__(self):
        return f"Note for {self.encounter_id}"
