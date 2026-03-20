import logging
from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

# Paths that should be exempt from MFA enforcement
MFA_EXEMPT_PATHS = [
    "/api/v1/auth/",
    "/admin/",
    "/api/v1/widget/",  # Patient-facing widget
]


class MFAEnforcementMiddleware(MiddlewareMixin):
    """Enforce MFA for doctors and admins accessing PHI (HIPAA §164.312(d))."""

    def process_request(self, request):
        if not getattr(settings, "MFA_ENFORCEMENT_ENABLED", True):
            return None

        if not hasattr(request, "user") or not request.user.is_authenticated:
            return None

        # Exempt paths
        path = request.path
        for exempt in MFA_EXEMPT_PATHS:
            if path.startswith(exempt):
                return None

        # Only enforce for doctors and admins
        user_role = getattr(request.user, "role", "")
        if user_role not in ("doctor", "admin"):
            return None

        # Check if user has MFA configured
        try:
            from allauth.mfa.models import Authenticator
            has_mfa = Authenticator.objects.filter(user=request.user).exists()
        except Exception:
            has_mfa = False

        if not has_mfa:
            return JsonResponse(
                {
                    "error": "MFA required",
                    "detail": "Multi-factor authentication must be configured before accessing clinical data.",
                    "mfa_setup_url": "/api/v1/auth/mfa/totp/",
                },
                status=403,
            )

        return None
