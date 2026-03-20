import os

# Set dev-only defaults BEFORE importing base (which calls _require_env)
os.environ.setdefault("DJANGO_SECRET_KEY", "insecure-dev-key-change-in-production")
os.environ.setdefault("FIELD_ENCRYPTION_KEY", "bTzU1e8gzOEaqJsig_fvQSOuBPAdQL4bzJiFsA00DkY=")

from .base import *  # noqa: F401,F403

DEBUG = True

# Allow all hosts in development
ALLOWED_HOSTS = ["*"]

# Use console email backend
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Add browsable API renderer in development
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"].append(  # noqa: F405
    "rest_framework.renderers.BrowsableAPIRenderer"
)

# Less strict security in development
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

# CORS: allow all in development
CORS_ALLOW_ALL_ORIGINS = True

# Skip email verification in development
ACCOUNT_EMAIL_VERIFICATION = "none"
