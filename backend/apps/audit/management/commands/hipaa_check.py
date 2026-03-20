import sys
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "HIPAA compliance health check — run before deployment"

    def handle(self, *args, **options):
        checks = []

        # 1. Secret key
        secret = settings.SECRET_KEY
        if secret and "insecure" not in secret and "change" not in secret.lower():
            checks.append(("PASS", "SECRET_KEY is set and not a default value"))
        else:
            checks.append(("FAIL", "SECRET_KEY appears to be a default/insecure value"))

        # 2. Encryption key
        enc_key = settings.FIELD_ENCRYPTION_KEY
        default_key = "bTzU1e8gzOEaqJsig_fvQSOuBPAdQL4bzJiFsA00DkY="
        if enc_key and enc_key != default_key:
            checks.append(("PASS", "FIELD_ENCRYPTION_KEY is set and not the default"))
        else:
            checks.append(("FAIL", "FIELD_ENCRYPTION_KEY is the default dev key — rotate immediately"))

        # 3. DEBUG mode
        if not settings.DEBUG:
            checks.append(("PASS", "DEBUG is False"))
        else:
            checks.append(("FAIL", "DEBUG is True — must be False in production"))

        # 4. Redis TLS
        import os
        redis_url = os.environ.get("REDIS_TLS_URL", "")
        celery_url = getattr(settings, "CELERY_BROKER_URL", "")
        if redis_url and celery_url.startswith("rediss://"):
            checks.append(("PASS", "Redis connections use TLS"))
        elif not redis_url:
            checks.append(("WARN", "REDIS_TLS_URL not set — ensure Redis uses TLS in production"))
        else:
            checks.append(("FAIL", "Redis connections do not use TLS"))

        # 5. BAA records
        try:
            from apps.compliance.models import BusinessAssociateAgreement
            active_baas = BusinessAssociateAgreement.objects.filter(status="active").count()
            if active_baas > 0:
                checks.append(("PASS", f"{active_baas} active BAA(s) on file"))
            else:
                checks.append(("WARN", "No active BAAs found — ensure all vendors have signed BAAs"))
        except Exception:
            checks.append(("WARN", "Compliance app not available — cannot check BAAs"))

        # 6. MFA enrollment
        try:
            from apps.accounts.models import User
            from allauth.mfa.models import Authenticator
            privileged = User.objects.filter(role__in=["doctor", "admin"], is_active=True)
            total = privileged.count()
            if total > 0:
                with_mfa = privileged.filter(
                    id__in=Authenticator.objects.values_list("user_id", flat=True)
                ).count()
                rate = (with_mfa / total) * 100
                if rate >= 90:
                    checks.append(("PASS", f"MFA enrollment: {with_mfa}/{total} ({rate:.0f}%)"))
                elif rate >= 50:
                    checks.append(("WARN", f"MFA enrollment: {with_mfa}/{total} ({rate:.0f}%) — target 100%"))
                else:
                    checks.append(("FAIL", f"MFA enrollment: {with_mfa}/{total} ({rate:.0f}%) — critically low"))
            else:
                checks.append(("WARN", "No privileged users found"))
        except Exception as e:
            checks.append(("WARN", f"Cannot check MFA enrollment: {e}"))

        # 7. Audit log volume
        try:
            from apps.audit.models import AuditLog
            recent = AuditLog.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).count()
            if recent > 0:
                checks.append(("PASS", f"{recent} audit log entries in the last 24h"))
            else:
                checks.append(("WARN", "No audit logs in the last 24h — is the system active?"))
        except Exception:
            checks.append(("WARN", "Cannot check audit log volume"))

        # 8. Anthropic BAA
        llm_provider = getattr(settings, "LLM_PROVIDER", "claude")
        if "claude" in llm_provider:
            if getattr(settings, "ANTHROPIC_BAA_CONFIRMED", False):
                checks.append(("PASS", "Anthropic BAA confirmed"))
            else:
                checks.append(("FAIL", "ANTHROPIC_BAA_CONFIRMED is not set — BAA required before sending PHI"))

        # 9. GCP Project ID for Vertex AI
        if "gemini" in llm_provider:
            if getattr(settings, "GCP_PROJECT_ID", ""):
                checks.append(("PASS", "GCP_PROJECT_ID is set for Vertex AI"))
            else:
                checks.append(("FAIL", "GCP_PROJECT_ID not set — Vertex AI requires a GCP project"))

        # Print results
        has_failures = False
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("  HIPAA COMPLIANCE HEALTH CHECK")
        self.stdout.write("=" * 60 + "\n")

        for status_code, message in checks:
            if status_code == "PASS":
                self.stdout.write(self.style.SUCCESS(f"  [PASS] {message}"))
            elif status_code == "WARN":
                self.stdout.write(self.style.WARNING(f"  [WARN] {message}"))
            else:
                self.stdout.write(self.style.ERROR(f"  [FAIL] {message}"))
                has_failures = True

        self.stdout.write("\n" + "=" * 60)
        if has_failures:
            self.stdout.write(self.style.ERROR("  RESULT: FAILED — address all FAIL items before deployment"))
            sys.exit(1)
        else:
            self.stdout.write(self.style.SUCCESS("  RESULT: PASSED"))
        self.stdout.write("=" * 60 + "\n")
