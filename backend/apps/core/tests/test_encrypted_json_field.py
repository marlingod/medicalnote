import json

from django.db import connection
from django.test import TestCase, override_settings

from apps.core.fields import EncryptedJSONField


class EncryptedJSONFieldTest(TestCase):
    def setUp(self):
        self.field = EncryptedJSONField()

    def test_round_trip_list(self):
        """Encrypt then decrypt a JSON list."""
        original = ["ICD10:J06.9", "ICD10:R05"]
        encrypted = self.field.get_prep_value(original)
        # Encrypted value should not be plain JSON
        self.assertNotEqual(encrypted, json.dumps(original))
        # Decrypt
        decrypted = self.field.from_db_value(encrypted, None, connection)
        self.assertEqual(decrypted, original)

    def test_round_trip_dict(self):
        """Encrypt then decrypt a JSON dict."""
        original = {"term": "hypertension", "explanation": "high blood pressure"}
        encrypted = self.field.get_prep_value(original)
        self.assertNotEqual(encrypted, json.dumps(original))
        decrypted = self.field.from_db_value(encrypted, None, connection)
        self.assertEqual(decrypted, original)

    def test_none_values_pass_through(self):
        """None should remain None through encrypt/decrypt."""
        self.assertIsNone(self.field.get_prep_value(None))
        self.assertIsNone(self.field.from_db_value(None, None, connection))

    def test_fallback_for_plain_json(self):
        """Pre-migration plain JSON data should be readable (fallback)."""
        plain_json = json.dumps(["code1", "code2"])
        result = self.field.from_db_value(plain_json, None, connection)
        self.assertEqual(result, ["code1", "code2"])

    def test_empty_list_round_trip(self):
        """Empty list should survive round-trip."""
        original = []
        encrypted = self.field.get_prep_value(original)
        decrypted = self.field.from_db_value(encrypted, None, connection)
        self.assertEqual(decrypted, original)

    def test_nested_structure_round_trip(self):
        """Nested JSON structures should survive round-trip."""
        original = [
            {"term": "HTN", "explanation": "High blood pressure", "codes": ["I10"]},
            {"term": "DM2", "explanation": "Type 2 diabetes", "codes": ["E11.9"]},
        ]
        encrypted = self.field.get_prep_value(original)
        decrypted = self.field.from_db_value(encrypted, None, connection)
        self.assertEqual(decrypted, original)
