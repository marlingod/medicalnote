import uuid

from django.core.exceptions import PermissionDenied
from django.db import models


class AuditLog(models.Model):
    class Action(models.TextChoices):
        VIEW = "view", "View"
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        EXPORT = "export", "Export"
        SHARE = "share", "Share"
        LOGIN_FAILED = "login_failed", "Login Failed"
        BREAK_GLASS = "break_glass", "Break Glass"
        DISCLOSE = "disclose", "Disclose"

    class ResourceType(models.TextChoices):
        PATIENT = "patient", "Patient"
        ENCOUNTER = "encounter", "Encounter"
        NOTE = "note", "Note"
        SUMMARY = "summary", "Summary"
        RECORDING = "recording", "Recording"
        TEMPLATE = "template", "Template"
        QUALITY_SCORE = "quality_score", "Quality Score"
        TELEHEALTH = "telehealth", "Telehealth"
        FHIR_PUSH = "fhir_push", "FHIR Push"
        DISCLOSURE = "disclosure", "Disclosure"

    class Outcome(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILURE = "failure", "Failure"
        ERROR = "error", "Error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="audit_logs",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    resource_type = models.CharField(max_length=20, choices=ResourceType.choices)
    resource_id = models.UUIDField()
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, default="")
    phi_accessed = models.BooleanField(default=False)
    details = models.JSONField(default=dict, blank=True)
    outcome = models.CharField(
        max_length=10,
        choices=Outcome.choices,
        default=Outcome.SUCCESS,
    )
    user_role = models.CharField(max_length=20, blank=True, default="")
    session_id = models.CharField(max_length=64, blank=True, default="")
    source_system = models.CharField(max_length=50, default="api")
    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created_at"]
        # No update or delete permissions
        default_permissions = ("add", "view")

    def __str__(self):
        user_desc = self.user_id or "anonymous"
        return f"{self.action} {self.resource_type} by {user_desc} at {self.created_at}"

    def save(self, *args, **kwargs):
        if self._state.adding:
            super().save(*args, **kwargs)
        else:
            raise PermissionDenied("Audit logs are append-only and cannot be modified.")

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Audit logs cannot be deleted.")


class BreakGlassAccess(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="break_glass_accesses",
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="break_glass_accesses",
    )
    reason = models.TextField()
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="break_glass_approvals",
    )
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "break_glass_accesses"
        ordering = ["-created_at"]

    def __str__(self):
        return f"BreakGlass by {self.user_id} for patient {self.patient_id}"
