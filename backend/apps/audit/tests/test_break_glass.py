import uuid

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import Practice, User
from apps.audit.models import AuditLog, BreakGlassAccess
from apps.patients.models import Patient


class BreakGlassRequestViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="SecurePass123!@#", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice,
            first_name="Jane",
            last_name="Doe",
            date_of_birth="1990-01-15",
        )

    def test_break_glass_creates_access_record_and_audit_log(self):
        self.client.force_authenticate(user=self.doctor)
        response = self.client.post(
            "/api/v1/audit/break-glass/",
            {
                "patient_id": str(self.patient.id),
                "reason": "Emergency - patient arrived unconscious, need medical history.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertIn("expires_at", response.data)

        # Verify BreakGlassAccess record was created
        access = BreakGlassAccess.objects.filter(user=self.doctor, patient=self.patient)
        self.assertTrue(access.exists())
        self.assertEqual(access.first().reason, "Emergency - patient arrived unconscious, need medical history.")

        # Verify AuditLog entry
        audit = AuditLog.objects.filter(
            user=self.doctor,
            action=AuditLog.Action.BREAK_GLASS,
            resource_id=self.patient.id,
        )
        self.assertTrue(audit.exists())
        self.assertTrue(audit.first().phi_accessed)

    def test_break_glass_reason_must_be_at_least_10_chars(self):
        self.client.force_authenticate(user=self.doctor)
        response = self.client.post(
            "/api/v1/audit/break-glass/",
            {
                "patient_id": str(self.patient.id),
                "reason": "Short",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_break_glass_requires_patient_id(self):
        self.client.force_authenticate(user=self.doctor)
        response = self.client.post(
            "/api/v1/audit/break-glass/",
            {
                "reason": "Emergency - patient needs urgent care access.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.post(
            "/api/v1/audit/break-glass/",
            {
                "patient_id": str(self.patient.id),
                "reason": "Emergency - patient arrived unconscious.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
