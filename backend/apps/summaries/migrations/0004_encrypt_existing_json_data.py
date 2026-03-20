"""Data migration: Encrypt existing plain JSON in medical_terms_explained."""
import json

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import migrations


def encrypt_existing_data(apps, schema_editor):
    """Read plain JSON, encrypt it with Fernet, write back."""
    PatientSummary = apps.get_model("summaries", "PatientSummary")
    key = settings.FIELD_ENCRYPTION_KEY
    if isinstance(key, str):
        key = key.encode()
    f = Fernet(key)

    for summary in PatientSummary.objects.all().iterator():
        value = summary.medical_terms_explained
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
                return
        else:
            continue
        PatientSummary.objects.filter(pk=summary.pk).update(medical_terms_explained=encrypted)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("summaries", "0003_alter_patientsummary_medical_terms_explained"),
    ]

    operations = [
        migrations.RunPython(encrypt_existing_data, noop),
    ]
