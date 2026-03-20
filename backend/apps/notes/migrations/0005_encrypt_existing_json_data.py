"""Data migration: Encrypt existing plain JSON in icd10_codes and cpt_codes."""
import json

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import migrations


def encrypt_existing_data(apps, schema_editor):
    """Read plain JSON, encrypt it with Fernet, write back."""
    ClinicalNote = apps.get_model("notes", "ClinicalNote")
    key = settings.FIELD_ENCRYPTION_KEY
    if isinstance(key, str):
        key = key.encode()
    f = Fernet(key)

    for note in ClinicalNote.objects.all().iterator():
        for field_name in ("icd10_codes", "cpt_codes"):
            value = getattr(note, field_name)
            if value is None:
                continue
            if isinstance(value, str) and value.startswith("gAAAAA"):
                continue
            if isinstance(value, (list, dict)):
                encrypted = f.encrypt(json.dumps(value).encode()).decode()
            elif isinstance(value, str):
                try:
                    json.loads(value)
                    encrypted = f.encrypt(value.encode()).decode()
                except json.JSONDecodeError:
                    continue
            else:
                continue
            ClinicalNote.objects.filter(pk=note.pk).update(**{field_name: encrypted})


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("notes", "0004_alter_clinicalnote_cpt_codes_and_more"),
    ]

    operations = [
        migrations.RunPython(encrypt_existing_data, noop),
    ]
