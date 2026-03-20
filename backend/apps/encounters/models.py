import uuid

from django.db import models
from encrypted_model_fields.fields import EncryptedCharField, EncryptedTextField

from apps.core.fields import EncryptedJSONField


class Encounter(models.Model):
    class InputMethod(models.TextChoices):
        RECORDING = "recording", "Recording"
        PASTE = "paste", "Paste"
        DICTATION = "dictation", "Dictation"
        SCAN = "scan", "Scan"
        TELEHEALTH = "telehealth", "Telehealth"

    class Status(models.TextChoices):
        UPLOADING = "uploading", "Uploading"
        TRANSCRIBING = "transcribing", "Transcribing"
        GENERATING_NOTE = "generating_note", "Generating Note"
        GENERATING_SUMMARY = "generating_summary", "Generating Summary"
        READY_FOR_REVIEW = "ready_for_review", "Ready for Review"
        APPROVED = "approved", "Approved"
        DELIVERED = "delivered", "Delivered"
        TRANSCRIPTION_FAILED = "transcription_failed", "Transcription Failed"
        NOTE_GENERATION_FAILED = "note_generation_failed", "Note Generation Failed"
        SUMMARY_GENERATION_FAILED = "summary_generation_failed", "Summary Generation Failed"
        QUALITY_CHECKING = "quality_checking", "Quality Checking"

    class ConsentMethod(models.TextChoices):
        VERBAL = "verbal", "Verbal"
        DIGITAL_CHECKBOX = "digital_checkbox", "Digital Checkbox"
        WRITTEN = "written", "Written"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="encounters",
        limit_choices_to={"role": "doctor"},
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="encounters",
    )
    encounter_date = models.DateField()
    input_method = models.CharField(max_length=20, choices=InputMethod.choices)
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.UPLOADING,
    )
    consent_recording = models.BooleanField(default=False)
    consent_timestamp = models.DateTimeField(null=True, blank=True)
    consent_method = models.CharField(
        max_length=20,
        choices=ConsentMethod.choices,
        blank=True,
        default="",
    )
    consent_jurisdiction_state = models.CharField(max_length=2, blank=True, default="")
    template_used = models.ForeignKey(
        "note_templates.NoteTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="encounters",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "encounters"
        ordering = ["-encounter_date", "-created_at"]

    def __str__(self):
        return f"Encounter {self.id} - {self.encounter_date}"


class Recording(models.Model):
    class Format(models.TextChoices):
        WAV = "wav", "WAV"
        MP3 = "mp3", "MP3"
        WEBM = "webm", "WebM"

    class TranscriptionStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    encounter = models.OneToOneField(
        Encounter,
        on_delete=models.CASCADE,
        related_name="recording",
    )
    storage_url = EncryptedCharField(max_length=500)
    duration_seconds = models.IntegerField(default=0)
    file_size_bytes = models.BigIntegerField(default=0)
    format = models.CharField(max_length=10, choices=Format.choices)
    transcription_status = models.CharField(
        max_length=20,
        choices=TranscriptionStatus.choices,
        default=TranscriptionStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "recordings"

    def __str__(self):
        return f"Recording for {self.encounter_id}"


class Transcript(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    encounter = models.OneToOneField(
        Encounter,
        on_delete=models.CASCADE,
        related_name="transcript",
    )
    raw_text = EncryptedTextField()
    speaker_segments = EncryptedJSONField(default=list)
    medical_terms_detected = EncryptedJSONField(default=list)
    confidence_score = models.FloatField(default=0.0)
    language_detected = models.CharField(max_length=10, default="en")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "transcripts"

    def __str__(self):
        return f"Transcript for {self.encounter_id}"
