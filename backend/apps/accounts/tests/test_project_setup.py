from django.test import TestCase


class ProjectSetupTest(TestCase):
    def test_django_boots(self):
        """Verify Django project is configured correctly and boots."""
        from django.conf import settings

        assert settings.AUTH_USER_MODEL == "accounts.User"
        assert "apps.accounts" in settings.INSTALLED_APPS
        assert "rest_framework" in settings.INSTALLED_APPS

    def test_password_hasher_argon2_is_primary(self):
        """Verify Argon2id is the primary password hasher in base settings."""
        from config.settings.base import PASSWORD_HASHERS

        assert "Argon2" in PASSWORD_HASHERS[0]
