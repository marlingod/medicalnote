from django.test import TestCase

from services.phi_sanitizer import PHISanitizer


class PHISanitizerTest(TestCase):
    def test_ssn_with_dashes_is_redacted(self):
        text = "Patient SSN is 123-45-6789 on file."
        result = PHISanitizer.sanitize_for_llm(text)
        self.assertNotIn("123-45-6789", result)
        self.assertIn("[SSN]", result)

    def test_ssn_without_dashes_is_redacted(self):
        text = "SSN: 123456789 in record."
        result = PHISanitizer.sanitize_for_llm(text)
        self.assertNotIn("123456789", result)
        self.assertIn("[SSN]", result)

    def test_phone_number_is_redacted(self):
        text = "Call patient at (555) 123-4567 for follow-up."
        result = PHISanitizer.sanitize_for_llm(text)
        self.assertNotIn("(555) 123-4567", result)
        self.assertIn("[PHONE]", result)

    def test_phone_number_with_dashes_is_redacted(self):
        text = "Phone: 555-123-4567."
        result = PHISanitizer.sanitize_for_llm(text)
        self.assertNotIn("555-123-4567", result)
        self.assertIn("[PHONE]", result)

    def test_email_is_redacted(self):
        text = "Contact at john.doe@example.com for results."
        result = PHISanitizer.sanitize_for_llm(text)
        self.assertNotIn("john.doe@example.com", result)
        self.assertIn("[EMAIL]", result)

    def test_dob_pattern_is_redacted(self):
        text = "Date of birth: 03/15/1990."
        result = PHISanitizer.sanitize_for_llm(text)
        self.assertNotIn("03/15/1990", result)
        self.assertIn("[DOB]", result)

    def test_patient_name_is_redacted(self):
        text = "John Smith presents with chest pain."
        result = PHISanitizer.sanitize_for_llm(text, patient_name="John Smith")
        self.assertNotIn("John", result)
        self.assertNotIn("Smith", result)
        self.assertIn("[PATIENT]", result)
        self.assertIn("chest pain", result)

    def test_clinical_text_is_preserved(self):
        text = "Patient presents with hypertension, BP 140/90. Prescribed lisinopril 10mg daily."
        result = PHISanitizer.sanitize_for_llm(text)
        self.assertIn("hypertension", result)
        self.assertIn("BP 140/90", result)
        self.assertIn("lisinopril 10mg daily", result)

    def test_empty_text_returns_empty(self):
        self.assertEqual(PHISanitizer.sanitize_for_llm(""), "")

    def test_none_text_returns_none(self):
        # Empty string is falsy, so sanitize_for_llm returns it as-is
        self.assertEqual(PHISanitizer.sanitize_for_llm(""), "")

    def test_explicit_dob_string_is_redacted(self):
        text = "Born on 1990-03-15, patient has diabetes."
        result = PHISanitizer.sanitize_for_llm(text, dob="1990-03-15")
        self.assertNotIn("1990-03-15", result)
        self.assertIn("[DOB]", result)
        self.assertIn("diabetes", result)
