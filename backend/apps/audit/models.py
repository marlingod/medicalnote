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

    class ResourceType(models.TextChoices):
        PATIENT = "patient", "Patient"
        ENCOUNTER = "encounter", "Encounter"
        NOTE = "note", "Note"
        SUMMARY = "summary", "Summary"
        RECORDING = "recording", "Recording"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=10, choices=Action.choices)
    resource_type = models.CharField(max_length=20, choices=ResourceType.choices)
    resource_id = models.UUIDField()
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, default="")
    phi_accessed = models.BooleanField(default=False)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created_at"]
        # No update or delete permissions
        default_permissions = ("add", "view")

    def __str__(self):
        return f"{self.action} {self.resource_type} by {self.user_id} at {self.created_at}"

    def save(self, *args, **kwargs):
        if self._state.adding:
            super().save(*args, **kwargs)
        else:
            raise PermissionDenied("Audit logs are append-only and cannot be modified.")

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Audit logs cannot be deleted.")
