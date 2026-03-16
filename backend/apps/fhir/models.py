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
        max_length=30,
        choices=AuthType.choices,
        default=AuthType.CLIENT_CREDENTIALS,
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
    """Audit log for FHIR resource push operations."""

    class PushStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        RETRYING = "retrying", "Retrying"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(
        FHIRConnection,
        on_delete=models.CASCADE,
        related_name="push_logs",
    )
    encounter = models.ForeignKey(
        "encounters.Encounter",
        on_delete=models.CASCADE,
        related_name="fhir_push_logs",
    )
    clinical_note = models.ForeignKey(
        "notes.ClinicalNote",
        on_delete=models.CASCADE,
        related_name="fhir_push_logs",
    )
    resource_type = models.CharField(max_length=50)
    fhir_resource_id = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(
        max_length=10,
        choices=PushStatus.choices,
        default=PushStatus.PENDING,
    )
    response_code = models.IntegerField(null=True, blank=True)
    response_body = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")
    retry_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fhir_push_logs"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"FHIR Push {self.resource_type} ({self.status}) "
            f"for {self.encounter_id}"
        )
