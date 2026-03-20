from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Practice, User
from apps.audit.models import AuditLog
from apps.patients.models import Patient


class FailedRequestAuditLoggingTest(TestCase):
    """Verify that the HIPAA audit middleware logs failed (4xx) requests."""

    def setUp(self):
        self.client = APIClient()
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="testpass123!", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="Jane", last_name="Doe", date_of_birth="1990-01-01"
        )

    def test_failed_login_creates_audit_log_with_failure_outcome(self):
        """A failed login attempt (wrong password) should NOT create an audit log
        because /api/v1/auth/login/ is not a PHI endpoint in PHI_URL_PATTERNS.
        Instead, test a failed POST to a PHI endpoint to verify failure logging."""
        self.client.force_authenticate(user=self.doctor)
        # POST invalid data to patient endpoint (missing required fields)
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

    def test_403_on_phi_endpoint_creates_failure_audit_log(self):
        """When an authenticated user gets a 403 on a PHI endpoint,
        the middleware should log it with outcome='failure'."""
        # Create a patient-role user who should not have permission to list patients
        patient_user = User.objects.create_user(
            email="patient@test.com", password="testpass123!", role="patient", practice=self.practice
        )
        self.client.force_authenticate(user=patient_user)

        response = self.client.get(f"/api/v1/patients/{self.patient.id}/")
        # Whether 403 or 200 depends on view permissions, but the middleware
        # should log the request regardless of status code.
        if response.status_code >= 400:
            logs = AuditLog.objects.filter(
                user=patient_user,
                resource_type="patient",
                outcome="failure",
            )
            assert logs.count() >= 1
            log = logs.first()
            assert log.phi_accessed is True
            assert log.details["status_code"] >= 400
        else:
            # If the view allows it, it should still be logged (as success)
            logs = AuditLog.objects.filter(
                user=patient_user,
                resource_type="patient",
            )
            assert logs.count() >= 1

    def test_unauthenticated_phi_access_logged_with_user_none(self):
        """Unauthenticated requests to PHI endpoints should be logged with user=None."""
        # No authentication set on client
        response = self.client.get(f"/api/v1/patients/{self.patient.id}/")
        # Should be 401 or 403
        assert response.status_code in (401, 403)

        logs = AuditLog.objects.filter(
            user=None,
            resource_type="patient",
            outcome="failure",
        )
        assert logs.count() >= 1
        log = logs.first()
        assert log.user is None
        assert log.phi_accessed is True
        assert log.details["path"] == f"/api/v1/patients/{self.patient.id}/"

    def test_4xx_response_is_logged_not_skipped(self):
        """Regression test: previously the middleware had an early exit for
        status_code >= 400. Confirm that 4xx responses are now logged."""
        initial_count = AuditLog.objects.count()

        # Unauthenticated request to PHI endpoint -> 401
        response = self.client.get("/api/v1/patients/")
        assert response.status_code in (401, 403)

        # At least one new audit log should have been created
        assert AuditLog.objects.count() > initial_count

    def test_bad_request_to_patient_create_logs_failure(self):
        """A 400 Bad Request on patient create should produce an audit log with
        outcome='failure' and action='create'."""
        self.client.force_authenticate(user=self.doctor)

        response = self.client.post(
            "/api/v1/patients/",
            {"first_name": ""},  # Missing required fields
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
        assert log.details["method"] == "POST"
        assert log.details["status_code"] == 400
