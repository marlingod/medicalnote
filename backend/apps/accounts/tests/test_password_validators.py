from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import Practice, User, PasswordHistory
from apps.accounts.validators import (
    UppercaseValidator,
    LowercaseValidator,
    SpecialCharacterValidator,
    PasswordHistoryValidator,
)


class UppercaseValidatorTest(TestCase):
    def setUp(self):
        self.validator = UppercaseValidator()

    def test_rejects_no_uppercase(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("alllowercase123!")
        assert ctx.exception.code == "password_no_upper"

    def test_accepts_with_uppercase(self):
        # Should not raise
        self.validator.validate("hasUppercase123!")

    def test_get_help_text(self):
        text = self.validator.get_help_text()
        assert "uppercase" in text.lower()


class LowercaseValidatorTest(TestCase):
    def setUp(self):
        self.validator = LowercaseValidator()

    def test_rejects_no_lowercase(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("ALLUPPERCASE123!")
        assert ctx.exception.code == "password_no_lower"

    def test_accepts_with_lowercase(self):
        # Should not raise
        self.validator.validate("HASLOWERcase123!")

    def test_get_help_text(self):
        text = self.validator.get_help_text()
        assert "lowercase" in text.lower()


class SpecialCharacterValidatorTest(TestCase):
    def setUp(self):
        self.validator = SpecialCharacterValidator()

    def test_rejects_no_special(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("NoSpecialChars123")
        assert ctx.exception.code == "password_no_special"

    def test_accepts_with_special(self):
        # Should not raise
        self.validator.validate("HasSpecial!123")

    def test_accepts_various_special_chars(self):
        for char in ["!", "@", "#", "$", "%", "^", "&", "*"]:
            self.validator.validate(f"Password{char}123")

    def test_get_help_text(self):
        text = self.validator.get_help_text()
        assert "special" in text.lower()


class PasswordHistoryValidatorTest(TestCase):
    def setUp(self):
        self.validator = PasswordHistoryValidator()
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.user = User.objects.create_user(
            email="testuser@test.com",
            password="CurrentPass123!",
            role="doctor",
            practice=self.practice,
        )

    def test_allows_new_password_no_history(self):
        # No history entries, should pass
        self.validator.validate("BrandNewPass123!", user=self.user)

    def test_blocks_reused_password(self):
        from django.contrib.auth.hashers import make_password

        PasswordHistory.objects.create(
            user=self.user,
            password_hash=make_password("OldPassword123!"),
        )
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("OldPassword123!", user=self.user)
        assert ctx.exception.code == "password_reused"

    def test_allows_different_password(self):
        from django.contrib.auth.hashers import make_password

        PasswordHistory.objects.create(
            user=self.user,
            password_hash=make_password("OldPassword123!"),
        )
        # Different password should pass
        self.validator.validate("CompletelyDifferent456@", user=self.user)

    def test_skips_validation_when_no_user(self):
        # Should not raise when user is None
        self.validator.validate("AnyPassword123!", user=None)

    def test_get_help_text(self):
        text = self.validator.get_help_text()
        assert "12" in text
