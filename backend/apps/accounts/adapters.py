import hashlib
import hmac
import secrets
import string

from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.core.cache import cache


class MedicalNoteAccountAdapter(DefaultAccountAdapter):
    """Custom allauth adapter for MedicalNote platform."""

    def is_open_for_signup(self, request):
        return True


def normalize_e164(phone_number: str) -> str:
    """Normalize phone number to E.164 format."""
    cleaned = "".join(c for c in phone_number if c.isdigit() or c == "+")
    if not cleaned.startswith("+"):
        cleaned = f"+1{cleaned}"
    return cleaned


def generate_6_digit_otp() -> str:
    """Generate a 6-digit OTP using CSPRNG."""
    return "".join(secrets.choice(string.digits) for _ in range(6))


class PatientOTPAdapter:
    MAX_SEND_ATTEMPTS = 3
    MAX_VERIFY_ATTEMPTS = 5
    OTP_TIMEOUT = 300  # 5 minutes

    def send_otp(self, phone_number: str) -> None:
        phone_number = normalize_e164(phone_number)
        send_key = f"otp_send_count:{phone_number}"
        send_count = cache.get(send_key, 0)
        if send_count >= self.MAX_SEND_ATTEMPTS:
            raise RateLimitExceeded("Too many OTP requests. Try again later.")

        code = generate_6_digit_otp()
        cache.set(f"otp:{phone_number}", code, timeout=self.OTP_TIMEOUT)
        cache.set(f"otp_attempts:{phone_number}", 0, timeout=self.OTP_TIMEOUT)
        cache.set(send_key, send_count + 1, timeout=3600)

        from services.notification_service import NotificationService

        NotificationService().send_sms(
            to=phone_number,
            body=f"Your MedicalNote code: {code}",
        )

    def verify_otp(self, phone_number: str, code: str):
        from apps.accounts.models import User

        phone_number = normalize_e164(phone_number)
        attempts_key = f"otp_attempts:{phone_number}"
        attempts = cache.get(attempts_key, 0)
        if attempts >= self.MAX_VERIFY_ATTEMPTS:
            cache.delete(f"otp:{phone_number}")
            raise RateLimitExceeded("Too many attempts. Request a new code.")

        cache.set(attempts_key, attempts + 1, timeout=self.OTP_TIMEOUT)

        stored = cache.get(f"otp:{phone_number}")
        if stored and hmac.compare_digest(str(stored), str(code)):
            cache.delete(f"otp:{phone_number}")
            cache.delete(attempts_key)
            user, created = User.objects.get_or_create(
                phone=phone_number,
                defaults={"role": "patient", "email": f"{phone_number}@patient.medicalnote.local"},
            )
            return user
        return None


class RateLimitExceeded(Exception):
    pass


class OTPDeliveryFailed(Exception):
    pass
