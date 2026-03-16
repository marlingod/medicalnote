import uuid

from django.db import IntegrityError
from django.test import TestCase

from apps.accounts.models import Practice, User
from apps.audit.models import AuditLog


class AuditLogModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.user = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )

    def test_create_audit_log(self):
        log = AuditLog.objects.create(
            user=self.user,
            action="view",
            resource_type="patient",
            resource_id=uuid.uuid4(),
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            phi_accessed=True,
            details={"field": "first_name"},
        )
        assert log.id is not None
        assert log.phi_accessed is True

    def test_audit_log_is_append_only_no_update(self):
        log = AuditLog.objects.create(
            user=self.user,
            action="create",
            resource_type="encounter",
            resource_id=uuid.uuid4(),
            ip_address="10.0.0.1",
            phi_accessed=False,
        )
        # The model should exist but we enforce append-only via save override
        log.action = "delete"
        # save should raise if the object already has a pk and was previously saved
        # We implement this by overriding save to block updates
        from django.core.exceptions import PermissionDenied

        with self.assertRaises(PermissionDenied):
            log.save()

    def test_audit_log_no_delete(self):
        log = AuditLog.objects.create(
            user=self.user,
            action="view",
            resource_type="patient",
            resource_id=uuid.uuid4(),
            ip_address="10.0.0.1",
            phi_accessed=True,
        )
        from django.core.exceptions import PermissionDenied

        with self.assertRaises(PermissionDenied):
            log.delete()

    def test_audit_log_action_choices(self):
        for action in ["view", "create", "update", "delete", "export", "share"]:
            log = AuditLog(
                user=self.user,
                action=action,
                resource_type="patient",
                resource_id=uuid.uuid4(),
                ip_address="10.0.0.1",
                phi_accessed=False,
            )
            log.full_clean()  # Should not raise

    def test_audit_log_str(self):
        log = AuditLog.objects.create(
            user=self.user,
            action="view",
            resource_type="patient",
            resource_id=uuid.uuid4(),
            ip_address="10.0.0.1",
            phi_accessed=True,
        )
        assert "view" in str(log)
        assert "patient" in str(log)
