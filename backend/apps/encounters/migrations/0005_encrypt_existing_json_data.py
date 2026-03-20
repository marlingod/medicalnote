"""Data migration: Encrypt existing plain JSON in speaker_segments and medical_terms_detected."""
import json

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import migrations


def encrypt_existing_data(apps, schema_editor):
    """Read plain JSON, encrypt it with Fernet, write back."""
    Transcript = apps.get_model("encounters", "Transcript")
    key = settings.FIELD_ENCRYPTION_KEY
    if isinstance(key, str):
        key = key.encode()
    f = Fernet(key)

    for transcript in Transcript.objects.all().iterator():
        changed = False
        for field_name in ("speaker_segments", "medical_terms_detected"):
            value = getattr(transcript, field_name)
            if value is None:
                continue
            # If it's already a Fernet token (starts with 'gAAAAA'), skip
            if isinstance(value, str) and value.startswith("gAAAAA"):
                continue
            # If it's a Python object (list/dict), JSON-serialize then encrypt
            if isinstance(value, (list, dict)):
                encrypted = f.encrypt(json.dumps(value).encode()).decode()
            elif isinstance(value, str):
                # Plain JSON string — try to parse to validate, then encrypt
                try:
                    json.loads(value)
                    encrypted = f.encrypt(value.encode()).decode()
                except json.JSONDecodeError:
                    continue
            else:
                continue
            # Use raw SQL update to bypass the field's get_prep_value (which would double-encrypt)
            Transcript.objects.filter(pk=transcript.pk).update(**{field_name: encrypted})
            changed = True


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("encounters", "0004_alter_transcript_medical_terms_detected_and_more"),
    ]

    operations = [
        migrations.RunPython(encrypt_existing_data, noop),
    ]
