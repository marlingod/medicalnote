from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Practice, User
from apps.compliance.models import BusinessAssociateAgreement


class BAAModelTest(TestCase):
    def test_is_expiring_soon_true(self):
        baa = BusinessAssociateAgreement(
            vendor_name="Test Vendor",
            vendor_type="cloud",
            status="active",
            effective_date=date.today() - timedelta(days=300),
            expiration_date=date.today() + timedelta(days=30),
        )
        assert baa.is_expiring_soon is True

    def test_is_expiring_soon_false_when_far_out(self):
        baa = BusinessAssociateAgreement(
            vendor_name="Test Vendor",
            vendor_type="cloud",
            status="active",
            effective_date=date.today() - timedelta(days=100),
            expiration_date=date.today() + timedelta(days=180),
        )
        assert baa.is_expiring_soon is False

    def test_is_expiring_soon_false_when_not_active(self):
        baa = BusinessAssociateAgreement(
            vendor_name="Test Vendor",
            vendor_type="cloud",
            status="draft",
            effective_date=date.today(),
            expiration_date=date.today() + timedelta(days=10),
        )
        assert baa.is_expiring_soon is False

    def test_str(self):
        baa = BusinessAssociateAgreement(
            vendor_name="Acme Corp",
            status="active",
            vendor_type="ai",
            effective_date=date.today(),
            expiration_date=date.today() + timedelta(days=365),
        )
        assert "Acme Corp" in str(baa)
        assert "active" in str(baa)


class BAAAPITest(TestCase):
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
        self.baa_data = {
            "vendor_name": "AWS",
            "vendor_type": "cloud",
            "status": "active",
            "effective_date": str(date.today()),
            "expiration_date": str(date.today() + timedelta(days=365)),
            "scope_description": "Cloud infrastructure",
            "breach_notification_hours": 72,
        }

    def test_admin_can_create_baa(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/v1/compliance/baa/",
            self.baa_data,
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["vendor_name"] == "AWS"

    def test_admin_can_list_baas(self):
        self.client.force_authenticate(user=self.admin)
        BusinessAssociateAgreement.objects.create(
            vendor_name="AWS",
            vendor_type="cloud",
            status="active",
            effective_date=date.today(),
            expiration_date=date.today() + timedelta(days=365),
        )
        response = self.client.get("/api/v1/compliance/baa/")
        assert response.status_code == status.HTTP_200_OK

    def test_admin_can_update_baa(self):
        self.client.force_authenticate(user=self.admin)
        baa = BusinessAssociateAgreement.objects.create(
            vendor_name="AWS",
            vendor_type="cloud",
            status="active",
            effective_date=date.today(),
            expiration_date=date.today() + timedelta(days=365),
        )
        response = self.client.patch(
            f"/api/v1/compliance/baa/{baa.id}/",
            {"status": "terminated"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        baa.refresh_from_db()
        assert baa.status == "terminated"

    def test_admin_can_delete_baa(self):
        self.client.force_authenticate(user=self.admin)
        baa = BusinessAssociateAgreement.objects.create(
            vendor_name="AWS",
            vendor_type="cloud",
            status="draft",
            effective_date=date.today(),
            expiration_date=date.today() + timedelta(days=365),
        )
        response = self.client.delete(f"/api/v1/compliance/baa/{baa.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_non_admin_gets_403(self):
        self.client.force_authenticate(user=self.doctor)
        response = self.client.get("/api/v1/compliance/baa/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_gets_401_or_403(self):
        response = self.client.get("/api/v1/compliance/baa/")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_expiring_endpoint(self):
        self.client.force_authenticate(user=self.admin)
        BusinessAssociateAgreement.objects.create(
            vendor_name="Expiring Vendor",
            vendor_type="ai",
            status="active",
            effective_date=date.today() - timedelta(days=300),
            expiration_date=date.today() + timedelta(days=30),
        )
        BusinessAssociateAgreement.objects.create(
            vendor_name="Safe Vendor",
            vendor_type="cloud",
            status="active",
            effective_date=date.today(),
            expiration_date=date.today() + timedelta(days=365),
        )
        response = self.client.get("/api/v1/compliance/baa/expiring/")
        assert response.status_code == status.HTTP_200_OK
        vendor_names = [b["vendor_name"] for b in response.data]
        assert "Expiring Vendor" in vendor_names
        assert "Safe Vendor" not in vendor_names
