import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class UppercaseValidator:
    def validate(self, password, user=None):
        if not re.search(r"[A-Z]", password):
            raise ValidationError(
                _("Password must contain at least one uppercase letter."),
                code="password_no_upper",
            )

    def get_help_text(self):
        return _("Your password must contain at least one uppercase letter.")


class LowercaseValidator:
    def validate(self, password, user=None):
        if not re.search(r"[a-z]", password):
            raise ValidationError(
                _("Password must contain at least one lowercase letter."),
                code="password_no_lower",
            )

    def get_help_text(self):
        return _("Your password must contain at least one lowercase letter.")


class SpecialCharacterValidator:
    def validate(self, password, user=None):
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            raise ValidationError(
                _("Password must contain at least one special character."),
                code="password_no_special",
            )

    def get_help_text(self):
        return _("Your password must contain at least one special character (!@#$%^&* etc).")


class PasswordHistoryValidator:
    """Prevent reuse of the last 12 passwords (HIPAA 164.312(a)(2)(i))."""

    HISTORY_COUNT = 12

    def validate(self, password, user=None):
        if user is None:
            return
        from apps.accounts.models import PasswordHistory
        from django.contrib.auth.hashers import check_password

        recent = PasswordHistory.objects.filter(user=user).order_by("-created_at")[: self.HISTORY_COUNT]
        for entry in recent:
            if check_password(password, entry.password_hash):
                raise ValidationError(
                    _("Cannot reuse any of your last %(count)d passwords."),
                    code="password_reused",
                    params={"count": self.HISTORY_COUNT},
                )

    def get_help_text(self):
        return _("Your password cannot be the same as any of your last 12 passwords.")
