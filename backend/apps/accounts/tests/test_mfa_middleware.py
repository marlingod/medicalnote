from unittest.mock import patch, MagicMock

from django.test import TestCase, RequestFactory, override_settings

from apps.accounts.middleware import MFAEnforcementMiddleware
from apps.accounts.models import Practice, User


@override_settings(MFA_ENFORCEMENT_ENABLED=True)
class MFAEnforcementMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = MFAEnforcementMiddleware(get_response=lambda r: None)
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="SecurePass123!@#", role="doctor", practice=self.practice
        )
        self.patient_user = User.objects.create_user(
            email="patient@test.com", password="SecurePass123!@#", role="patient"
        )

    @patch("apps.accounts.middleware.MFAEnforcementMiddleware.process_request")
    def _make_request(self, user, path, mock_process):
        """Helper: restore original process_request for actual testing."""
        mock_process.side_effect = MFAEnforcementMiddleware.process_request.__wrapped__ if hasattr(MFAEnforcementMiddleware.process_request, '__wrapped__') else None
        request = self.factory.get(path)
        request.user = user
        return self.middleware.process_request(request)

    def test_doctor_without_mfa_gets_403_on_patient_endpoint(self):
        request = self.factory.get("/api/v1/patients/")
        request.user = self.doctor

        with patch("apps.accounts.middleware.Authenticator", create=True) as mock_module:
            # Simulate import working but no authenticators found
            with patch("allauth.mfa.models.Authenticator") as MockAuth:
                MockAuth.objects.filter.return_value.exists.return_value = False
                response = self.middleware.process_request(request)

        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 403)

    def test_patient_role_is_allowed_through_without_mfa(self):
        request = self.factory.get("/api/v1/patients/")
        request.user = self.patient_user

        response = self.middleware.process_request(request)
        self.assertIsNone(response)

    def test_auth_paths_are_exempt_from_mfa_check(self):
        request = self.factory.get("/api/v1/auth/login/")
        request.user = self.doctor

        response = self.middleware.process_request(request)
        self.assertIsNone(response)

    def test_admin_path_is_exempt_from_mfa_check(self):
        request = self.factory.get("/admin/dashboard/")
        request.user = self.doctor

        response = self.middleware.process_request(request)
        self.assertIsNone(response)

    def test_widget_path_is_exempt_from_mfa_check(self):
        request = self.factory.get("/api/v1/widget/summary/")
        request.user = self.doctor

        response = self.middleware.process_request(request)
        self.assertIsNone(response)

    def test_doctor_with_mfa_authenticator_passes_through(self):
        request = self.factory.get("/api/v1/patients/")
        request.user = self.doctor

        with patch("allauth.mfa.models.Authenticator") as MockAuth:
            MockAuth.objects.filter.return_value.exists.return_value = True
            response = self.middleware.process_request(request)

        self.assertIsNone(response)

    @override_settings(MFA_ENFORCEMENT_ENABLED=False)
    def test_mfa_enforcement_disabled_allows_all(self):
        request = self.factory.get("/api/v1/patients/")
        request.user = self.doctor

        response = self.middleware.process_request(request)
        self.assertIsNone(response)

    def test_unauthenticated_user_passes_through(self):
        request = self.factory.get("/api/v1/patients/")
        request.user = MagicMock(is_authenticated=False)

        response = self.middleware.process_request(request)
        self.assertIsNone(response)
