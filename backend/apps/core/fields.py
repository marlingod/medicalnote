import json

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models
from rest_framework import serializers as drf_serializers


class EncryptedJSONField(models.TextField):
    """Encrypts JSON data at rest using Fernet (AES-128-CBC + HMAC-SHA256).

    Stores data as Fernet-encrypted text in the DB but presents native
    Python objects (list/dict) to application code and DRF serializers.
    """

    description = "Fernet-encrypted JSON field"

    def __init__(self, *args, default=None, **kwargs):
        if default is None:
            default = list
        super().__init__(*args, default=default, **kwargs)

    def _get_fernet(self):
        key = settings.FIELD_ENCRYPTION_KEY
        if isinstance(key, str):
            key = key.encode()
        return Fernet(key)

    def get_prep_value(self, value):
        if value is None:
            return None
        json_str = json.dumps(value)
        return self._get_fernet().encrypt(json_str.encode()).decode()

    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        try:
            decrypted = self._get_fernet().decrypt(value.encode()).decode()
            return json.loads(decrypted)
        except Exception:
            # Fallback: try parsing as plain JSON (for pre-migration data)
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

    def value_from_object(self, obj):
        """Return native Python value for serialization (DRF, dumpdata, etc.)."""
        return getattr(obj, self.attname)

    def value_to_string(self, obj):
        """Return JSON string for serialization."""
        value = self.value_from_object(obj)
        return json.dumps(value)

    def formfield(self, **kwargs):
        """Use JSONField's formfield so DRF ModelSerializer maps this correctly."""
        return models.JSONField().formfield(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return name, path, args, kwargs


# Register DRF serializer field mapping so ModelSerializer uses JSONField, not CharField
drf_serializers.ModelSerializer.serializer_field_mapping[EncryptedJSONField] = drf_serializers.JSONField
