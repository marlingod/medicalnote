import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone


class BusinessAssociateAgreement(models.Model):
    class VendorType(models.TextChoices):
        CLOUD = "cloud", "Cloud Provider"
        AI = "ai", "AI Provider"
        COMMUNICATION = "communication", "Communication Provider"
        DATABASE = "database", "Database Provider"
        ANALYTICS = "analytics", "Analytics Provider"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        TERMINATED = "terminated", "Terminated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor_name = models.CharField(max_length=255)
    vendor_type = models.CharField(max_length=20, choices=VendorType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    effective_date = models.DateField()
    expiration_date = models.DateField()
    scope_description = models.TextField(blank=True, default="")
    document_s3_key = models.CharField(max_length=500, blank=True, default="")
    document_hash = models.CharField(max_length=128, blank=True, default="")
    breach_notification_hours = models.IntegerField(default=72)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "business_associate_agreements"
        ordering = ["-effective_date"]

    def __str__(self):
        return f"BAA: {self.vendor_name} ({self.status})"

    @property
    def is_expiring_soon(self):
        return (
            self.status == self.Status.ACTIVE
            and self.expiration_date <= (timezone.now().date() + timedelta(days=90))
        )


class BreachIncident(models.Model):
    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        DETECTED = "detected", "Detected"
        INVESTIGATING = "investigating", "Investigating"
        CONFIRMED = "confirmed", "Confirmed"
        NOTIFIED = "notified", "Notified"
        RESOLVED = "resolved", "Resolved"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500)
    severity = models.CharField(max_length=10, choices=Severity.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DETECTED)
    detected_at = models.DateTimeField(default=timezone.now)
    affected_patients_count = models.IntegerField(default=0)
    phi_types_involved = models.JSONField(default=list, blank=True)
    notification_deadline = models.DateTimeField(blank=True, null=True)
    hhs_notified_at = models.DateTimeField(null=True, blank=True)
    patients_notified_at = models.DateTimeField(null=True, blank=True)
    remediation_steps = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "breach_incidents"
        ordering = ["-detected_at"]

    def __str__(self):
        return f"Breach: {self.title} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.notification_deadline:
            self.notification_deadline = self.detected_at + timedelta(days=60)
        super().save(*args, **kwargs)
