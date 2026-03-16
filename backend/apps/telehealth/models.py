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
    modality = models.CharField(
        max_length=20, choices=Modality.choices, default=Modality.AUDIO_VIDEO
    )
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
    cpt_modifier = models.CharField(
        max_length=5, choices=CPTModifier.choices, blank=True, default=""
    )

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
