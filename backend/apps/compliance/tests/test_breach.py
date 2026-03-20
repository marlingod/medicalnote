from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Practice, User
from apps.compliance.models import BreachIncident


class BreachIncidentModelTest(TestCase):
    def test_notification_deadline_auto_set(self):
        detected = timezone.now()
        incident = BreachIncident.objects.create(
            title="Test breach",
            severity="high",
            detected_at=detected,
        )
        expected_deadline = detected + timedelta(days=60)
        # Compare within 1 second tolerance
        assert abs((incident.notification_deadline - expected_deadline).total_seconds()) < 1

    def test_notification_deadline_not_overwritten(self):
        detected = timezone.now()
        custom_deadline = detected + timedelta(days=30)
        incident = BreachIncident.objects.create(
            title="Test breach",
            severity="medium",
            detected_at=detected,
            notification_deadline=custom_deadline,
        )
        assert abs((incident.notification_deadline - custom_deadline).total_seconds()) < 1

    def test_str(self):
        incident = BreachIncident(
            title="PHI Exposure",
            status="detected",
            severity="critical",
        )
        assert "PHI Exposure" in str(incident)
        assert "detected" in str(incident)

    def test_default_status_is_detected(self):
        incident = BreachIncident.objects.create(
            title="New incident",
            severity="low",
            detected_at=timezone.now(),
        )
        assert incident.status == "detected"


class BreachIncidentAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.admin = User.objects.create_user(
            email="admin@test.com",
            password="SecurePass123!@#",
            role="admin",
            practice=self.practice,
        )
        self.doctor = User.objects.create_user(
            email="doctor@test.com",
            password="SecurePass123!@#",
            role="doctor",
            practice=self.practice,
        )

    def test_admin_can_create_breach(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/v1/compliance/breaches/",
            {
                "title": "Unauthorized access detected",
                "severity": "high",
                "detected_at": timezone.now().isoformat(),
                "affected_patients_count": 5,
                "phi_types_involved": ["name", "dob"],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "Unauthorized access detected"
        assert response.data["notification_deadline"] is not None

    def test_admin_can_list_breaches(self):
        self.client.force_authenticate(user=self.admin)
        BreachIncident.objects.create(
            title="Breach 1",
            severity="low",
            detected_at=timezone.now(),
        )
        response = self.client.get("/api/v1/compliance/breaches/")
        assert response.status_code == status.HTTP_200_OK

    def test_non_admin_gets_403(self):
        self.client.force_authenticate(user=self.doctor)
        response = self.client.get("/api/v1/compliance/breaches/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_notify_action(self):
        self.client.force_authenticate(user=self.admin)
        incident = BreachIncident.objects.create(
            title="Notify test",
            severity="critical",
            detected_at=timezone.now(),
        )
        response = self.client.post(
            f"/api/v1/compliance/breaches/{incident.id}/notify/",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "notified"
        assert response.data["hhs_notified_at"] is not None

    def test_breach_lifecycle(self):
        self.client.force_authenticate(user=self.admin)
        # Create
        response = self.client.post(
            "/api/v1/compliance/breaches/",
            {
                "title": "Lifecycle test",
                "severity": "medium",
                "detected_at": timezone.now().isoformat(),
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        breach_id = response.data["id"]

        # Update to investigating
        response = self.client.patch(
            f"/api/v1/compliance/breaches/{breach_id}/",
            {"status": "investigating"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "investigating"

        # Update to confirmed
        response = self.client.patch(
            f"/api/v1/compliance/breaches/{breach_id}/",
            {"status": "confirmed"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "confirmed"

        # Notify
        response = self.client.post(
            f"/api/v1/compliance/breaches/{breach_id}/notify/",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "notified"
