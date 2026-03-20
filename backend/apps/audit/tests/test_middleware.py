from datetime import date
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import Practice, User
from apps.audit.models import AuditLog
from apps.patients.models import Patient


class HIPAAAuditMiddlewareTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D", date_of_birth="1990-01-01"
        )
        self.client.force_authenticate(user=self.doctor)

    def test_phi_access_logged_on_patient_view(self):
        response = self.client.get(f"/api/v1/patients/{self.patient.id}/")
        assert response.status_code == 200
        logs = AuditLog.objects.filter(
            user=self.doctor, resource_type="patient", action="view"
        )
        assert logs.count() >= 1

    def test_phi_access_logged_on_patient_create(self):
        response = self.client.post(
            "/api/v1/patients/",
            {"first_name": "New", "last_name": "Patient", "date_of_birth": "1995-01-01"},
            format="json",
        )
        assert response.status_code == 201
        logs = AuditLog.objects.filter(
            user=self.doctor, resource_type="patient", action="create"
        )
        assert logs.count() >= 1

    def test_no_log_for_non_phi_endpoints(self):
        initial_count = AuditLog.objects.count()
        self.client.get("/admin/")  # Non-PHI endpoint
        # Middleware should not log admin panel
        assert AuditLog.objects.count() == initial_count

    def test_failed_request_is_logged(self):
        """Regression: middleware previously had early exit for status >= 400.
        Verify that 4xx responses on PHI endpoints now create audit logs."""
        # Force-authenticate so we isolate the 400 from the view, not auth
        self.client.force_authenticate(user=self.doctor)
        # Submit an invalid patient create (missing required fields)
        response = self.client.post(
            "/api/v1/patients/",
            {},
            format="json",
        )
        assert response.status_code == 400
        logs = AuditLog.objects.filter(
            user=self.doctor,
            resource_type="patient",
            action="create",
            outcome="failure",
        )
        assert logs.count() >= 1
        log = logs.first()
        assert log.phi_accessed is True
        assert log.details["status_code"] == 400

    def test_unauthenticated_request_to_phi_endpoint_is_logged(self):
        """Unauthenticated requests to PHI endpoints should be logged with user=None."""
        unauthenticated_client = APIClient()
        response = unauthenticated_client.get(f"/api/v1/patients/{self.patient.id}/")
        assert response.status_code in (401, 403)
        logs = AuditLog.objects.filter(
            user=None,
            resource_type="patient",
            outcome="failure",
        )
        assert logs.count() >= 1
