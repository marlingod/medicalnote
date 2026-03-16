import hashlib
import hmac
import uuid

from django.conf import settings
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField, EncryptedDateField


class Patient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    practice = models.ForeignKey(
        "accounts.Practice",
        on_delete=models.CASCADE,
        related_name="patients",
    )
    first_name = EncryptedCharField(max_length=150)
    last_name = EncryptedCharField(max_length=150)
    name_search_hash = models.CharField(max_length=64, db_index=True, blank=True, default="")
    email = EncryptedCharField(max_length=254, blank=True, default="")
    phone = EncryptedCharField(max_length=20, blank=True, default="")
    date_of_birth = EncryptedDateField()
    language_preference = models.CharField(max_length=5, default="en")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "patients"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Patient {self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        self._generate_name_search_hash()
        super().save(*args, **kwargs)

    def _generate_name_search_hash(self):
        """Generate HMAC-SHA256 blind index from normalized name for searchability."""
        normalized = f"{self.first_name} {self.last_name}".strip().lower()
        self.name_search_hash = hmac.new(
            settings.FIELD_ENCRYPTION_KEY.encode(),
            normalized.encode(),
            hashlib.sha256,
        ).hexdigest()
