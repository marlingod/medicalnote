import os

# Set test-only defaults BEFORE importing base (which calls _require_env)
os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("FIELD_ENCRYPTION_KEY", "bTzU1e8gzOEaqJsig_fvQSOuBPAdQL4bzJiFsA00DkY=")

from .base import *  # noqa: F401,F403

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Faster password hashing in tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable throttling in tests
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {}  # noqa: F405

# In-memory channel layer for tests
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

# Celery runs tasks synchronously in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Skip email verification in tests for auth flows
ACCOUNT_EMAIL_VERIFICATION = "none"

# Disable axes lockout in tests unless explicitly testing it
AXES_ENABLED = False

# Disable MFA enforcement in tests unless explicitly testing it
MFA_ENFORCEMENT_ENABLED = False
