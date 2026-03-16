import hashlib
import hmac
import uuid

from django.conf import settings
from django.test import TestCase

from apps.accounts.models import Practice
from apps.patients.models import Patient


class PatientModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(
            name="Test Clinic",
            subscription_tier="solo",
        )

    def test_create_patient(self):
        patient = Patient.objects.create(
            practice=self.practice,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="+15551234567",
            date_of_birth="1990-01-15",
            language_preference="en",
        )
        assert patient.id is not None
        assert isinstance(patient.id, uuid.UUID)
        assert patient.practice == self.practice

    def test_patient_str(self):
        patient = Patient.objects.create(
            practice=self.practice,
            first_name="Jane",
            last_name="Smith",
            date_of_birth="1985-06-20",
        )
        assert "Jane" in str(patient) or "Patient" in str(patient)

    def test_patient_belongs_to_practice(self):
        patient = Patient.objects.create(
            practice=self.practice,
            first_name="Test",
            last_name="Patient",
            date_of_birth="2000-01-01",
        )
        assert patient.practice_id == self.practice.id

    def test_name_search_hash_generated(self):
        patient = Patient.objects.create(
            practice=self.practice,
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-15",
        )
        assert patient.name_search_hash is not None
        assert len(patient.name_search_hash) > 0

    def test_name_search_hash_deterministic(self):
        patient1 = Patient.objects.create(
            practice=self.practice,
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-15",
        )
        patient1_hash = patient1.name_search_hash
        # Same name should produce same hash
        normalized = "john doe"
        expected = hmac.new(
            settings.FIELD_ENCRYPTION_KEY.encode(),
            normalized.encode(),
            hashlib.sha256,
        ).hexdigest()
        assert patient1_hash == expected

    def test_email_nullable(self):
        patient = Patient.objects.create(
            practice=self.practice,
            first_name="No",
            last_name="Email",
            date_of_birth="1990-01-01",
        )
        assert patient.email in (None, "")

    def test_phone_nullable(self):
        patient = Patient.objects.create(
            practice=self.practice,
            first_name="No",
            last_name="Phone",
            date_of_birth="1990-01-01",
        )
        assert patient.phone in (None, "")
