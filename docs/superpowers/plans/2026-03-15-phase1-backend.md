# Phase 1 Backend Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Django backend for MedicalNote Phase 1 — API, auth, models, Celery workers, services, HIPAA middleware, and WebSocket support.

**Architecture:** Modular monolith with async Celery workers. Django 5.x + DRF handles the API layer. Four workers (transcription, SOAP note, summary, OCR) process encounters through a chained pipeline. Django Channels provides real-time status updates via WebSocket.

**Tech Stack:** Django 5.x, DRF, django-allauth, dj-rest-auth, simplejwt, Celery, Redis, PostgreSQL, Django Channels, AWS (HealthScribe, Textract, S3, KMS), Claude API (Anthropic)

---

## Chunk 1: Project Scaffolding and Configuration

### Task 1.1: Initialize Django project with split settings

- [ ] **Step 1 (2 min):** Create the backend directory structure and initialize Django project.

```bash
mkdir -p backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install django==5.1.* djangorestframework django-allauth[mfa] dj-rest-auth djangorestframework-simplejwt celery[redis] django-channels channels-redis django-encrypted-model-fields django-filter django-cors-headers argon2-cffi pytest-django factory-boy
django-admin startproject config .
```

- [ ] **Step 2 (3 min):** Create split settings directory. Remove `config/settings.py` and create `config/settings/__init__.py`, `config/settings/base.py`, `config/settings/development.py`, `config/settings/production.py`, `config/settings/test.py`.

File: `backend/config/settings/__init__.py`
```python
```

File: `backend/config/settings/base.py`
```python
import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-dev-key-change-in-production")

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Third-party
    "rest_framework",
    "rest_framework.authtoken",
    "allauth",
    "allauth.account",
    "allauth.mfa",
    "dj_rest_auth",
    "dj_rest_auth.registration",
    "django_filters",
    "corsheaders",
    "channels",
    # Local apps
    "apps.accounts",
    "apps.patients",
    "apps.encounters",
    "apps.notes",
    "apps.summaries",
    "apps.widget",
    "apps.audit",
    "apps.realtime",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.audit.middleware.HIPAAAuditMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "medicalnote"),
        "USER": os.environ.get("DB_USER", "medicalnote"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "medicalnote"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SITE_ID = 1

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/min",
        "user": "100/min",
    },
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
}

# SimpleJWT
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# django-allauth
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_ADAPTER = "apps.accounts.adapters.MedicalNoteAccountAdapter"

# dj-rest-auth
REST_AUTH = {
    "USE_JWT": True,
    "JWT_AUTH_HTTPONLY": True,
    "JWT_AUTH_COOKIE": "medicalnote-auth",
    "JWT_AUTH_REFRESH_COOKIE": "medicalnote-refresh",
    "USER_DETAILS_SERIALIZER": "apps.accounts.serializers.UserDetailSerializer",
    "REGISTER_SERIALIZER": "apps.accounts.serializers.DoctorRegistrationSerializer",
}

# Celery
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 600  # 10 min hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 300  # 5 min soft limit
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# Django Channels
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.environ.get("REDIS_URL", "redis://localhost:6379/2")],
        },
    },
}

# CORS
CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8000"
).split(",")
CORS_ALLOW_CREDENTIALS = True

# Encryption key for django-encrypted-model-fields
FIELD_ENCRYPTION_KEY = os.environ.get(
    "FIELD_ENCRYPTION_KEY",
    "dev-encryption-key-must-be-replaced-in-production-32b=",
)

# AWS Settings
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_S3_BUCKET = os.environ.get("AWS_S3_BUCKET", "medicalnote-hipaa-dev")
AWS_KMS_KEY_ID = os.environ.get("AWS_KMS_KEY_ID", "")

# Claude API
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Twilio (OTP)
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "")

# Security
SESSION_COOKIE_AGE = 900  # 15-minute session timeout (HIPAA)
SESSION_SAVE_EVERY_REQUEST = True
SECURE_BROWSER_XSS_FILTER = False  # Rely on CSP instead
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "apps": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
        "workers": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    },
}
```

File: `backend/config/settings/development.py`
```python
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
```

File: `backend/config/settings/production.py`
```python
from .base import *  # noqa: F401,F403

DEBUG = False

# Security settings
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

File: `backend/config/settings/test.py`
```python
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

FIELD_ENCRYPTION_KEY = "test-encryption-key-32-bytes-long-pad="
```

- [ ] **Step 3 (2 min):** Create `pyproject.toml` with pytest configuration.

File: `backend/pyproject.toml`
```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.test"
python_files = ["tests.py", "test_*.py", "*_tests.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short --strict-markers"
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks integration tests",
]

[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
```

- [ ] **Step 4 (2 min):** Create `requirements.txt`.

File: `backend/requirements.txt`
```
Django>=5.1,<5.2
djangorestframework>=3.15,<4.0
django-allauth[mfa]>=65.0,<66.0
dj-rest-auth>=7.0,<8.0
djangorestframework-simplejwt>=5.3,<6.0
celery[redis]>=5.4,<6.0
django-celery-beat>=2.7,<3.0
channels>=4.1,<5.0
channels-redis>=4.2,<5.0
daphne>=4.1,<5.0
django-encrypted-model-fields>=0.6,<1.0
django-filter>=24.0,<25.0
django-cors-headers>=4.4,<5.0
argon2-cffi>=23.1,<24.0
psycopg2-binary>=2.9,<3.0
boto3>=1.35,<2.0
anthropic>=0.40,<1.0
twilio>=9.0,<10.0
gunicorn>=22.0,<23.0
whitenoise>=6.7,<7.0
redis>=5.0,<6.0
# Testing
pytest>=8.0,<9.0
pytest-django>=4.9,<5.0
pytest-asyncio>=0.24,<1.0
factory-boy>=3.3,<4.0
pytest-cov>=5.0,<6.0
freezegun>=1.4,<2.0
```

- [ ] **Step 5 (2 min):** Create Celery app configuration.

File: `backend/config/celery.py`
```python
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("medicalnote")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(["workers"])

app.conf.task_routes = {
    "workers.transcription.*": {"queue": "transcription"},
    "workers.soap_note.*": {"queue": "soap_note"},
    "workers.summary.*": {"queue": "summary"},
    "workers.ocr.*": {"queue": "ocr"},
}

app.conf.task_default_queue = "default"
```

File: `backend/config/__init__.py`
```python
from .celery import app as celery_app

__all__ = ("celery_app",)
```

- [ ] **Step 6 (2 min):** Create ASGI configuration for Django Channels.

File: `backend/config/asgi.py`
```python
import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django_asgi_app = get_asgi_application()

from apps.realtime.middleware import JWTAuthMiddleware  # noqa: E402
from apps.realtime.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            JWTAuthMiddleware(URLRouter(websocket_urlpatterns))
        ),
    }
)
```

File: `backend/config/wsgi.py`
```python
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
application = get_wsgi_application()
```

- [ ] **Step 7 (2 min):** Create root URL configuration.

File: `backend/config/urls.py`
```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/patients/", include("apps.patients.urls")),
    path("api/v1/encounters/", include("apps.encounters.urls")),
    path("api/v1/notes/", include("apps.notes.urls")),
    path("api/v1/summaries/", include("apps.summaries.urls")),
    path("api/v1/widget/", include("apps.widget.urls")),
    path("api/v1/practice/", include("apps.accounts.practice_urls")),
    path("api/v1/patient/", include("apps.summaries.patient_urls")),
]
```

- [ ] **Step 8 (2 min):** Create app directory scaffolding with `__init__.py` files.

```bash
cd backend
mkdir -p apps/accounts/tests
mkdir -p apps/patients/tests
mkdir -p apps/encounters/tests
mkdir -p apps/notes/tests
mkdir -p apps/summaries/tests
mkdir -p apps/widget/tests
mkdir -p apps/audit/tests
mkdir -p apps/realtime/tests
mkdir -p workers
mkdir -p services
mkdir -p prompts
```

Create `apps/__init__.py` and each app's `__init__.py`, `apps.py` files. Each `apps.py` follows this pattern (example for accounts):

File: `backend/apps/accounts/apps.py`
```python
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Accounts"
```

Repeat for all apps: `patients` (name `apps.patients`), `encounters` (name `apps.encounters`), `notes` (name `apps.notes`), `summaries` (name `apps.summaries`), `widget` (name `apps.widget`), `audit` (name `apps.audit`), `realtime` (name `apps.realtime`).

- [ ] **Step 9 (2 min):** Write and run first test to verify project boots.

File: `backend/apps/accounts/tests/__init__.py`
```python
```

File: `backend/apps/accounts/tests/test_project_setup.py`
```python
from django.test import TestCase


class ProjectSetupTest(TestCase):
    def test_django_boots(self):
        """Verify Django project is configured correctly and boots."""
        from django.conf import settings

        assert settings.AUTH_USER_MODEL == "accounts.User"
        assert "apps.accounts" in settings.INSTALLED_APPS
        assert "rest_framework" in settings.INSTALLED_APPS

    def test_password_hasher_argon2_is_primary(self):
        """Verify Argon2id is the primary password hasher."""
        from django.conf import settings

        assert "Argon2" in settings.PASSWORD_HASHERS[0]
```

Run: `cd backend && python -m pytest apps/accounts/tests/test_project_setup.py -v`
Verify: Tests fail because `User` model does not exist yet. This is expected -- we build models next.

---

## Chunk 2: Core Models and Migrations

### Task 2.1: Accounts models (User, Practice)

- [ ] **Step 1 (3 min):** Write failing tests for User and Practice models.

File: `backend/apps/accounts/tests/test_models.py`
```python
import uuid

import pytest
from django.test import TestCase

from apps.accounts.models import Practice, User


class UserModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(
            name="Test Clinic",
            subscription_tier="solo",
        )

    def test_create_doctor_user(self):
        user = User.objects.create_user(
            email="doctor@example.com",
            password="securepassword123!",
            first_name="Jane",
            last_name="Smith",
            role="doctor",
            practice=self.practice,
        )
        assert user.id is not None
        assert isinstance(user.id, uuid.UUID)
        assert user.email == "doctor@example.com"
        assert user.role == "doctor"
        assert user.practice == self.practice
        assert user.check_password("securepassword123!")

    def test_create_patient_user(self):
        user = User.objects.create_user(
            email="patient@example.com",
            password=None,
            first_name="John",
            last_name="Doe",
            role="patient",
            phone="+15551234567",
        )
        assert user.role == "patient"
        assert not user.has_usable_password()

    def test_create_admin_user(self):
        user = User.objects.create_user(
            email="admin@example.com",
            password="securepassword123!",
            first_name="Admin",
            last_name="User",
            role="admin",
            practice=self.practice,
        )
        assert user.role == "admin"

    def test_user_str(self):
        user = User.objects.create_user(
            email="doctor@example.com",
            password="securepassword123!",
            first_name="Jane",
            last_name="Smith",
            role="doctor",
            practice=self.practice,
        )
        assert str(user) == "doctor@example.com"

    def test_user_has_uuid_pk(self):
        user = User.objects.create_user(
            email="doctor@example.com",
            password="test",
            role="doctor",
            practice=self.practice,
        )
        assert isinstance(user.pk, uuid.UUID)

    def test_email_is_unique(self):
        User.objects.create_user(
            email="unique@example.com", password="test", role="doctor", practice=self.practice
        )
        with pytest.raises(Exception):
            User.objects.create_user(
                email="unique@example.com", password="test2", role="doctor", practice=self.practice
            )

    def test_role_choices_enforced(self):
        user = User(email="bad@example.com", role="hacker")
        with pytest.raises(Exception):
            user.full_clean()


class PracticeModelTest(TestCase):
    def test_create_practice(self):
        practice = Practice.objects.create(
            name="Downtown Clinic",
            subscription_tier="group",
        )
        assert practice.id is not None
        assert isinstance(practice.id, uuid.UUID)
        assert practice.name == "Downtown Clinic"
        assert practice.subscription_tier == "group"

    def test_practice_str(self):
        practice = Practice.objects.create(name="My Clinic", subscription_tier="solo")
        assert str(practice) == "My Clinic"

    def test_practice_white_label_config_nullable(self):
        practice = Practice.objects.create(
            name="Test",
            subscription_tier="solo",
            white_label_config=None,
        )
        assert practice.white_label_config is None

    def test_practice_with_white_label_config(self):
        config = {
            "logo_url": "https://cdn.example.com/logo.png",
            "brand_color": "#FF5733",
            "custom_domain": "portal.clinic.com",
            "widget_key": "wk_abc123",
        }
        practice = Practice.objects.create(
            name="Branded Clinic",
            subscription_tier="enterprise",
            white_label_config=config,
        )
        assert practice.white_label_config["brand_color"] == "#FF5733"
```

Run: `cd backend && python -m pytest apps/accounts/tests/test_models.py -v`
Verify: Tests fail with `ImportError` because models do not exist yet.

- [ ] **Step 2 (4 min):** Implement User and Practice models.

File: `backend/apps/accounts/models.py`
```python
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class Practice(models.Model):
    class SubscriptionTier(models.TextChoices):
        SOLO = "solo", "Solo"
        GROUP = "group", "Group"
        ENTERPRISE = "enterprise", "Enterprise"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    address = EncryptedCharField(max_length=500, blank=True, default="")
    phone = EncryptedCharField(max_length=20, blank=True, default="")
    subscription_tier = models.CharField(
        max_length=20,
        choices=SubscriptionTier.choices,
        default=SubscriptionTier.SOLO,
    )
    white_label_config = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "practices"
        ordering = ["name"]

    def __str__(self):
        return self.name


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        DOCTOR = "doctor", "Doctor"
        ADMIN = "admin", "Admin"
        PATIENT = "patient", "Patient"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = EncryptedCharField(max_length=150, blank=True, default="")
    last_name = EncryptedCharField(max_length=150, blank=True, default="")
    phone = EncryptedCharField(max_length=20, blank=True, default="")
    role = models.CharField(max_length=10, choices=Role.choices)
    specialty = models.CharField(max_length=100, blank=True, default="")
    license_number = models.CharField(max_length=50, blank=True, default="")
    practice = models.ForeignKey(
        Practice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
    )
    language_preference = models.CharField(max_length=5, default="en")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
```

Run: `cd backend && python manage.py makemigrations accounts && python -m pytest apps/accounts/tests/test_models.py -v`
Verify: All tests pass.

### Task 2.2: Patient model

- [ ] **Step 1 (3 min):** Write failing tests for Patient model.

File: `backend/apps/patients/tests/__init__.py`
```python
```

File: `backend/apps/patients/tests/test_models.py`
```python
import hashlib
import hmac
import uuid

from django.conf import settings
from django.test import TestCase

from apps.accounts.models import Practice
from apps.patients.models import Patient


class PatientModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(
            name="Test Clinic",
            subscription_tier="solo",
        )

    def test_create_patient(self):
        patient = Patient.objects.create(
            practice=self.practice,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="+15551234567",
            date_of_birth="1990-01-15",
            language_preference="en",
        )
        assert patient.id is not None
        assert isinstance(patient.id, uuid.UUID)
        assert patient.practice == self.practice

    def test_patient_str(self):
        patient = Patient.objects.create(
            practice=self.practice,
            first_name="Jane",
            last_name="Smith",
            date_of_birth="1985-06-20",
        )
        assert "Jane" in str(patient) or "Patient" in str(patient)

    def test_patient_belongs_to_practice(self):
        patient = Patient.objects.create(
            practice=self.practice,
            first_name="Test",
            last_name="Patient",
            date_of_birth="2000-01-01",
        )
        assert patient.practice_id == self.practice.id

    def test_name_search_hash_generated(self):
        patient = Patient.objects.create(
            practice=self.practice,
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-15",
        )
        assert patient.name_search_hash is not None
        assert len(patient.name_search_hash) > 0

    def test_name_search_hash_deterministic(self):
        patient1 = Patient.objects.create(
            practice=self.practice,
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-15",
        )
        patient1_hash = patient1.name_search_hash
        # Same name should produce same hash
        normalized = "john doe"
        expected = hmac.new(
            settings.FIELD_ENCRYPTION_KEY.encode(),
            normalized.encode(),
            hashlib.sha256,
        ).hexdigest()
        assert patient1_hash == expected

    def test_email_nullable(self):
        patient = Patient.objects.create(
            practice=self.practice,
            first_name="No",
            last_name="Email",
            date_of_birth="1990-01-01",
        )
        assert patient.email in (None, "")

    def test_phone_nullable(self):
        patient = Patient.objects.create(
            practice=self.practice,
            first_name="No",
            last_name="Phone",
            date_of_birth="1990-01-01",
        )
        assert patient.phone in (None, "")
```

Run: Verify tests fail.

- [ ] **Step 2 (3 min):** Implement Patient model.

File: `backend/apps/patients/models.py`
```python
import hashlib
import hmac
import uuid

from django.conf import settings
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField, EncryptedDateField


class Patient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    practice = models.ForeignKey(
        "accounts.Practice",
        on_delete=models.CASCADE,
        related_name="patients",
    )
    first_name = EncryptedCharField(max_length=150)
    last_name = EncryptedCharField(max_length=150)
    name_search_hash = models.CharField(max_length=64, db_index=True, blank=True, default="")
    email = EncryptedCharField(max_length=254, blank=True, default="")
    phone = EncryptedCharField(max_length=20, blank=True, default="")
    date_of_birth = EncryptedDateField()
    language_preference = models.CharField(max_length=5, default="en")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "patients"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Patient {self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        self._generate_name_search_hash()
        super().save(*args, **kwargs)

    def _generate_name_search_hash(self):
        """Generate HMAC-SHA256 blind index from normalized name for searchability."""
        normalized = f"{self.first_name} {self.last_name}".strip().lower()
        self.name_search_hash = hmac.new(
            settings.FIELD_ENCRYPTION_KEY.encode(),
            normalized.encode(),
            hashlib.sha256,
        ).hexdigest()
```

Run: `cd backend && python manage.py makemigrations patients && python -m pytest apps/patients/tests/test_models.py -v`
Verify: All tests pass.

### Task 2.3: Encounter, Recording, Transcript models

- [ ] **Step 1 (4 min):** Write failing tests.

File: `backend/apps/encounters/tests/__init__.py`
```python
```

File: `backend/apps/encounters/tests/test_models.py`
```python
import uuid
from datetime import date

from django.test import TestCase

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter, Recording, Transcript
from apps.patients.models import Patient


class EncounterModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice,
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
        )

    def test_create_encounter(self):
        encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="recording",
            status="uploading",
            consent_recording=True,
            consent_method="verbal",
            consent_jurisdiction_state="CA",
        )
        assert encounter.id is not None
        assert isinstance(encounter.id, uuid.UUID)
        assert encounter.status == "uploading"

    def test_encounter_status_choices(self):
        encounter = Encounter(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="recording",
            status="invalid_status",
        )
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            encounter.full_clean()

    def test_encounter_input_method_choices(self):
        for method in ["recording", "paste", "dictation", "scan"]:
            encounter = Encounter.objects.create(
                doctor=self.doctor,
                patient=self.patient,
                encounter_date=date.today(),
                input_method=method,
                status="uploading",
            )
            assert encounter.input_method == method

    def test_encounter_str(self):
        encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date(2026, 3, 15),
            input_method="recording",
            status="uploading",
        )
        result = str(encounter)
        assert "2026-03-15" in result or str(encounter.id) in result


class RecordingModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D", date_of_birth="1990-01-01"
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="recording",
            status="uploading",
        )

    def test_create_recording(self):
        recording = Recording.objects.create(
            encounter=self.encounter,
            storage_url="s3://bucket/audio/test.wav",
            duration_seconds=1800,
            file_size_bytes=54000000,
            format="wav",
            transcription_status="pending",
        )
        assert recording.id is not None
        assert recording.duration_seconds == 1800

    def test_recording_format_choices(self):
        for fmt in ["wav", "mp3", "webm"]:
            recording = Recording(
                encounter=self.encounter,
                storage_url=f"s3://bucket/{fmt}",
                format=fmt,
                transcription_status="pending",
            )
            recording.full_clean()  # Should not raise


class TranscriptModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D", date_of_birth="1990-01-01"
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="recording",
            status="transcribing",
        )

    def test_create_transcript(self):
        transcript = Transcript.objects.create(
            encounter=self.encounter,
            raw_text="Doctor: How are you? Patient: I have a headache.",
            speaker_segments=[
                {"speaker": "doctor", "start": 0.0, "end": 2.5, "text": "How are you?"},
                {"speaker": "patient", "start": 2.5, "end": 5.0, "text": "I have a headache."},
            ],
            medical_terms_detected=["headache"],
            confidence_score=0.95,
            language_detected="en",
        )
        assert transcript.id is not None
        assert len(transcript.speaker_segments) == 2
        assert transcript.confidence_score == 0.95
```

- [ ] **Step 2 (4 min):** Implement Encounter, Recording, Transcript models.

File: `backend/apps/encounters/models.py`
```python
import uuid

from django.db import models
from encrypted_model_fields.fields import EncryptedCharField, EncryptedTextField


class Encounter(models.Model):
    class InputMethod(models.TextChoices):
        RECORDING = "recording", "Recording"
        PASTE = "paste", "Paste"
        DICTATION = "dictation", "Dictation"
        SCAN = "scan", "Scan"

    class Status(models.TextChoices):
        UPLOADING = "uploading", "Uploading"
        TRANSCRIBING = "transcribing", "Transcribing"
        GENERATING_NOTE = "generating_note", "Generating Note"
        GENERATING_SUMMARY = "generating_summary", "Generating Summary"
        READY_FOR_REVIEW = "ready_for_review", "Ready for Review"
        APPROVED = "approved", "Approved"
        DELIVERED = "delivered", "Delivered"
        TRANSCRIPTION_FAILED = "transcription_failed", "Transcription Failed"
        NOTE_GENERATION_FAILED = "note_generation_failed", "Note Generation Failed"
        SUMMARY_GENERATION_FAILED = "summary_generation_failed", "Summary Generation Failed"

    class ConsentMethod(models.TextChoices):
        VERBAL = "verbal", "Verbal"
        DIGITAL_CHECKBOX = "digital_checkbox", "Digital Checkbox"
        WRITTEN = "written", "Written"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="encounters",
        limit_choices_to={"role": "doctor"},
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="encounters",
    )
    encounter_date = models.DateField()
    input_method = models.CharField(max_length=20, choices=InputMethod.choices)
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.UPLOADING,
    )
    consent_recording = models.BooleanField(default=False)
    consent_timestamp = models.DateTimeField(null=True, blank=True)
    consent_method = models.CharField(
        max_length=20,
        choices=ConsentMethod.choices,
        blank=True,
        default="",
    )
    consent_jurisdiction_state = models.CharField(max_length=2, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "encounters"
        ordering = ["-encounter_date", "-created_at"]

    def __str__(self):
        return f"Encounter {self.id} - {self.encounter_date}"


class Recording(models.Model):
    class Format(models.TextChoices):
        WAV = "wav", "WAV"
        MP3 = "mp3", "MP3"
        WEBM = "webm", "WebM"

    class TranscriptionStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    encounter = models.OneToOneField(
        Encounter,
        on_delete=models.CASCADE,
        related_name="recording",
    )
    storage_url = EncryptedCharField(max_length=500)
    duration_seconds = models.IntegerField(default=0)
    file_size_bytes = models.BigIntegerField(default=0)
    format = models.CharField(max_length=10, choices=Format.choices)
    transcription_status = models.CharField(
        max_length=20,
        choices=TranscriptionStatus.choices,
        default=TranscriptionStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "recordings"

    def __str__(self):
        return f"Recording for {self.encounter_id}"


class Transcript(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    encounter = models.OneToOneField(
        Encounter,
        on_delete=models.CASCADE,
        related_name="transcript",
    )
    raw_text = EncryptedTextField()
    speaker_segments = models.JSONField(default=list)
    medical_terms_detected = models.JSONField(default=list)
    confidence_score = models.FloatField(default=0.0)
    language_detected = models.CharField(max_length=10, default="en")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "transcripts"

    def __str__(self):
        return f"Transcript for {self.encounter_id}"
```

Run: `cd backend && python manage.py makemigrations encounters && python -m pytest apps/encounters/tests/test_models.py -v`
Verify: All tests pass.

### Task 2.4: ClinicalNote, PromptVersion models

- [ ] **Step 1 (3 min):** Write failing tests.

File: `backend/apps/notes/tests/__init__.py`
```python
```

File: `backend/apps/notes/tests/test_models.py`
```python
import uuid
from datetime import date

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote, PromptVersion
from apps.patients.models import Patient


class PromptVersionModelTest(TestCase):
    def test_create_prompt_version(self):
        pv = PromptVersion.objects.create(
            prompt_name="soap_note",
            version="1.0.0",
            template_text="You are a medical documentation assistant...",
            is_active=True,
        )
        assert pv.id is not None
        assert isinstance(pv.id, uuid.UUID)
        assert pv.is_active is True

    def test_prompt_version_str(self):
        pv = PromptVersion.objects.create(
            prompt_name="patient_summary",
            version="2.1.0",
            template_text="Convert this clinical note...",
            is_active=False,
        )
        assert "patient_summary" in str(pv)
        assert "2.1.0" in str(pv)


class ClinicalNoteModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D", date_of_birth="1990-01-01"
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="paste",
            status="generating_note",
        )
        self.prompt_version = PromptVersion.objects.create(
            prompt_name="soap_note",
            version="1.0.0",
            template_text="You are a medical documentation assistant...",
            is_active=True,
        )

    def test_create_clinical_note(self):
        note = ClinicalNote.objects.create(
            encounter=self.encounter,
            note_type="soap",
            subjective="Patient complains of headache for 3 days.",
            objective="BP 120/80, Temp 98.6F, alert and oriented.",
            assessment="Tension headache, likely stress-related.",
            plan="Ibuprofen 400mg as needed. Follow up in 2 weeks.",
            icd10_codes=["R51.9"],
            cpt_codes=["99214"],
            ai_generated=True,
            doctor_edited=False,
            prompt_version=self.prompt_version,
        )
        assert note.id is not None
        assert note.note_type == "soap"
        assert note.ai_generated is True
        assert note.approved_at is None

    def test_approve_clinical_note(self):
        note = ClinicalNote.objects.create(
            encounter=self.encounter,
            note_type="soap",
            subjective="S",
            objective="O",
            assessment="A",
            plan="P",
            ai_generated=True,
            prompt_version=self.prompt_version,
        )
        now = timezone.now()
        note.approved_at = now
        note.approved_by = self.doctor
        note.save()
        note.refresh_from_db()
        assert note.approved_at is not None
        assert note.approved_by == self.doctor

    def test_note_type_choices(self):
        for note_type in ["soap", "free_text", "h_and_p"]:
            note = ClinicalNote(
                encounter=self.encounter,
                note_type=note_type,
                prompt_version=self.prompt_version,
            )
            note.full_clean()  # Should not raise
```

- [ ] **Step 2 (3 min):** Implement PromptVersion and ClinicalNote models.

File: `backend/apps/notes/models.py`
```python
import uuid

from django.db import models
from encrypted_model_fields.fields import EncryptedTextField


class PromptVersion(models.Model):
    class PromptName(models.TextChoices):
        SOAP_NOTE = "soap_note", "SOAP Note"
        PATIENT_SUMMARY = "patient_summary", "Patient Summary"
        MEDICAL_TERMS = "medical_terms", "Medical Terms"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prompt_name = models.CharField(max_length=50, choices=PromptName.choices)
    version = models.CharField(max_length=20)
    template_text = models.TextField()
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "prompt_versions"
        unique_together = [("prompt_name", "version")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.prompt_name} v{self.version}"


class ClinicalNote(models.Model):
    class NoteType(models.TextChoices):
        SOAP = "soap", "SOAP"
        FREE_TEXT = "free_text", "Free Text"
        H_AND_P = "h_and_p", "History & Physical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    encounter = models.OneToOneField(
        "encounters.Encounter",
        on_delete=models.CASCADE,
        related_name="clinical_note",
    )
    note_type = models.CharField(max_length=20, choices=NoteType.choices, default=NoteType.SOAP)
    subjective = EncryptedTextField(blank=True, default="")
    objective = EncryptedTextField(blank=True, default="")
    assessment = EncryptedTextField(blank=True, default="")
    plan = EncryptedTextField(blank=True, default="")
    raw_content = EncryptedTextField(blank=True, default="")
    icd10_codes = models.JSONField(default=list)
    cpt_codes = models.JSONField(default=list)
    ai_generated = models.BooleanField(default=False)
    doctor_edited = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_notes",
    )
    prompt_version = models.ForeignKey(
        PromptVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clinical_notes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clinical_notes"

    def __str__(self):
        return f"Note for {self.encounter_id}"
```

Run: `cd backend && python manage.py makemigrations notes && python -m pytest apps/notes/tests/test_models.py -v`
Verify: All tests pass.

### Task 2.5: PatientSummary model

- [ ] **Step 1 (3 min):** Write failing tests.

File: `backend/apps/summaries/tests/__init__.py`
```python
```

File: `backend/apps/summaries/tests/test_models.py`
```python
import uuid
from datetime import date

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote, PromptVersion
from apps.patients.models import Patient
from apps.summaries.models import PatientSummary


class PatientSummaryModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D", date_of_birth="1990-01-01"
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="paste",
            status="generating_summary",
        )
        self.prompt_version = PromptVersion.objects.create(
            prompt_name="patient_summary",
            version="1.0.0",
            template_text="Convert...",
            is_active=True,
        )
        self.note = ClinicalNote.objects.create(
            encounter=self.encounter,
            note_type="soap",
            subjective="S",
            objective="O",
            assessment="A",
            plan="P",
            prompt_version=self.prompt_version,
        )

    def test_create_patient_summary(self):
        summary = PatientSummary.objects.create(
            encounter=self.encounter,
            clinical_note=self.note,
            summary_en="You visited the doctor today. Your blood pressure was normal.",
            summary_es="Visitaste al doctor hoy. Tu presion arterial fue normal.",
            reading_level="grade_8",
            medical_terms_explained=[
                {"term": "hypertension", "explanation": "high blood pressure"}
            ],
            disclaimer_text="This summary is for informational purposes only.",
            delivery_status="pending",
            prompt_version=self.prompt_version,
        )
        assert summary.id is not None
        assert isinstance(summary.id, uuid.UUID)
        assert summary.delivery_status == "pending"
        assert len(summary.medical_terms_explained) == 1

    def test_summary_delivery_lifecycle(self):
        summary = PatientSummary.objects.create(
            encounter=self.encounter,
            clinical_note=self.note,
            summary_en="Summary text.",
            reading_level="grade_8",
            disclaimer_text="Disclaimer.",
            delivery_status="pending",
            prompt_version=self.prompt_version,
        )
        # Send
        summary.delivery_status = "sent"
        summary.delivered_at = timezone.now()
        summary.delivery_method = "app"
        summary.save()
        summary.refresh_from_db()
        assert summary.delivery_status == "sent"
        assert summary.delivered_at is not None

        # View
        summary.delivery_status = "viewed"
        summary.viewed_at = timezone.now()
        summary.save()
        summary.refresh_from_db()
        assert summary.delivery_status == "viewed"
        assert summary.viewed_at is not None

    def test_reading_level_choices(self):
        for level in ["grade_5", "grade_8", "grade_12"]:
            summary = PatientSummary(
                encounter=self.encounter,
                clinical_note=self.note,
                summary_en="Test",
                reading_level=level,
                delivery_status="pending",
                prompt_version=self.prompt_version,
            )
            summary.full_clean()  # Should not raise
```

- [ ] **Step 2 (3 min):** Implement PatientSummary model.

File: `backend/apps/summaries/models.py`
```python
import uuid

from django.db import models
from encrypted_model_fields.fields import EncryptedTextField


class PatientSummary(models.Model):
    class ReadingLevel(models.TextChoices):
        GRADE_5 = "grade_5", "Grade 5"
        GRADE_8 = "grade_8", "Grade 8"
        GRADE_12 = "grade_12", "Grade 12"

    class DeliveryStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        VIEWED = "viewed", "Viewed"
        FAILED = "failed", "Failed"

    class DeliveryMethod(models.TextChoices):
        APP = "app", "App"
        WIDGET = "widget", "Widget"
        SMS_LINK = "sms_link", "SMS Link"
        EMAIL_LINK = "email_link", "Email Link"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    encounter = models.OneToOneField(
        "encounters.Encounter",
        on_delete=models.CASCADE,
        related_name="patient_summary",
    )
    clinical_note = models.ForeignKey(
        "notes.ClinicalNote",
        on_delete=models.CASCADE,
        related_name="summaries",
    )
    summary_en = EncryptedTextField()
    summary_es = EncryptedTextField(blank=True, default="")
    reading_level = models.CharField(
        max_length=10,
        choices=ReadingLevel.choices,
        default=ReadingLevel.GRADE_8,
    )
    medical_terms_explained = models.JSONField(default=list)
    disclaimer_text = models.TextField(
        default="This summary is for informational purposes only and does not constitute medical advice."
    )
    delivery_status = models.CharField(
        max_length=10,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
    )
    delivered_at = models.DateTimeField(null=True, blank=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    delivery_method = models.CharField(
        max_length=20,
        choices=DeliveryMethod.choices,
        blank=True,
        default="",
    )
    prompt_version = models.ForeignKey(
        "notes.PromptVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patient_summaries",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "patient_summaries"
        verbose_name_plural = "Patient summaries"

    def __str__(self):
        return f"Summary for {self.encounter_id}"
```

Run: `cd backend && python manage.py makemigrations summaries && python -m pytest apps/summaries/tests/test_models.py -v`
Verify: All tests pass.

### Task 2.6: AuditLog model (append-only)

- [ ] **Step 1 (3 min):** Write failing tests.

File: `backend/apps/audit/tests/__init__.py`
```python
```

File: `backend/apps/audit/tests/test_models.py`
```python
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
```

- [ ] **Step 2 (3 min):** Implement AuditLog model.

File: `backend/apps/audit/models.py`
```python
import uuid

from django.core.exceptions import PermissionDenied
from django.db import models


class AuditLog(models.Model):
    class Action(models.TextChoices):
        VIEW = "view", "View"
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        EXPORT = "export", "Export"
        SHARE = "share", "Share"

    class ResourceType(models.TextChoices):
        PATIENT = "patient", "Patient"
        ENCOUNTER = "encounter", "Encounter"
        NOTE = "note", "Note"
        SUMMARY = "summary", "Summary"
        RECORDING = "recording", "Recording"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=10, choices=Action.choices)
    resource_type = models.CharField(max_length=20, choices=ResourceType.choices)
    resource_id = models.UUIDField()
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, default="")
    phi_accessed = models.BooleanField(default=False)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created_at"]
        # No update or delete permissions
        default_permissions = ("add", "view")

    def __str__(self):
        return f"{self.action} {self.resource_type} by {self.user_id} at {self.created_at}"

    def save(self, *args, **kwargs):
        if self._state.adding:
            super().save(*args, **kwargs)
        else:
            raise PermissionDenied("Audit logs are append-only and cannot be modified.")

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Audit logs cannot be deleted.")
```

Run: `cd backend && python manage.py makemigrations audit && python -m pytest apps/audit/tests/test_models.py -v`
Verify: All tests pass.

- [ ] **Step 3 (2 min):** Run all migrations together and verify full model suite.

```bash
cd backend
python manage.py makemigrations
python manage.py migrate
python -m pytest apps/ -v
```
Verify: All model tests pass, all migrations applied cleanly.

---

## Chunk 3: Authentication (django-allauth + dj-rest-auth + Patient OTP)

### Task 3.1: Account adapters and serializers

- [ ] **Step 1 (3 min):** Write failing tests for authentication flows.

File: `backend/apps/accounts/tests/test_auth.py`
```python
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import Practice, User


class DoctorRegistrationTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_doctor_registration_creates_practice(self):
        response = self.client.post(
            "/api/v1/auth/registration/",
            {
                "email": "newdoc@example.com",
                "password1": "SecurePass123!@#",
                "password2": "SecurePass123!@#",
                "first_name": "Jane",
                "last_name": "Smith",
                "practice_name": "Smith Clinic",
                "specialty": "Internal Medicine",
            },
            format="json",
        )
        assert response.status_code in (status.HTTP_201_CREATED, status.HTTP_204_NO_CONTENT)
        user = User.objects.get(email="newdoc@example.com")
        assert user.role == "doctor"
        assert user.practice is not None
        assert user.practice.name == "Smith Clinic"

    def test_doctor_registration_requires_practice_name(self):
        response = self.client.post(
            "/api/v1/auth/registration/",
            {
                "email": "newdoc@example.com",
                "password1": "SecurePass123!@#",
                "password2": "SecurePass123!@#",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class DoctorLoginTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doctor@example.com",
            password="SecurePass123!@#",
            role="doctor",
            practice=self.practice,
        )

    def test_login_returns_jwt(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "doctor@example.com", "password": "SecurePass123!@#"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data or "access_token" in response.data

    def test_login_wrong_password(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "doctor@example.com", "password": "wrongpassword"},
            format="json",
        )
        assert response.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_get_current_user_authenticated(self):
        self.client.force_authenticate(user=self.doctor)
        response = self.client.get("/api/v1/auth/user/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "doctor@example.com"

    def test_get_current_user_unauthenticated(self):
        response = self.client.get("/api/v1/auth/user/")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )
```

- [ ] **Step 2 (4 min):** Implement serializers.

File: `backend/apps/accounts/serializers.py`
```python
from rest_framework import serializers
from dj_rest_auth.registration.serializers import RegisterSerializer

from apps.accounts.models import Practice, User


class DoctorRegistrationSerializer(RegisterSerializer):
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)
    practice_name = serializers.CharField(required=True, max_length=255)
    specialty = serializers.CharField(required=False, max_length=100, default="")

    def validate_practice_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Practice name is required.")
        return value.strip()

    def custom_signup(self, request, user):
        practice = Practice.objects.create(
            name=self.validated_data["practice_name"],
            subscription_tier="solo",
        )
        user.first_name = self.validated_data["first_name"]
        user.last_name = self.validated_data["last_name"]
        user.role = "doctor"
        user.practice = practice
        user.specialty = self.validated_data.get("specialty", "")
        user.save()


class UserDetailSerializer(serializers.ModelSerializer):
    practice_name = serializers.CharField(source="practice.name", read_only=True, default=None)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "specialty",
            "license_number",
            "practice",
            "practice_name",
            "language_preference",
            "created_at",
        ]
        read_only_fields = ["id", "email", "role", "created_at"]


class PracticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Practice
        fields = [
            "id",
            "name",
            "address",
            "phone",
            "subscription_tier",
            "white_label_config",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
```

- [ ] **Step 3 (3 min):** Implement allauth adapter.

File: `backend/apps/accounts/adapters.py`
```python
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
```

- [ ] **Step 4 (3 min):** Implement permissions.

File: `backend/apps/accounts/permissions.py`
```python
from rest_framework.permissions import BasePermission


class IsDoctor(BasePermission):
    """Allow access only to users with doctor role."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "doctor"
        )


class IsAdmin(BasePermission):
    """Allow access only to users with admin role."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )


class IsDoctorOrAdmin(BasePermission):
    """Allow access to doctors and admins."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ("doctor", "admin")
        )


class IsPatient(BasePermission):
    """Allow access only to users with patient role."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "patient"
        )


class IsSamePractice(BasePermission):
    """Ensure user can only access resources within their practice."""

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "practice"):
            return obj.practice_id == request.user.practice_id
        if hasattr(obj, "patient"):
            return obj.patient.practice_id == request.user.practice_id
        if hasattr(obj, "doctor"):
            return obj.doctor.practice_id == request.user.practice_id
        return False
```

- [ ] **Step 5 (3 min):** Create auth URL configuration and patient OTP views.

File: `backend/apps/accounts/views.py`
```python
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.adapters import PatientOTPAdapter, RateLimitExceeded


class AuthEndpointThrottle(AnonRateThrottle):
    rate = "10/min"


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AuthEndpointThrottle])
def patient_otp_send(request):
    phone = request.data.get("phone")
    if not phone:
        return Response(
            {"error": "Phone number is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    adapter = PatientOTPAdapter()
    try:
        adapter.send_otp(phone)
    except RateLimitExceeded as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    except Exception:
        return Response(
            {"error": "Could not send verification code."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return Response(
        {"message": "Verification code sent."},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AuthEndpointThrottle])
def patient_otp_verify(request):
    phone = request.data.get("phone")
    code = request.data.get("code")
    if not phone or not code:
        return Response(
            {"error": "Phone and code are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    adapter = PatientOTPAdapter()
    try:
        user = adapter.verify_otp(phone, code)
    except RateLimitExceeded as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    if user is None:
        return Response(
            {"error": "Invalid verification code."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user_id": str(user.id),
        },
        status=status.HTTP_200_OK,
    )
```

File: `backend/apps/accounts/urls.py`
```python
from django.urls import include, path

from apps.accounts.views import patient_otp_send, patient_otp_verify

urlpatterns = [
    # dj-rest-auth endpoints (login, logout, user, password)
    path("", include("dj_rest_auth.urls")),
    # dj-rest-auth registration
    path("registration/", include("dj_rest_auth.registration.urls")),
    # Custom patient OTP endpoints
    path("patient/otp/send/", patient_otp_send, name="patient-otp-send"),
    path("patient/otp/verify/", patient_otp_verify, name="patient-otp-verify"),
]
```

File: `backend/apps/accounts/practice_urls.py`
```python
from django.urls import path

from apps.accounts.practice_views import (
    PracticeDetailView,
    PracticeAuditLogView,
    PracticeStatsView,
)

urlpatterns = [
    path("", PracticeDetailView.as_view(), name="practice-detail"),
    path("stats/", PracticeStatsView.as_view(), name="practice-stats"),
    path("audit-log/", PracticeAuditLogView.as_view(), name="practice-audit-log"),
]
```

File: `backend/apps/accounts/practice_views.py`
```python
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Practice
from apps.accounts.permissions import IsDoctorOrAdmin, IsAdmin
from apps.accounts.serializers import PracticeSerializer
from apps.audit.models import AuditLog


class PracticeDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = PracticeSerializer
    permission_classes = [IsDoctorOrAdmin]

    def get_object(self):
        return self.request.user.practice


class PracticeStatsView(APIView):
    permission_classes = [IsDoctorOrAdmin]

    def get(self, request):
        from apps.encounters.models import Encounter
        from apps.patients.models import Patient

        practice = request.user.practice
        stats = {
            "total_patients": Patient.objects.filter(practice=practice).count(),
            "total_encounters": Encounter.objects.filter(
                doctor__practice=practice
            ).count(),
            "encounters_by_status": {},
        }
        for status_choice in Encounter.Status.values:
            count = Encounter.objects.filter(
                doctor__practice=practice, status=status_choice
            ).count()
            if count > 0:
                stats["encounters_by_status"][status_choice] = count
        return Response(stats)


class PracticeAuditLogView(generics.ListAPIView):
    permission_classes = [IsAdmin]

    def get_queryset(self):
        practice = self.request.user.practice
        return AuditLog.objects.filter(user__practice=practice)

    class AuditLogSerializer:
        pass  # Placeholder - implemented in Task 3.1 Step 6

    def get_serializer_class(self):
        from rest_framework import serializers

        class AuditLogListSerializer(serializers.ModelSerializer):
            user_email = serializers.CharField(source="user.email", read_only=True)

            class Meta:
                model = AuditLog
                fields = [
                    "id",
                    "user_email",
                    "action",
                    "resource_type",
                    "resource_id",
                    "ip_address",
                    "phi_accessed",
                    "created_at",
                ]

        return AuditLogListSerializer
```

Run: `cd backend && python -m pytest apps/accounts/tests/test_auth.py -v`
Verify: Tests pass.

### Task 3.2: Admin configuration

- [ ] **Step 1 (2 min):** Create admin registrations for all models.

File: `backend/apps/accounts/admin.py`
```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import Practice, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "role", "practice", "is_active", "created_at")
    list_filter = ("role", "is_active", "practice")
    search_fields = ("email",)
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal", {"fields": ("first_name", "last_name", "phone")}),
        ("Professional", {"fields": ("role", "specialty", "license_number", "practice")}),
        ("Preferences", {"fields": ("language_preference",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {"fields": ("email", "password1", "password2", "role", "practice")}),
    )


@admin.register(Practice)
class PracticeAdmin(admin.ModelAdmin):
    list_display = ("name", "subscription_tier", "created_at")
    list_filter = ("subscription_tier",)
    search_fields = ("name",)
```

File: `backend/apps/patients/admin.py`
```python
from django.contrib import admin

from apps.patients.models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("id", "practice", "language_preference", "created_at")
    list_filter = ("practice", "language_preference")
    # Do not display encrypted fields in list view
    readonly_fields = ("name_search_hash",)
```

File: `backend/apps/encounters/admin.py`
```python
from django.contrib import admin

from apps.encounters.models import Encounter, Recording, Transcript


@admin.register(Encounter)
class EncounterAdmin(admin.ModelAdmin):
    list_display = ("id", "doctor", "patient", "encounter_date", "status", "input_method")
    list_filter = ("status", "input_method", "encounter_date")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Recording)
class RecordingAdmin(admin.ModelAdmin):
    list_display = ("id", "encounter", "format", "transcription_status", "duration_seconds")
    list_filter = ("format", "transcription_status")


@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ("id", "encounter", "language_detected", "confidence_score")
    readonly_fields = ("id", "created_at", "updated_at")
```

File: `backend/apps/notes/admin.py`
```python
from django.contrib import admin

from apps.notes.models import ClinicalNote, PromptVersion


@admin.register(ClinicalNote)
class ClinicalNoteAdmin(admin.ModelAdmin):
    list_display = ("id", "encounter", "note_type", "ai_generated", "doctor_edited", "approved_at")
    list_filter = ("note_type", "ai_generated", "doctor_edited")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(PromptVersion)
class PromptVersionAdmin(admin.ModelAdmin):
    list_display = ("prompt_name", "version", "is_active", "created_at")
    list_filter = ("prompt_name", "is_active")
```

File: `backend/apps/summaries/admin.py`
```python
from django.contrib import admin

from apps.summaries.models import PatientSummary


@admin.register(PatientSummary)
class PatientSummaryAdmin(admin.ModelAdmin):
    list_display = ("id", "encounter", "reading_level", "delivery_status", "delivered_at")
    list_filter = ("reading_level", "delivery_status", "delivery_method")
    readonly_fields = ("id", "created_at", "updated_at")
```

File: `backend/apps/audit/admin.py`
```python
from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "action", "resource_type", "resource_id", "phi_accessed", "created_at")
    list_filter = ("action", "resource_type", "phi_accessed")
    readonly_fields = (
        "id", "user", "action", "resource_type", "resource_id",
        "ip_address", "user_agent", "phi_accessed", "details", "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
```

---

## Chunk 4: Core API Endpoints (DRF ViewSets)

### Task 4.1: Patient API

- [ ] **Step 1 (3 min):** Write failing tests.

File: `backend/apps/patients/tests/test_api.py`
```python
from datetime import date

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Practice, User
from apps.patients.models import Patient


class PatientAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.other_practice = Practice.objects.create(name="Other Clinic", subscription_tier="solo")
        self.other_doctor = User.objects.create_user(
            email="other@test.com", password="test", role="doctor", practice=self.other_practice
        )
        self.client.force_authenticate(user=self.doctor)

    def test_create_patient(self):
        response = self.client.post(
            "/api/v1/patients/",
            {
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-01-15",
                "email": "john@example.com",
                "phone": "+15551234567",
                "language_preference": "en",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["first_name"] == "John"

    def test_list_patients_filtered_by_practice(self):
        Patient.objects.create(
            practice=self.practice, first_name="A", last_name="B", date_of_birth="1990-01-01"
        )
        Patient.objects.create(
            practice=self.other_practice, first_name="C", last_name="D", date_of_birth="1990-01-01"
        )
        response = self.client.get("/api/v1/patients/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

    def test_get_patient_detail(self):
        patient = Patient.objects.create(
            practice=self.practice, first_name="A", last_name="B", date_of_birth="1990-01-01"
        )
        response = self.client.get(f"/api/v1/patients/{patient.id}/")
        assert response.status_code == status.HTTP_200_OK

    def test_cannot_access_other_practice_patient(self):
        patient = Patient.objects.create(
            practice=self.other_practice, first_name="X", last_name="Y", date_of_birth="1990-01-01"
        )
        response = self.client.get(f"/api/v1/patients/{patient.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_patient(self):
        patient = Patient.objects.create(
            practice=self.practice, first_name="A", last_name="B", date_of_birth="1990-01-01"
        )
        response = self.client.patch(
            f"/api/v1/patients/{patient.id}/",
            {"language_preference": "es"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        patient.refresh_from_db()
        assert patient.language_preference == "es"

    def test_unauthenticated_access_denied(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/v1/patients/")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_patient_role_cannot_list_patients(self):
        patient_user = User.objects.create_user(
            email="patient@test.com", role="patient"
        )
        self.client.force_authenticate(user=patient_user)
        response = self.client.get("/api/v1/patients/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
```

- [ ] **Step 2 (4 min):** Implement patient serializers, views, and URLs.

File: `backend/apps/patients/serializers.py`
```python
from rest_framework import serializers

from apps.patients.models import Patient


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "date_of_birth",
            "language_preference",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["practice"] = request.user.practice
        return super().create(validated_data)


class PatientListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list view (no full PHI)."""

    class Meta:
        model = Patient
        fields = [
            "id",
            "first_name",
            "last_name",
            "language_preference",
            "created_at",
        ]
```

File: `backend/apps/patients/filters.py`
```python
import hashlib
import hmac

from django.conf import settings
from django_filters import rest_framework as filters

from apps.patients.models import Patient


class PatientFilter(filters.FilterSet):
    name = filters.CharFilter(method="filter_by_name")

    class Meta:
        model = Patient
        fields = ["language_preference"]

    def filter_by_name(self, queryset, name, value):
        """Search patients by blind index hash of normalized name."""
        normalized = value.strip().lower()
        search_hash = hmac.new(
            settings.FIELD_ENCRYPTION_KEY.encode(),
            normalized.encode(),
            hashlib.sha256,
        ).hexdigest()
        return queryset.filter(name_search_hash=search_hash)
```

File: `backend/apps/patients/views.py`
```python
from rest_framework import viewsets

from apps.accounts.permissions import IsDoctorOrAdmin, IsSamePractice
from apps.patients.filters import PatientFilter
from apps.patients.models import Patient
from apps.patients.serializers import PatientListSerializer, PatientSerializer


class PatientViewSet(viewsets.ModelViewSet):
    serializer_class = PatientSerializer
    permission_classes = [IsDoctorOrAdmin]
    filterset_class = PatientFilter

    def get_queryset(self):
        return Patient.objects.filter(practice=self.request.user.practice)

    def get_serializer_class(self):
        if self.action == "list":
            return PatientListSerializer
        return PatientSerializer
```

File: `backend/apps/patients/urls.py`
```python
from rest_framework.routers import DefaultRouter

from apps.patients.views import PatientViewSet

router = DefaultRouter()
router.register("", PatientViewSet, basename="patient")

urlpatterns = router.urls
```

Run: `cd backend && python -m pytest apps/patients/tests/test_api.py -v`
Verify: All tests pass.

### Task 4.2: Encounter API (CRUD + input method endpoints)

- [ ] **Step 1 (4 min):** Write failing tests.

File: `backend/apps/encounters/tests/test_api.py`
```python
from datetime import date

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.patients.models import Patient


class EncounterAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D", date_of_birth="1990-01-01"
        )
        self.client.force_authenticate(user=self.doctor)

    def test_create_encounter(self):
        response = self.client.post(
            "/api/v1/encounters/",
            {
                "patient": str(self.patient.id),
                "encounter_date": "2026-03-15",
                "input_method": "paste",
                "consent_recording": False,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "uploading"

    def test_list_encounters_filtered_by_practice(self):
        Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="paste",
        )
        response = self.client.get("/api/v1/encounters/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

    def test_get_encounter_detail(self):
        encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="paste",
        )
        response = self.client.get(f"/api/v1/encounters/{encounter.id}/")
        assert response.status_code == status.HTTP_200_OK

    def test_paste_text_input(self):
        encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="paste",
            status="uploading",
        )
        response = self.client.post(
            f"/api/v1/encounters/{encounter.id}/paste/",
            {"text": "Patient presents with acute headache..."},
            format="json",
        )
        assert response.status_code == status.HTTP_202_ACCEPTED

    def test_update_encounter_status(self):
        encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="paste",
            status="ready_for_review",
        )
        response = self.client.patch(
            f"/api/v1/encounters/{encounter.id}/",
            {"status": "approved"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_cannot_access_other_practice_encounter(self):
        other_practice = Practice.objects.create(name="Other", subscription_tier="solo")
        other_doctor = User.objects.create_user(
            email="other@test.com", password="test", role="doctor", practice=other_practice
        )
        other_patient = Patient.objects.create(
            practice=other_practice, first_name="X", last_name="Y", date_of_birth="1990-01-01"
        )
        encounter = Encounter.objects.create(
            doctor=other_doctor,
            patient=other_patient,
            encounter_date=date.today(),
            input_method="paste",
        )
        response = self.client.get(f"/api/v1/encounters/{encounter.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
```

- [ ] **Step 2 (5 min):** Implement encounter serializers, views, and URLs.

File: `backend/apps/encounters/serializers.py`
```python
from rest_framework import serializers

from apps.encounters.models import Encounter, Recording, Transcript


class TranscriptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transcript
        fields = [
            "id",
            "raw_text",
            "speaker_segments",
            "medical_terms_detected",
            "confidence_score",
            "language_detected",
            "created_at",
        ]
        read_only_fields = fields


class RecordingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recording
        fields = [
            "id",
            "storage_url",
            "duration_seconds",
            "file_size_bytes",
            "format",
            "transcription_status",
            "created_at",
        ]
        read_only_fields = fields


class EncounterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Encounter
        fields = [
            "id",
            "doctor",
            "patient",
            "encounter_date",
            "input_method",
            "status",
            "consent_recording",
            "consent_timestamp",
            "consent_method",
            "consent_jurisdiction_state",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "doctor", "status", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["doctor"] = self.context["request"].user
        return super().create(validated_data)


class EncounterDetailSerializer(EncounterSerializer):
    """Detail serializer with nested outputs."""

    has_recording = serializers.SerializerMethodField()
    has_transcript = serializers.SerializerMethodField()
    has_note = serializers.SerializerMethodField()
    has_summary = serializers.SerializerMethodField()

    class Meta(EncounterSerializer.Meta):
        fields = EncounterSerializer.Meta.fields + [
            "has_recording",
            "has_transcript",
            "has_note",
            "has_summary",
        ]

    def get_has_recording(self, obj):
        return hasattr(obj, "recording")

    def get_has_transcript(self, obj):
        return hasattr(obj, "transcript")

    def get_has_note(self, obj):
        return hasattr(obj, "clinical_note")

    def get_has_summary(self, obj):
        return hasattr(obj, "patient_summary")


class PasteInputSerializer(serializers.Serializer):
    text = serializers.CharField(min_length=10, max_length=50000)


class DictationInputSerializer(serializers.Serializer):
    text = serializers.CharField(min_length=10, max_length=50000)
```

File: `backend/apps/encounters/views.py`
```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsDoctorOrAdmin
from apps.encounters.models import Encounter, Transcript
from apps.encounters.serializers import (
    EncounterDetailSerializer,
    EncounterSerializer,
    PasteInputSerializer,
    DictationInputSerializer,
    TranscriptSerializer,
)


class EncounterViewSet(viewsets.ModelViewSet):
    serializer_class = EncounterSerializer
    permission_classes = [IsDoctorOrAdmin]

    def get_queryset(self):
        return Encounter.objects.filter(
            doctor__practice=self.request.user.practice
        ).select_related("doctor", "patient")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return EncounterDetailSerializer
        return EncounterSerializer

    @action(detail=True, methods=["post"], url_path="paste")
    def paste_input(self, request, pk=None):
        encounter = self.get_object()
        serializer = PasteInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data["text"]

        # Create transcript directly from pasted text
        Transcript.objects.update_or_create(
            encounter=encounter,
            defaults={
                "raw_text": text,
                "speaker_segments": [],
                "confidence_score": 1.0,
                "language_detected": "en",
            },
        )

        encounter.status = Encounter.Status.GENERATING_NOTE
        encounter.save(update_fields=["status", "updated_at"])

        # Dispatch SOAP note worker
        from workers.soap_note import generate_soap_note_task

        generate_soap_note_task.delay(str(encounter.id))

        return Response(
            {"status": "processing", "encounter_id": str(encounter.id)},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"], url_path="dictation")
    def dictation_input(self, request, pk=None):
        encounter = self.get_object()
        serializer = DictationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data["text"]

        Transcript.objects.update_or_create(
            encounter=encounter,
            defaults={
                "raw_text": text,
                "speaker_segments": [],
                "confidence_score": 1.0,
                "language_detected": "en",
            },
        )

        encounter.status = Encounter.Status.GENERATING_NOTE
        encounter.save(update_fields=["status", "updated_at"])

        from workers.soap_note import generate_soap_note_task

        generate_soap_note_task.delay(str(encounter.id))

        return Response(
            {"status": "processing", "encounter_id": str(encounter.id)},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"], url_path="recording")
    def upload_recording(self, request, pk=None):
        encounter = self.get_object()
        audio_file = request.FILES.get("audio")
        if not audio_file:
            return Response(
                {"error": "Audio file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from services.storage_service import StorageService
        from apps.encounters.models import Recording

        storage = StorageService()
        storage_url = storage.upload_audio(audio_file, encounter.id)

        Recording.objects.update_or_create(
            encounter=encounter,
            defaults={
                "storage_url": storage_url,
                "duration_seconds": 0,  # Updated after transcription
                "file_size_bytes": audio_file.size,
                "format": audio_file.name.rsplit(".", 1)[-1] if "." in audio_file.name else "wav",
                "transcription_status": "pending",
            },
        )

        encounter.status = Encounter.Status.TRANSCRIBING
        encounter.save(update_fields=["status", "updated_at"])

        from workers.transcription import transcription_task

        transcription_task.delay(str(encounter.id))

        return Response(
            {"status": "transcribing", "encounter_id": str(encounter.id)},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"], url_path="scan")
    def upload_scan(self, request, pk=None):
        encounter = self.get_object()
        scan_file = request.FILES.get("image")
        if not scan_file:
            return Response(
                {"error": "Image file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from services.storage_service import StorageService

        storage = StorageService()
        storage_url = storage.upload_scan(scan_file, encounter.id)

        encounter.status = Encounter.Status.TRANSCRIBING
        encounter.save(update_fields=["status", "updated_at"])

        from workers.ocr import ocr_task

        ocr_task.delay(str(encounter.id), storage_url)

        return Response(
            {"status": "processing_scan", "encounter_id": str(encounter.id)},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["get"], url_path="transcript")
    def get_transcript(self, request, pk=None):
        encounter = self.get_object()
        try:
            transcript = encounter.transcript
        except Transcript.DoesNotExist:
            return Response(
                {"error": "No transcript available."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = TranscriptSerializer(transcript)
        return Response(serializer.data)
```

File: `backend/apps/encounters/urls.py`
```python
from rest_framework.routers import DefaultRouter

from apps.encounters.views import EncounterViewSet

router = DefaultRouter()
router.register("", EncounterViewSet, basename="encounter")

urlpatterns = router.urls
```

File: `backend/apps/encounters/filters.py`
```python
from django_filters import rest_framework as filters

from apps.encounters.models import Encounter


class EncounterFilter(filters.FilterSet):
    status = filters.ChoiceFilter(choices=Encounter.Status.choices)
    input_method = filters.ChoiceFilter(choices=Encounter.InputMethod.choices)
    date_from = filters.DateFilter(field_name="encounter_date", lookup_expr="gte")
    date_to = filters.DateFilter(field_name="encounter_date", lookup_expr="lte")
    patient = filters.UUIDFilter(field_name="patient_id")

    class Meta:
        model = Encounter
        fields = ["status", "input_method", "patient"]
```

Run: `cd backend && python -m pytest apps/encounters/tests/test_api.py -v`
Verify: All tests pass.

### Task 4.3: Notes API (CRUD + approve)

- [ ] **Step 1 (3 min):** Write failing tests.

File: `backend/apps/notes/tests/test_api.py`
```python
from datetime import date

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote, PromptVersion
from apps.patients.models import Patient


class NoteAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D", date_of_birth="1990-01-01"
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="paste",
            status="ready_for_review",
        )
        self.prompt_version = PromptVersion.objects.create(
            prompt_name="soap_note",
            version="1.0.0",
            template_text="prompt",
            is_active=True,
        )
        self.note = ClinicalNote.objects.create(
            encounter=self.encounter,
            note_type="soap",
            subjective="S",
            objective="O",
            assessment="A",
            plan="P",
            ai_generated=True,
            prompt_version=self.prompt_version,
        )
        self.client.force_authenticate(user=self.doctor)

    def test_get_note_for_encounter(self):
        response = self.client.get(f"/api/v1/encounters/{self.encounter.id}/note/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["subjective"] == "S"

    def test_edit_note(self):
        response = self.client.patch(
            f"/api/v1/encounters/{self.encounter.id}/note/",
            {"subjective": "Updated subjective text", "doctor_edited": True},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        self.note.refresh_from_db()
        assert self.note.subjective == "Updated subjective text"
        assert self.note.doctor_edited is True

    def test_approve_note(self):
        response = self.client.post(
            f"/api/v1/encounters/{self.encounter.id}/note/approve/"
        )
        assert response.status_code == status.HTTP_200_OK
        self.note.refresh_from_db()
        assert self.note.approved_at is not None
        assert self.note.approved_by == self.doctor
        self.encounter.refresh_from_db()
        assert self.encounter.status == "approved"
```

- [ ] **Step 2 (4 min):** Implement notes serializers, views, and URLs.

File: `backend/apps/notes/serializers.py`
```python
from rest_framework import serializers

from apps.notes.models import ClinicalNote, PromptVersion


class PromptVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromptVersion
        fields = ["id", "prompt_name", "version", "is_active", "created_at"]
        read_only_fields = fields


class ClinicalNoteSerializer(serializers.ModelSerializer):
    prompt_version_detail = PromptVersionSerializer(source="prompt_version", read_only=True)

    class Meta:
        model = ClinicalNote
        fields = [
            "id",
            "encounter",
            "note_type",
            "subjective",
            "objective",
            "assessment",
            "plan",
            "raw_content",
            "icd10_codes",
            "cpt_codes",
            "ai_generated",
            "doctor_edited",
            "approved_at",
            "approved_by",
            "prompt_version",
            "prompt_version_detail",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "encounter",
            "ai_generated",
            "approved_at",
            "approved_by",
            "prompt_version",
            "created_at",
            "updated_at",
        ]
```

File: `backend/apps/notes/views.py`
```python
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.permissions import IsDoctorOrAdmin
from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote
from apps.notes.serializers import ClinicalNoteSerializer


@api_view(["GET", "PATCH"])
@permission_classes([IsDoctorOrAdmin])
def encounter_note(request, encounter_id):
    try:
        encounter = Encounter.objects.get(
            id=encounter_id,
            doctor__practice=request.user.practice,
        )
    except Encounter.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    try:
        note = encounter.clinical_note
    except ClinicalNote.DoesNotExist:
        return Response(
            {"error": "No note available for this encounter."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        serializer = ClinicalNoteSerializer(note)
        return Response(serializer.data)

    if request.method == "PATCH":
        serializer = ClinicalNoteSerializer(note, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsDoctorOrAdmin])
def approve_note(request, encounter_id):
    try:
        encounter = Encounter.objects.get(
            id=encounter_id,
            doctor__practice=request.user.practice,
        )
    except Encounter.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    try:
        note = encounter.clinical_note
    except ClinicalNote.DoesNotExist:
        return Response(
            {"error": "No note available for this encounter."},
            status=status.HTTP_404_NOT_FOUND,
        )

    note.approved_at = timezone.now()
    note.approved_by = request.user
    note.save(update_fields=["approved_at", "approved_by", "updated_at"])

    encounter.status = Encounter.Status.APPROVED
    encounter.save(update_fields=["status", "updated_at"])

    serializer = ClinicalNoteSerializer(note)
    return Response(serializer.data)
```

File: `backend/apps/notes/urls.py`
```python
from django.urls import path

# Notes are accessed through encounter URLs; this file is for any standalone note endpoints.
urlpatterns = []
```

Add note endpoints to encounter URLs. Update `backend/apps/encounters/urls.py`:
```python
from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.encounters.views import EncounterViewSet
from apps.notes.views import encounter_note, approve_note

router = DefaultRouter()
router.register("", EncounterViewSet, basename="encounter")

urlpatterns = router.urls + [
    path("<uuid:encounter_id>/note/", encounter_note, name="encounter-note"),
    path("<uuid:encounter_id>/note/approve/", approve_note, name="encounter-note-approve"),
]
```

Run: `cd backend && python -m pytest apps/notes/tests/test_api.py -v`
Verify: All tests pass.

### Task 4.4: Summary API + delivery + patient-facing endpoints

- [ ] **Step 1 (3 min):** Write failing tests.

File: `backend/apps/summaries/tests/test_api.py`

```python
from datetime import date

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote, PromptVersion
from apps.patients.models import Patient
from apps.summaries.models import PatientSummary


class SummaryAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D", date_of_birth="1990-01-01"
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor, patient=self.patient,
            encounter_date=date.today(), input_method="paste", status="approved",
        )
        self.pv = PromptVersion.objects.create(
            prompt_name="patient_summary", version="1.0.0", template_text="t", is_active=True
        )
        self.note = ClinicalNote.objects.create(
            encounter=self.encounter, note_type="soap",
            subjective="S", objective="O", assessment="A", plan="P",
            prompt_version=self.pv,
        )
        self.summary = PatientSummary.objects.create(
            encounter=self.encounter, clinical_note=self.note,
            summary_en="Your visit summary.", reading_level="grade_8",
            disclaimer_text="Disclaimer.", delivery_status="pending",
            prompt_version=self.pv,
        )
        self.client.force_authenticate(user=self.doctor)

    def test_get_summary_for_encounter(self):
        response = self.client.get(f"/api/v1/encounters/{self.encounter.id}/summary/")
        assert response.status_code == status.HTTP_200_OK
        assert "Your visit summary" in response.data["summary_en"]

    def test_send_summary(self):
        response = self.client.post(
            f"/api/v1/encounters/{self.encounter.id}/summary/send/",
            {"delivery_method": "app"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        self.summary.refresh_from_db()
        assert self.summary.delivery_status == "sent"

    def test_get_summary_not_found(self):
        encounter2 = Encounter.objects.create(
            doctor=self.doctor, patient=self.patient,
            encounter_date=date.today(), input_method="paste", status="uploading",
        )
        response = self.client.get(f"/api/v1/encounters/{encounter2.id}/summary/")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class PatientFacingSummaryAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient_record = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D",
            date_of_birth="1990-01-01", phone="+15551234567",
        )
        self.patient_user = User.objects.create_user(
            email="+15551234567@patient.medicalnote.local",
            role="patient", phone="+15551234567",
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor, patient=self.patient_record,
            encounter_date=date.today(), input_method="paste", status="delivered",
        )
        self.pv = PromptVersion.objects.create(
            prompt_name="patient_summary", version="1.0.0", template_text="t", is_active=True
        )
        self.note = ClinicalNote.objects.create(
            encounter=self.encounter, note_type="soap",
            subjective="S", objective="O", assessment="A", plan="P",
            prompt_version=self.pv,
        )
        self.summary = PatientSummary.objects.create(
            encounter=self.encounter, clinical_note=self.note,
            summary_en="Summary.", reading_level="grade_8",
            disclaimer_text="Disclaimer.", delivery_status="sent",
            prompt_version=self.pv,
        )
        self.client.force_authenticate(user=self.patient_user)

    def test_patient_list_own_summaries(self):
        response = self.client.get("/api/v1/patient/summaries/")
        assert response.status_code == status.HTTP_200_OK

    def test_patient_mark_summary_read(self):
        response = self.client.patch(
            f"/api/v1/patient/summaries/{self.summary.id}/read/"
        )
        assert response.status_code == status.HTTP_200_OK
        self.summary.refresh_from_db()
        assert self.summary.delivery_status == "viewed"
        assert self.summary.viewed_at is not None
```

- [ ] **Step 2 (4 min):** Implement summary views and URLs.

File: `backend/apps/summaries/serializers.py`
```python
from rest_framework import serializers
from apps.summaries.models import PatientSummary


class PatientSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientSummary
        fields = [
            "id", "encounter", "clinical_note", "summary_en", "summary_es",
            "reading_level", "medical_terms_explained", "disclaimer_text",
            "delivery_status", "delivered_at", "viewed_at", "delivery_method",
            "prompt_version", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "encounter", "clinical_note", "summary_en", "summary_es",
            "reading_level", "medical_terms_explained", "disclaimer_text",
            "prompt_version", "created_at", "updated_at",
        ]


class PatientFacingSummarySerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    encounter_date = serializers.DateField(source="encounter.encounter_date", read_only=True)

    class Meta:
        model = PatientSummary
        fields = [
            "id", "summary_en", "summary_es", "reading_level",
            "medical_terms_explained", "disclaimer_text",
            "encounter_date", "doctor_name", "delivery_status",
            "viewed_at", "created_at",
        ]

    def get_doctor_name(self, obj):
        doctor = obj.encounter.doctor
        return f"Dr. {doctor.last_name}" if doctor.last_name else doctor.email
```

File: `backend/apps/summaries/views.py`
```python
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.permissions import IsDoctorOrAdmin, IsPatient
from apps.encounters.models import Encounter
from apps.summaries.models import PatientSummary
from apps.summaries.serializers import PatientSummarySerializer


@api_view(["GET"])
@permission_classes([IsDoctorOrAdmin])
def encounter_summary(request, encounter_id):
    try:
        encounter = Encounter.objects.get(
            id=encounter_id, doctor__practice=request.user.practice
        )
    except Encounter.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    try:
        summary = encounter.patient_summary
    except PatientSummary.DoesNotExist:
        return Response({"error": "No summary available."}, status=status.HTTP_404_NOT_FOUND)
    return Response(PatientSummarySerializer(summary).data)


@api_view(["POST"])
@permission_classes([IsDoctorOrAdmin])
def send_summary(request, encounter_id):
    try:
        encounter = Encounter.objects.get(
            id=encounter_id, doctor__practice=request.user.practice
        )
    except Encounter.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    try:
        summary = encounter.patient_summary
    except PatientSummary.DoesNotExist:
        return Response({"error": "No summary available."}, status=status.HTTP_404_NOT_FOUND)

    delivery_method = request.data.get("delivery_method", "app")
    summary.delivery_status = "sent"
    summary.delivered_at = timezone.now()
    summary.delivery_method = delivery_method
    summary.save(update_fields=["delivery_status", "delivered_at", "delivery_method", "updated_at"])

    encounter.status = Encounter.Status.DELIVERED
    encounter.save(update_fields=["status", "updated_at"])

    return Response(PatientSummarySerializer(summary).data)
```

File: `backend/apps/summaries/patient_views.py`
```python
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.permissions import IsPatient
from apps.summaries.models import PatientSummary
from apps.summaries.serializers import PatientFacingSummarySerializer


@api_view(["GET"])
@permission_classes([IsPatient])
def patient_summary_list(request):
    summaries = PatientSummary.objects.filter(
        encounter__patient__phone=request.user.phone,
        delivery_status__in=["sent", "viewed"],
    ).select_related("encounter", "encounter__doctor").order_by("-created_at")
    serializer = PatientFacingSummarySerializer(summaries, many=True)
    return Response({"count": summaries.count(), "results": serializer.data})


@api_view(["GET"])
@permission_classes([IsPatient])
def patient_summary_detail(request, summary_id):
    try:
        summary = PatientSummary.objects.select_related(
            "encounter", "encounter__doctor"
        ).get(id=summary_id, encounter__patient__phone=request.user.phone)
    except PatientSummary.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response(PatientFacingSummarySerializer(summary).data)


@api_view(["PATCH"])
@permission_classes([IsPatient])
def patient_summary_mark_read(request, summary_id):
    try:
        summary = PatientSummary.objects.get(
            id=summary_id, encounter__patient__phone=request.user.phone
        )
    except PatientSummary.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    summary.delivery_status = "viewed"
    summary.viewed_at = timezone.now()
    summary.save(update_fields=["delivery_status", "viewed_at", "updated_at"])
    return Response({"status": "viewed"})
```

File: `backend/apps/summaries/urls.py`
```python
from django.urls import path
from apps.summaries.views import encounter_summary, send_summary

urlpatterns = [
    # These are mounted under /api/v1/encounters/ via encounter urls
]

# Standalone encounter-scoped summary endpoints added to encounters/urls.py
```

File: `backend/apps/summaries/patient_urls.py`
```python
from django.urls import path
from apps.summaries.patient_views import (
    patient_summary_list, patient_summary_detail, patient_summary_mark_read,
)

urlpatterns = [
    path("summaries/", patient_summary_list, name="patient-summaries"),
    path("summaries/<uuid:summary_id>/", patient_summary_detail, name="patient-summary-detail"),
    path("summaries/<uuid:summary_id>/read/", patient_summary_mark_read, name="patient-summary-read"),
]
```

Update `backend/apps/encounters/urls.py` to include summary endpoints:
```python
from django.urls import path
from rest_framework.routers import DefaultRouter
from apps.encounters.views import EncounterViewSet
from apps.notes.views import encounter_note, approve_note
from apps.summaries.views import encounter_summary, send_summary

router = DefaultRouter()
router.register("", EncounterViewSet, basename="encounter")

urlpatterns = router.urls + [
    path("<uuid:encounter_id>/note/", encounter_note, name="encounter-note"),
    path("<uuid:encounter_id>/note/approve/", approve_note, name="encounter-note-approve"),
    path("<uuid:encounter_id>/summary/", encounter_summary, name="encounter-summary"),
    path("<uuid:encounter_id>/summary/send/", send_summary, name="encounter-summary-send"),
]
```

Run: `cd backend && python -m pytest apps/summaries/tests/test_api.py -v`
Verify: All tests pass.

### Task 4.5: Widget API

- [ ] **Step 1 (3 min):** Write failing tests.

File: `backend/apps/widget/tests/__init__.py`
```python
```

File: `backend/apps/widget/tests/test_api.py`
```python
from datetime import date
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote, PromptVersion
from apps.patients.models import Patient
from apps.summaries.models import PatientSummary


class WidgetAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.practice = Practice.objects.create(
            name="Clinic", subscription_tier="enterprise",
            white_label_config={
                "logo_url": "https://cdn.example.com/logo.png",
                "brand_color": "#FF5733",
                "widget_key": "wk_test123",
            },
        )

    def test_get_widget_config(self):
        response = self.client.get("/api/v1/widget/config/wk_test123/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["brand_color"] == "#FF5733"

    def test_widget_config_invalid_key(self):
        response = self.client.get("/api/v1/widget/config/wk_invalid/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
```

- [ ] **Step 2 (3 min):** Implement widget views.

File: `backend/apps/widget/models.py`
```python
# Widget config lives in Practice.white_label_config (JSONField)
# No separate model needed for Phase 1
```

File: `backend/apps/widget/serializers.py`
```python
from rest_framework import serializers


class WidgetConfigSerializer(serializers.Serializer):
    logo_url = serializers.URLField(required=False, default="")
    brand_color = serializers.CharField(required=False, default="#000000")
    custom_domain = serializers.CharField(required=False, default="")
    practice_name = serializers.CharField(read_only=True)
```

File: `backend/apps/widget/views.py`
```python
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.models import Practice
from apps.summaries.models import PatientSummary
from apps.summaries.serializers import PatientFacingSummarySerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def widget_config(request, widget_key):
    try:
        practice = Practice.objects.get(white_label_config__widget_key=widget_key)
    except Practice.DoesNotExist:
        return Response({"error": "Invalid widget key."}, status=status.HTTP_404_NOT_FOUND)
    config = practice.white_label_config or {}
    config["practice_name"] = practice.name
    return Response(config)


@api_view(["GET"])
@permission_classes([AllowAny])
def widget_summary(request, token):
    signer = TimestampSigner()
    try:
        summary_id = signer.unsign(token, max_age=86400)  # 24h expiry
    except (BadSignature, SignatureExpired):
        return Response({"error": "Invalid or expired token."}, status=status.HTTP_403_FORBIDDEN)
    try:
        summary = PatientSummary.objects.select_related(
            "encounter", "encounter__doctor"
        ).get(id=summary_id)
    except PatientSummary.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response(PatientFacingSummarySerializer(summary).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def widget_summary_read(request, token):
    signer = TimestampSigner()
    try:
        summary_id = signer.unsign(token, max_age=86400)
    except (BadSignature, SignatureExpired):
        return Response({"error": "Invalid or expired token."}, status=status.HTTP_403_FORBIDDEN)
    from django.utils import timezone
    PatientSummary.objects.filter(id=summary_id).update(
        delivery_status="viewed", viewed_at=timezone.now()
    )
    return Response({"status": "viewed"})
```

File: `backend/apps/widget/urls.py`
```python
from django.urls import path
from apps.widget.views import widget_config, widget_summary, widget_summary_read

urlpatterns = [
    path("config/<str:widget_key>/", widget_config, name="widget-config"),
    path("summary/<str:token>/", widget_summary, name="widget-summary"),
    path("summary/<str:token>/read/", widget_summary_read, name="widget-summary-read"),
]
```

Run: `cd backend && python -m pytest apps/widget/tests/test_api.py -v`
Verify: All tests pass.

---

## Chunk 5: Services Layer

### Task 5.1: LLM service (Claude API wrapper)

- [ ] **Step 1 (3 min):** Write failing tests.

File: `backend/services/tests/__init__.py`
```python
```

File: `backend/services/tests/test_llm_service.py`
```python
from unittest.mock import MagicMock, patch
from django.test import TestCase
from services.llm_service import LLMService


class LLMServiceTest(TestCase):
    @patch("services.llm_service.anthropic.Anthropic")
    def test_generate_soap_note(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"subjective":"S","objective":"O","assessment":"A","plan":"P","icd10_codes":["R51.9"],"cpt_codes":["99214"]}')]
        mock_client.messages.create.return_value = mock_response

        service = LLMService()
        result = service.generate_soap_note("Patient has headache.", "1.0.0")
        assert result["subjective"] == "S"
        assert "R51.9" in result["icd10_codes"]

    @patch("services.llm_service.anthropic.Anthropic")
    def test_generate_patient_summary(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"summary_en":"You visited the doctor.","summary_es":"Visitaste al doctor.","medical_terms_explained":[]}')]
        mock_client.messages.create.return_value = mock_response

        service = LLMService()
        result = service.generate_patient_summary(
            subjective="S", objective="O", assessment="A", plan="P",
            reading_level="grade_8", language="en",
        )
        assert "visited" in result["summary_en"]

    @patch("services.llm_service.anthropic.Anthropic")
    def test_invalid_json_raises(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="not valid json")]
        mock_client.messages.create.return_value = mock_response

        service = LLMService()
        with self.assertRaises(ValueError):
            service.generate_soap_note("text", "1.0.0")
```

- [ ] **Step 2 (4 min):** Implement LLM service.

File: `backend/services/__init__.py`
```python
```

File: `backend/services/llm_service.py`
```python
import json
import logging

import anthropic
from django.conf import settings

logger = logging.getLogger(__name__)

SOAP_SYSTEM_PROMPT = """You are a medical documentation assistant. Given a clinical transcript or note text, produce a structured SOAP note as JSON.

Output format (strict JSON, no markdown):
{
  "subjective": "...",
  "objective": "...",
  "assessment": "...",
  "plan": "...",
  "icd10_codes": ["..."],
  "cpt_codes": ["..."]
}"""

SUMMARY_SYSTEM_PROMPT = """Convert the following clinical SOAP note into a patient-friendly summary.

Rules:
- Write at a {reading_level} reading level
- Explain all medical terms in plain language
- Include a list of medical terms with explanations
- Do NOT include medical advice beyond what the doctor documented
- Generate in {language}

Output format (strict JSON, no markdown):
{{
  "summary_en": "...",
  "summary_es": "..." or "",
  "medical_terms_explained": [{{"term": "...", "explanation": "..."}}]
}}"""


class LLMService:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"

    def _call_claude(self, system_prompt: str, user_content: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        return response.content[0].text

    def _parse_json(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}\nResponse: {text[:500]}")
            raise ValueError(f"LLM returned invalid JSON: {e}")

    def generate_soap_note(self, transcript_text: str, prompt_version: str) -> dict:
        raw = self._call_claude(SOAP_SYSTEM_PROMPT, transcript_text)
        result = self._parse_json(raw)
        required_keys = {"subjective", "objective", "assessment", "plan"}
        missing = required_keys - set(result.keys())
        if missing:
            raise ValueError(f"SOAP note missing required fields: {missing}")
        result.setdefault("icd10_codes", [])
        result.setdefault("cpt_codes", [])
        return result

    def generate_patient_summary(
        self, subjective: str, objective: str, assessment: str, plan: str,
        reading_level: str = "grade_8", language: str = "en",
    ) -> dict:
        system = SUMMARY_SYSTEM_PROMPT.format(
            reading_level=reading_level.replace("_", " "),
            language="English and Spanish" if language == "en" else language,
        )
        note_text = f"Subjective: {subjective}\nObjective: {objective}\nAssessment: {assessment}\nPlan: {plan}"
        raw = self._call_claude(system, note_text)
        result = self._parse_json(raw)
        if "summary_en" not in result:
            raise ValueError("Summary missing 'summary_en' field.")
        result.setdefault("summary_es", "")
        result.setdefault("medical_terms_explained", [])
        return result
```

Run: `cd backend && python -m pytest services/tests/test_llm_service.py -v`
Verify: All tests pass.

### Task 5.2: STT service (AWS HealthScribe wrapper)

- [ ] **Step 1 (2 min):** Write failing tests.

File: `backend/services/tests/test_stt_service.py`
```python
from unittest.mock import MagicMock, patch
from django.test import TestCase
from services.stt_service import STTService


class STTServiceTest(TestCase):
    @patch("services.stt_service.boto3.client")
    def test_start_transcription_job(self, mock_boto):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.start_medical_scribe_job.return_value = {
            "MedicalScribeJob": {"MedicalScribeJobName": "job-123", "MedicalScribeJobStatus": "IN_PROGRESS"}
        }
        service = STTService()
        result = service.start_transcription("s3://bucket/audio.wav", "encounter-123")
        assert result["job_name"] == "job-123"

    @patch("services.stt_service.boto3.client")
    def test_get_transcription_result(self, mock_boto):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.get_medical_scribe_job.return_value = {
            "MedicalScribeJob": {
                "MedicalScribeJobStatus": "COMPLETED",
                "MedicalScribeOutput": {
                    "TranscriptFileUri": "s3://output/transcript.json",
                    "ClinicalDocumentUri": "s3://output/clinical.json",
                },
            }
        }
        service = STTService()
        result = service.get_transcription_result("job-123")
        assert result["status"] == "COMPLETED"
```

- [ ] **Step 2 (3 min):** Implement STT service.

File: `backend/services/stt_service.py`
```python
import logging

import boto3
from django.conf import settings

logger = logging.getLogger(__name__)


class STTService:
    def __init__(self):
        self.client = boto3.client(
            "transcribe",
            region_name=settings.AWS_REGION,
        )

    def start_transcription(self, s3_uri: str, encounter_id: str) -> dict:
        job_name = f"medicalnote-{encounter_id}"
        try:
            response = self.client.start_medical_scribe_job(
                MedicalScribeJobName=job_name,
                Media={"MediaFileUri": s3_uri},
                OutputBucketName=settings.AWS_S3_BUCKET,
                DataAccessRoleArn=settings.AWS_KMS_KEY_ID,  # Role ARN in production
                Settings={
                    "ShowSpeakerLabels": True,
                    "MaxSpeakerLabels": 2,
                    "ChannelIdentification": False,
                },
            )
            job = response["MedicalScribeJob"]
            return {
                "job_name": job["MedicalScribeJobName"],
                "status": job["MedicalScribeJobStatus"],
            }
        except Exception as e:
            logger.error(f"Failed to start transcription for {encounter_id}: {e}")
            raise

    def get_transcription_result(self, job_name: str) -> dict:
        try:
            response = self.client.get_medical_scribe_job(
                MedicalScribeJobName=job_name
            )
            job = response["MedicalScribeJob"]
            result = {
                "status": job["MedicalScribeJobStatus"],
                "job_name": job_name,
            }
            if job["MedicalScribeJobStatus"] == "COMPLETED":
                output = job.get("MedicalScribeOutput", {})
                result["transcript_uri"] = output.get("TranscriptFileUri", "")
                result["clinical_uri"] = output.get("ClinicalDocumentUri", "")
            elif job["MedicalScribeJobStatus"] == "FAILED":
                result["failure_reason"] = job.get("FailureReason", "Unknown")
            return result
        except Exception as e:
            logger.error(f"Failed to get transcription result for {job_name}: {e}")
            raise
```

### Task 5.3: OCR service, Storage service, Notification service

- [ ] **Step 1 (3 min):** Write failing tests for all three.

File: `backend/services/tests/test_ocr_service.py`
```python
from unittest.mock import MagicMock, patch
from django.test import TestCase
from services.ocr_service import OCRService


class OCRServiceTest(TestCase):
    @patch("services.ocr_service.boto3.client")
    def test_extract_text(self, mock_boto):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.detect_document_text.return_value = {
            "Blocks": [
                {"BlockType": "LINE", "Text": "Patient Name: John Doe"},
                {"BlockType": "LINE", "Text": "Chief Complaint: Headache"},
            ]
        }
        service = OCRService()
        result = service.extract_text_from_s3("s3://bucket/scan.jpg")
        assert "John Doe" in result
        assert "Headache" in result
```

File: `backend/services/tests/test_storage_service.py`
```python
from unittest.mock import MagicMock, patch
from io import BytesIO
from django.test import TestCase
from services.storage_service import StorageService


class StorageServiceTest(TestCase):
    @patch("services.storage_service.boto3.client")
    def test_upload_audio(self, mock_boto):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        service = StorageService()
        fake_file = MagicMock()
        fake_file.read.return_value = b"audio data"
        fake_file.name = "recording.wav"
        result = service.upload_audio(fake_file, "encounter-123")
        assert "encounter-123" in result
        mock_client.upload_fileobj.assert_called_once()
```

File: `backend/services/tests/test_notification_service.py`
```python
from unittest.mock import MagicMock, patch
from django.test import TestCase
from services.notification_service import NotificationService


class NotificationServiceTest(TestCase):
    @patch("services.notification_service.Client")
    def test_send_sms(self, mock_twilio_cls):
        mock_client = MagicMock()
        mock_twilio_cls.return_value = mock_client
        service = NotificationService()
        service.send_sms("+15551234567", "Test message")
        mock_client.messages.create.assert_called_once()
```

- [ ] **Step 2 (4 min):** Implement all three services.

File: `backend/services/ocr_service.py`
```python
import logging
import boto3
from django.conf import settings

logger = logging.getLogger(__name__)


class OCRService:
    def __init__(self):
        self.client = boto3.client("textract", region_name=settings.AWS_REGION)

    def extract_text_from_s3(self, s3_uri: str) -> str:
        parts = s3_uri.replace("s3://", "").split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        try:
            response = self.client.detect_document_text(
                Document={"S3Object": {"Bucket": bucket, "Name": key}}
            )
            lines = [
                block["Text"]
                for block in response.get("Blocks", [])
                if block["BlockType"] == "LINE"
            ]
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"OCR failed for {s3_uri}: {e}")
            raise
```

File: `backend/services/storage_service.py`
```python
import logging
import uuid
import boto3
from django.conf import settings

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        self.client = boto3.client("s3", region_name=settings.AWS_REGION)
        self.bucket = settings.AWS_S3_BUCKET

    def upload_audio(self, file_obj, encounter_id: str) -> str:
        ext = file_obj.name.rsplit(".", 1)[-1] if hasattr(file_obj, "name") and "." in file_obj.name else "wav"
        key = f"audio/{encounter_id}/{uuid.uuid4()}.{ext}"
        self.client.upload_fileobj(
            file_obj, self.bucket, key,
            ExtraArgs={"ServerSideEncryption": "aws:kms", "SSEKMSKeyId": settings.AWS_KMS_KEY_ID},
        )
        return f"s3://{self.bucket}/{key}"

    def upload_scan(self, file_obj, encounter_id: str) -> str:
        ext = file_obj.name.rsplit(".", 1)[-1] if hasattr(file_obj, "name") and "." in file_obj.name else "jpg"
        key = f"scans/{encounter_id}/{uuid.uuid4()}.{ext}"
        self.client.upload_fileobj(
            file_obj, self.bucket, key,
            ExtraArgs={"ServerSideEncryption": "aws:kms", "SSEKMSKeyId": settings.AWS_KMS_KEY_ID},
        )
        return f"s3://{self.bucket}/{key}"

    def get_presigned_url(self, s3_uri: str, expiry: int = 3600) -> str:
        parts = s3_uri.replace("s3://", "").split("/", 1)
        bucket, key = parts[0], parts[1]
        return self.client.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expiry
        )
```

File: `backend/services/notification_service.py`
```python
import logging
from django.conf import settings
from twilio.rest import Client

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self):
        self.twilio_client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
        )
        self.from_number = settings.TWILIO_PHONE_NUMBER

    def send_sms(self, to: str, body: str) -> None:
        try:
            self.twilio_client.messages.create(
                to=to, from_=self.from_number, body=body
            )
        except Exception as e:
            logger.error(f"SMS send failed to {to}: {e}")
            raise

    def send_push_notification(self, device_token: str, title: str, body: str, data: dict = None) -> None:
        # FCM integration - placeholder for Phase 1
        # In production, use firebase-admin SDK
        logger.info(f"Push notification to {device_token}: {title}")
```

Run: `cd backend && python -m pytest services/tests/ -v`
Verify: All tests pass.

---

## Chunk 6: Celery Workers

### Task 6.1: Transcription worker

- [ ] **Step 1 (3 min):** Write failing tests.

File: `backend/workers/tests/__init__.py`
```python
```

File: `backend/workers/tests/test_transcription.py`
```python
from datetime import date
from unittest.mock import MagicMock, patch
from django.test import TestCase
from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter, Recording
from apps.patients.models import Patient


class TranscriptionTaskTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D", date_of_birth="1990-01-01"
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor, patient=self.patient,
            encounter_date=date.today(), input_method="recording", status="transcribing",
        )
        self.recording = Recording.objects.create(
            encounter=self.encounter, storage_url="s3://bucket/audio.wav",
            duration_seconds=600, file_size_bytes=5000000, format="wav",
            transcription_status="pending",
        )

    @patch("workers.transcription.STTService")
    @patch("workers.transcription.generate_soap_note_task")
    def test_transcription_success(self, mock_soap_task, mock_stt_cls):
        mock_stt = MagicMock()
        mock_stt_cls.return_value = mock_stt
        mock_stt.start_transcription.return_value = {"job_name": "job-1", "status": "COMPLETED"}
        mock_stt.get_transcription_result.return_value = {
            "status": "COMPLETED",
            "transcript_uri": "s3://out/transcript.json",
        }

        from workers.transcription import transcription_task
        with patch("workers.transcription.StorageService") as mock_storage_cls:
            mock_storage = MagicMock()
            mock_storage_cls.return_value = mock_storage
            mock_storage.get_presigned_url.return_value = "https://presigned"

            with patch("workers.transcription.json.loads") as mock_json:
                mock_json.return_value = {
                    "results": {
                        "transcripts": [{"transcript": "Doctor: How are you?"}],
                        "speaker_labels": {"segments": []},
                    }
                }
                with patch("workers.transcription.requests.get") as mock_get:
                    mock_resp = MagicMock()
                    mock_resp.text = "{}"
                    mock_get.return_value = mock_resp

                    transcription_task(str(self.encounter.id))

        self.encounter.refresh_from_db()
        assert self.encounter.status == "generating_note"
```

- [ ] **Step 2 (4 min):** Implement transcription worker.

File: `backend/workers/__init__.py`
```python
```

File: `backend/workers/transcription.py`
```python
import json
import logging
import time

import requests
from celery import shared_task
from django.db import transaction

from apps.encounters.models import Encounter, Recording, Transcript
from services.stt_service import STTService
from services.storage_service import StorageService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    retry_backoff=True,
    retry_backoff_max=90,
    time_limit=300,
    name="workers.transcription.transcription_task",
)
def transcription_task(self, encounter_id: str):
    try:
        encounter = Encounter.objects.select_related("recording").get(id=encounter_id)
        recording = encounter.recording
    except (Encounter.DoesNotExist, Recording.DoesNotExist) as e:
        logger.error(f"Encounter or recording not found: {encounter_id}")
        return

    try:
        stt = STTService()
        job_result = stt.start_transcription(recording.storage_url, encounter_id)
        job_name = job_result["job_name"]

        # Poll for completion (in production, use SNS callback)
        max_polls = 60
        for _ in range(max_polls):
            result = stt.get_transcription_result(job_name)
            if result["status"] == "COMPLETED":
                break
            if result["status"] == "FAILED":
                raise Exception(f"Transcription failed: {result.get('failure_reason')}")
            time.sleep(5)
        else:
            raise Exception("Transcription timed out")

        # Fetch and parse transcript
        storage = StorageService()
        transcript_url = storage.get_presigned_url(result["transcript_uri"])
        transcript_response = requests.get(transcript_url, timeout=30)
        transcript_data = json.loads(transcript_response.text)

        raw_text = ""
        speaker_segments = []
        if "results" in transcript_data:
            transcripts = transcript_data["results"].get("transcripts", [])
            raw_text = " ".join(t.get("transcript", "") for t in transcripts)
            segments_data = transcript_data["results"].get("speaker_labels", {}).get("segments", [])
            for seg in segments_data:
                speaker_segments.append({
                    "speaker": seg.get("speaker_label", "unknown"),
                    "start": float(seg.get("start_time", 0)),
                    "end": float(seg.get("end_time", 0)),
                    "text": " ".join(
                        item.get("alternatives", [{}])[0].get("content", "")
                        for item in seg.get("items", [])
                    ),
                })

        with transaction.atomic():
            Transcript.objects.update_or_create(
                encounter=encounter,
                defaults={
                    "raw_text": raw_text,
                    "speaker_segments": speaker_segments,
                    "confidence_score": 0.9,
                    "language_detected": "en",
                },
            )
            recording.transcription_status = "completed"
            recording.save(update_fields=["transcription_status"])
            encounter.status = Encounter.Status.GENERATING_NOTE
            encounter.save(update_fields=["status", "updated_at"])

        # Chain to SOAP note generation
        from workers.soap_note import generate_soap_note_task
        generate_soap_note_task.delay(encounter_id)

        _send_ws_update(encounter_id, "generating_note")

    except Exception as exc:
        logger.error(f"Transcription task failed for {encounter_id}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        Encounter.objects.filter(id=encounter_id).update(status="transcription_failed")
        Recording.objects.filter(encounter_id=encounter_id).update(transcription_status="failed")
        _send_ws_update(encounter_id, "transcription_failed")


def _send_ws_update(encounter_id: str, status: str):
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"encounter_{encounter_id}",
            {"type": "job_status_update", "status": status, "encounter_id": encounter_id},
        )
    except Exception as e:
        logger.warning(f"WebSocket update failed for {encounter_id}: {e}")
```

### Task 6.2: SOAP note worker

- [ ] **Step 1 (3 min):** Write failing tests.

File: `backend/workers/tests/test_soap_note.py`
```python
from datetime import date
from unittest.mock import MagicMock, patch
from django.test import TestCase
from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter, Transcript
from apps.notes.models import PromptVersion
from apps.patients.models import Patient


class SOAPNoteTaskTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D", date_of_birth="1990-01-01"
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor, patient=self.patient,
            encounter_date=date.today(), input_method="paste", status="generating_note",
        )
        self.transcript = Transcript.objects.create(
            encounter=self.encounter, raw_text="Patient has headache for 3 days.",
            confidence_score=1.0,
        )
        self.prompt = PromptVersion.objects.create(
            prompt_name="soap_note", version="1.0.0",
            template_text="prompt", is_active=True,
        )

    @patch("workers.soap_note.LLMService")
    @patch("workers.soap_note.generate_summary_task")
    def test_soap_note_success(self, mock_summary_task, mock_llm_cls):
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        mock_llm.generate_soap_note.return_value = {
            "subjective": "Headache x3 days",
            "objective": "Alert, oriented",
            "assessment": "Tension headache",
            "plan": "Ibuprofen PRN",
            "icd10_codes": ["R51.9"],
            "cpt_codes": ["99214"],
        }

        from workers.soap_note import generate_soap_note_task
        generate_soap_note_task(str(self.encounter.id))

        self.encounter.refresh_from_db()
        assert self.encounter.status == "generating_summary"
        assert hasattr(self.encounter, "clinical_note")
        assert self.encounter.clinical_note.subjective == "Headache x3 days"
        mock_summary_task.delay.assert_called_once_with(str(self.encounter.id))
```

- [ ] **Step 2 (3 min):** Implement SOAP note worker.

File: `backend/workers/soap_note.py`
```python
import logging

from celery import shared_task
from django.db import transaction

from apps.encounters.models import Encounter, Transcript
from apps.notes.models import ClinicalNote, PromptVersion
from services.llm_service import LLMService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    retry_backoff=True,
    retry_backoff_max=45,
    time_limit=120,
    name="workers.soap_note.generate_soap_note_task",
)
def generate_soap_note_task(self, encounter_id: str):
    try:
        encounter = Encounter.objects.get(id=encounter_id)
        transcript = Transcript.objects.get(encounter=encounter)
    except (Encounter.DoesNotExist, Transcript.DoesNotExist) as e:
        logger.error(f"Encounter or transcript not found: {encounter_id}")
        return

    try:
        prompt_version = PromptVersion.objects.filter(
            prompt_name="soap_note", is_active=True
        ).first()
        version_str = prompt_version.version if prompt_version else "1.0.0"

        llm = LLMService()
        result = llm.generate_soap_note(transcript.raw_text, version_str)

        with transaction.atomic():
            ClinicalNote.objects.update_or_create(
                encounter=encounter,
                defaults={
                    "note_type": "soap",
                    "subjective": result["subjective"],
                    "objective": result["objective"],
                    "assessment": result["assessment"],
                    "plan": result["plan"],
                    "icd10_codes": result.get("icd10_codes", []),
                    "cpt_codes": result.get("cpt_codes", []),
                    "ai_generated": True,
                    "doctor_edited": False,
                    "prompt_version": prompt_version,
                },
            )
            encounter.status = Encounter.Status.GENERATING_SUMMARY
            encounter.save(update_fields=["status", "updated_at"])

        from workers.summary import generate_summary_task
        generate_summary_task.delay(encounter_id)

        _send_ws_update(encounter_id, "generating_summary")

    except ValueError as exc:
        logger.warning(f"LLM output validation failed for {encounter_id}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        Encounter.objects.filter(id=encounter_id).update(status="note_generation_failed")
        _send_ws_update(encounter_id, "note_generation_failed")
    except Exception as exc:
        logger.error(f"SOAP note task failed for {encounter_id}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        Encounter.objects.filter(id=encounter_id).update(status="note_generation_failed")
        _send_ws_update(encounter_id, "note_generation_failed")


def _send_ws_update(encounter_id: str, status: str):
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"encounter_{encounter_id}",
            {"type": "job_status_update", "status": status, "encounter_id": encounter_id},
        )
    except Exception as e:
        logger.warning(f"WebSocket update failed: {e}")
```

### Task 6.3: Summary worker

- [ ] **Step 1 (3 min):** Write failing test.

File: `backend/workers/tests/test_summary.py`
```python
from datetime import date
from unittest.mock import MagicMock, patch
from django.test import TestCase
from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote, PromptVersion
from apps.patients.models import Patient
from apps.summaries.models import PatientSummary


class SummaryTaskTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D", date_of_birth="1990-01-01"
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor, patient=self.patient,
            encounter_date=date.today(), input_method="paste", status="generating_summary",
        )
        self.pv = PromptVersion.objects.create(
            prompt_name="patient_summary", version="1.0.0", template_text="t", is_active=True,
        )
        self.note = ClinicalNote.objects.create(
            encounter=self.encounter, note_type="soap",
            subjective="S", objective="O", assessment="A", plan="P",
            ai_generated=True, prompt_version=self.pv,
        )

    @patch("workers.summary.LLMService")
    def test_summary_success(self, mock_llm_cls):
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        mock_llm.generate_patient_summary.return_value = {
            "summary_en": "You visited the doctor today.",
            "summary_es": "Visitaste al doctor hoy.",
            "medical_terms_explained": [{"term": "headache", "explanation": "pain in head"}],
        }

        from workers.summary import generate_summary_task
        generate_summary_task(str(self.encounter.id))

        self.encounter.refresh_from_db()
        assert self.encounter.status == "ready_for_review"
        summary = PatientSummary.objects.get(encounter=self.encounter)
        assert "visited" in summary.summary_en
```

- [ ] **Step 2 (3 min):** Implement summary worker.

File: `backend/workers/summary.py`
```python
import logging

from celery import shared_task
from django.db import transaction

from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote, PromptVersion
from apps.summaries.models import PatientSummary
from services.llm_service import LLMService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    retry_backoff=True,
    retry_backoff_max=45,
    time_limit=120,
    name="workers.summary.generate_summary_task",
)
def generate_summary_task(self, encounter_id: str):
    try:
        encounter = Encounter.objects.get(id=encounter_id)
        note = ClinicalNote.objects.get(encounter=encounter)
    except (Encounter.DoesNotExist, ClinicalNote.DoesNotExist):
        logger.error(f"Encounter or note not found: {encounter_id}")
        return

    try:
        prompt_version = PromptVersion.objects.filter(
            prompt_name="patient_summary", is_active=True
        ).first()

        patient = encounter.patient
        reading_level = "grade_8"
        language = patient.language_preference if patient else "en"

        llm = LLMService()
        result = llm.generate_patient_summary(
            subjective=note.subjective,
            objective=note.objective,
            assessment=note.assessment,
            plan=note.plan,
            reading_level=reading_level,
            language=language,
        )

        with transaction.atomic():
            PatientSummary.objects.update_or_create(
                encounter=encounter,
                defaults={
                    "clinical_note": note,
                    "summary_en": result["summary_en"],
                    "summary_es": result.get("summary_es", ""),
                    "reading_level": reading_level,
                    "medical_terms_explained": result.get("medical_terms_explained", []),
                    "delivery_status": "pending",
                    "prompt_version": prompt_version,
                },
            )
            encounter.status = Encounter.Status.READY_FOR_REVIEW
            encounter.save(update_fields=["status", "updated_at"])

        _send_ws_update(encounter_id, "ready_for_review")

    except ValueError as exc:
        logger.warning(f"Summary LLM output invalid for {encounter_id}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        Encounter.objects.filter(id=encounter_id).update(status="summary_generation_failed")
        _send_ws_update(encounter_id, "summary_generation_failed")
    except Exception as exc:
        logger.error(f"Summary task failed for {encounter_id}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        Encounter.objects.filter(id=encounter_id).update(status="summary_generation_failed")
        _send_ws_update(encounter_id, "summary_generation_failed")


def _send_ws_update(encounter_id: str, status: str):
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"encounter_{encounter_id}",
            {"type": "job_status_update", "status": status, "encounter_id": encounter_id},
        )
    except Exception as e:
        logger.warning(f"WebSocket update failed: {e}")
```

### Task 6.4: OCR worker

- [ ] **Step 1 (2 min):** Write failing test.

File: `backend/workers/tests/test_ocr.py`
```python
from datetime import date
from unittest.mock import MagicMock, patch
from django.test import TestCase
from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.patients.models import Patient


class OCRTaskTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D", date_of_birth="1990-01-01"
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor, patient=self.patient,
            encounter_date=date.today(), input_method="scan", status="transcribing",
        )

    @patch("workers.ocr.OCRService")
    @patch("workers.ocr.generate_soap_note_task")
    def test_ocr_success(self, mock_soap_task, mock_ocr_cls):
        mock_ocr = MagicMock()
        mock_ocr_cls.return_value = mock_ocr
        mock_ocr.extract_text_from_s3.return_value = "Chief Complaint: Headache\nBP: 120/80"

        from workers.ocr import ocr_task
        ocr_task(str(self.encounter.id), "s3://bucket/scan.jpg")

        self.encounter.refresh_from_db()
        assert self.encounter.status == "generating_note"
        assert hasattr(self.encounter, "transcript")
```

- [ ] **Step 2 (3 min):** Implement OCR worker.

File: `backend/workers/ocr.py`
```python
import logging

from celery import shared_task
from django.db import transaction

from apps.encounters.models import Encounter, Transcript
from services.ocr_service import OCRService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    retry_backoff=True,
    retry_backoff_max=45,
    time_limit=120,
    name="workers.ocr.ocr_task",
)
def ocr_task(self, encounter_id: str, s3_uri: str):
    try:
        encounter = Encounter.objects.get(id=encounter_id)
    except Encounter.DoesNotExist:
        logger.error(f"Encounter not found: {encounter_id}")
        return

    try:
        ocr_service = OCRService()
        extracted_text = ocr_service.extract_text_from_s3(s3_uri)

        if not extracted_text.strip():
            raise ValueError("OCR extracted no text from image.")

        with transaction.atomic():
            Transcript.objects.update_or_create(
                encounter=encounter,
                defaults={
                    "raw_text": extracted_text,
                    "speaker_segments": [],
                    "confidence_score": 0.85,
                    "language_detected": "en",
                },
            )
            encounter.status = Encounter.Status.GENERATING_NOTE
            encounter.save(update_fields=["status", "updated_at"])

        from workers.soap_note import generate_soap_note_task
        generate_soap_note_task.delay(encounter_id)

        _send_ws_update(encounter_id, "generating_note")

    except Exception as exc:
        logger.error(f"OCR task failed for {encounter_id}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        Encounter.objects.filter(id=encounter_id).update(status="transcription_failed")
        _send_ws_update(encounter_id, "transcription_failed")


def _send_ws_update(encounter_id: str, status: str):
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"encounter_{encounter_id}",
            {"type": "job_status_update", "status": status, "encounter_id": encounter_id},
        )
    except Exception as e:
        logger.warning(f"WebSocket update failed: {e}")
```

Run: `cd backend && python -m pytest workers/tests/ -v`
Verify: All worker tests pass.

---

## Chunk 7: HIPAA Audit Middleware, WebSocket, and Prompt Templates

### Task 7.1: HIPAA audit middleware

- [ ] **Step 1 (3 min):** Write failing tests.

File: `backend/apps/audit/tests/test_middleware.py`
```python
from datetime import date
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import Practice, User
from apps.audit.models import AuditLog
from apps.patients.models import Patient


class HIPAAAuditMiddlewareTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D", date_of_birth="1990-01-01"
        )
        self.client.force_authenticate(user=self.doctor)

    def test_phi_access_logged_on_patient_view(self):
        response = self.client.get(f"/api/v1/patients/{self.patient.id}/")
        assert response.status_code == 200
        logs = AuditLog.objects.filter(
            user=self.doctor, resource_type="patient", action="view"
        )
        assert logs.count() >= 1

    def test_phi_access_logged_on_patient_create(self):
        response = self.client.post(
            "/api/v1/patients/",
            {"first_name": "New", "last_name": "Patient", "date_of_birth": "1995-01-01"},
            format="json",
        )
        assert response.status_code == 201
        logs = AuditLog.objects.filter(
            user=self.doctor, resource_type="patient", action="create"
        )
        assert logs.count() >= 1

    def test_no_log_for_non_phi_endpoints(self):
        initial_count = AuditLog.objects.count()
        self.client.get("/admin/")  # Non-PHI endpoint
        # Middleware should not log admin panel
        assert AuditLog.objects.count() == initial_count
```

- [ ] **Step 2 (4 min):** Implement HIPAA audit middleware.

File: `backend/apps/audit/middleware.py`
```python
import logging
import re
import uuid

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

PHI_URL_PATTERNS = [
    (re.compile(r"^/api/v1/patients/(?P<id>[0-9a-f-]+)/?$"), "patient", "view"),
    (re.compile(r"^/api/v1/patients/?$"), "patient", None),
    (re.compile(r"^/api/v1/encounters/(?P<id>[0-9a-f-]+)/?$"), "encounter", "view"),
    (re.compile(r"^/api/v1/encounters/?$"), "encounter", None),
    (re.compile(r"^/api/v1/encounters/[0-9a-f-]+/note/?$"), "note", None),
    (re.compile(r"^/api/v1/encounters/[0-9a-f-]+/summary/?$"), "summary", None),
    (re.compile(r"^/api/v1/encounters/[0-9a-f-]+/transcript/?$"), "recording", "view"),
    (re.compile(r"^/api/v1/encounters/[0-9a-f-]+/recording/?$"), "recording", None),
    (re.compile(r"^/api/v1/patient/summaries/?"), "summary", None),
]

METHOD_TO_ACTION = {
    "GET": "view",
    "POST": "create",
    "PUT": "update",
    "PATCH": "update",
    "DELETE": "delete",
}


class HIPAAAuditMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return response

        if response.status_code >= 400:
            return response

        path = request.path
        matched_resource = None
        resource_id = None

        for pattern, resource_type, forced_action in PHI_URL_PATTERNS:
            match = pattern.match(path)
            if match:
                matched_resource = resource_type
                groups = match.groupdict()
                if "id" in groups:
                    resource_id = groups["id"]
                break

        if matched_resource is None:
            return response

        action = METHOD_TO_ACTION.get(request.method, "view")

        try:
            from apps.audit.models import AuditLog

            AuditLog.objects.create(
                user=request.user,
                action=action,
                resource_type=matched_resource,
                resource_id=uuid.UUID(resource_id) if resource_id else uuid.uuid4(),
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                phi_accessed=True,
                details={"path": path, "method": request.method, "status_code": response.status_code},
            )
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")

        return response

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "0.0.0.0")
```

Run: `cd backend && python -m pytest apps/audit/tests/test_middleware.py -v`
Verify: All tests pass.

### Task 7.2: WebSocket consumer (Django Channels)

- [ ] **Step 1 (3 min):** Write failing tests.

File: `backend/apps/realtime/tests/__init__.py`
```python
```

File: `backend/apps/realtime/tests/test_consumers.py`
```python
import json
from unittest.mock import MagicMock, patch
from channels.testing import WebsocketCommunicator
from django.test import TestCase
from apps.realtime.consumers import JobStatusConsumer


class JobStatusConsumerTest(TestCase):
    async def test_connect_and_receive_status(self):
        communicator = WebsocketCommunicator(
            JobStatusConsumer.as_asgi(),
            "/api/v1/ws/jobs/test-encounter-id/",
        )
        communicator.scope["url_route"] = {
            "kwargs": {"encounter_id": "test-encounter-id"}
        }
        communicator.scope["user"] = MagicMock(is_authenticated=True, id="user-1")

        connected, _ = await communicator.connect()
        assert connected

        # Simulate sending a status update from the channel layer
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            "encounter_test-encounter-id",
            {
                "type": "job_status_update",
                "status": "generating_note",
                "encounter_id": "test-encounter-id",
            },
        )

        response = await communicator.receive_json_from()
        assert response["status"] == "generating_note"

        await communicator.disconnect()
```

- [ ] **Step 2 (3 min):** Implement WebSocket consumer, routing, and auth middleware.

File: `backend/apps/realtime/consumers.py`
```python
import json
import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger(__name__)


class JobStatusConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.encounter_id = self.scope["url_route"]["kwargs"]["encounter_id"]
        self.group_name = f"encounter_{self.encounter_id}"

        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def job_status_update(self, event):
        await self.send_json({
            "type": "status_update",
            "status": event["status"],
            "encounter_id": event["encounter_id"],
        })
```

File: `backend/apps/realtime/routing.py`
```python
from django.urls import re_path
from apps.realtime.consumers import JobStatusConsumer

websocket_urlpatterns = [
    re_path(
        r"api/v1/ws/jobs/(?P<encounter_id>[0-9a-f-]+)/$",
        JobStatusConsumer.as_asgi(),
    ),
]
```

File: `backend/apps/realtime/middleware.py`
```python
import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger(__name__)


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        token = params.get("token", [None])[0]

        if token:
            scope["user"] = await self._get_user_from_token(token)
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def _get_user_from_token(self, raw_token):
        try:
            from apps.accounts.models import User

            access_token = AccessToken(raw_token)
            user_id = access_token["user_id"]
            return User.objects.get(id=user_id)
        except Exception as e:
            logger.warning(f"WebSocket JWT auth failed: {e}")
            return AnonymousUser()
```

### Task 7.3: Prompt templates

- [ ] **Step 1 (2 min):** Create prompt template files and a data migration to seed initial prompt versions.

File: `backend/prompts/__init__.py`
```python
```

File: `backend/prompts/soap_note.py`
```python
SOAP_NOTE_PROMPT_V1 = """You are a medical documentation assistant specialized in creating structured clinical notes.

Given a transcript of a patient-doctor encounter (or raw clinical text), produce a structured SOAP note.

Guidelines:
- Subjective: Patient's chief complaint, history of present illness, symptoms in their own words
- Objective: Physical examination findings, vital signs, lab results
- Assessment: Clinical impression, diagnosis, differential diagnoses
- Plan: Treatment plan, medications, follow-up instructions, referrals

Also extract relevant ICD-10 and CPT codes when identifiable.

Output strict JSON only (no markdown, no explanation):
{
  "subjective": "...",
  "objective": "...",
  "assessment": "...",
  "plan": "...",
  "icd10_codes": ["..."],
  "cpt_codes": ["..."]
}"""
```

File: `backend/prompts/patient_summary.py`
```python
PATIENT_SUMMARY_PROMPT_V1 = """You are a medical communication specialist. Convert the following clinical SOAP note into a patient-friendly visit summary.

Rules:
- Write at a {reading_level} reading level
- Use short sentences and common words
- Explain ALL medical terms in parentheses on first use
- Organize with clear headings: "What We Discussed", "What We Found", "Your Diagnosis", "Next Steps"
- Do NOT include medical advice beyond what the doctor documented
- Be warm and reassuring in tone
- Generate in {language}

If language includes Spanish, provide both English and Spanish versions.

Output strict JSON only:
{{
  "summary_en": "...",
  "summary_es": "...",
  "medical_terms_explained": [{{"term": "...", "explanation": "..."}}]
}}"""
```

File: `backend/prompts/medical_terms.py`
```python
MEDICAL_TERMS_PROMPT_V1 = """Given the following medical text, extract all medical terminology and provide patient-friendly explanations.

Output strict JSON only:
{
  "terms": [
    {"term": "...", "explanation": "..."}
  ]
}"""
```

---

## Chunk 8: Docker and Infrastructure Configuration

### Task 8.1: Dockerfile

- [ ] **Step 1 (3 min):** Create production Dockerfile.

File: `backend/Dockerfile`
```dockerfile
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput --settings=config.settings.production 2>/dev/null || true

EXPOSE 8000

# API server
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
```

### Task 8.2: docker-compose for local development

- [ ] **Step 1 (4 min):** Create docker-compose.yml.

File: `infrastructure/docker-compose.yml`
```yaml
version: "3.9"

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: medicalnote
      POSTGRES_USER: medicalnote
      POSTGRES_PASSWORD: medicalnote
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U medicalnote"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build:
      context: ../backend
      dockerfile: Dockerfile
    command: >
      sh -c "python manage.py migrate &&
             daphne -b 0.0.0.0 -p 8000 config.asgi:application"
    environment:
      DJANGO_SETTINGS_MODULE: config.settings.development
      DB_HOST: db
      DB_PORT: "5432"
      DB_NAME: medicalnote
      DB_USER: medicalnote
      DB_PASSWORD: medicalnote
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/1
      REDIS_URL: redis://redis:6379/2
      FIELD_ENCRYPTION_KEY: "local-dev-encryption-key-32-bytes-pad="
    ports:
      - "8000:8000"
    volumes:
      - ../backend:/app
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  celery-worker:
    build:
      context: ../backend
      dockerfile: Dockerfile
    command: >
      celery -A config worker -l info
      -Q default,transcription,soap_note,summary,ocr
      --concurrency=2
    environment:
      DJANGO_SETTINGS_MODULE: config.settings.development
      DB_HOST: db
      DB_PORT: "5432"
      DB_NAME: medicalnote
      DB_USER: medicalnote
      DB_PASSWORD: medicalnote
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/1
      REDIS_URL: redis://redis:6379/2
      FIELD_ENCRYPTION_KEY: "local-dev-encryption-key-32-bytes-pad="
    volumes:
      - ../backend:/app
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  celery-beat:
    build:
      context: ../backend
      dockerfile: Dockerfile
    command: celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    environment:
      DJANGO_SETTINGS_MODULE: config.settings.development
      DB_HOST: db
      DB_PORT: "5432"
      DB_NAME: medicalnote
      DB_USER: medicalnote
      DB_PASSWORD: medicalnote
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/1
      FIELD_ENCRYPTION_KEY: "local-dev-encryption-key-32-bytes-pad="
    volumes:
      - ../backend:/app
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

volumes:
  postgres_data:
```

### Task 8.3: Environment template and .gitignore

- [ ] **Step 1 (2 min):** Create `.env.example`.

File: `backend/.env.example`
```bash
DJANGO_SETTINGS_MODULE=config.settings.development
DJANGO_SECRET_KEY=change-me-to-a-random-string
DB_NAME=medicalnote
DB_USER=medicalnote
DB_PASSWORD=medicalnote
DB_HOST=localhost
DB_PORT=5432
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
REDIS_URL=redis://localhost:6379/2
FIELD_ENCRYPTION_KEY=change-me-to-a-32-byte-base64-key=
AWS_REGION=us-east-1
AWS_S3_BUCKET=medicalnote-hipaa-dev
AWS_KMS_KEY_ID=
ANTHROPIC_API_KEY=
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

- [ ] **Step 2 (1 min):** Create `.gitignore` for backend.

File: `backend/.gitignore`
```
__pycache__/
*.py[cod]
*.so
.venv/
*.egg-info/
dist/
build/
.env
.env.local
*.sqlite3
staticfiles/
media/
.pytest_cache/
.coverage
htmlcov/
```

### Task 8.4: Final integration test

- [ ] **Step 1 (3 min):** Write a full pipeline integration test.

File: `backend/tests/__init__.py`
```python
```

File: `backend/tests/test_integration.py`
```python
from datetime import date
from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote, PromptVersion
from apps.patients.models import Patient
from apps.summaries.models import PatientSummary


class FullPasteFlowIntegrationTest(TestCase):
    """End-to-end test: doctor creates encounter, pastes text, pipeline runs, review, approve, deliver."""

    def setUp(self):
        self.client = APIClient()
        self.practice = Practice.objects.create(name="Test Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@integration.test", password="SecurePass123!",
            role="doctor", first_name="Jane", last_name="Smith",
            practice=self.practice,
        )
        PromptVersion.objects.create(
            prompt_name="soap_note", version="1.0.0", template_text="p", is_active=True
        )
        PromptVersion.objects.create(
            prompt_name="patient_summary", version="1.0.0", template_text="p", is_active=True
        )
        self.client.force_authenticate(user=self.doctor)

    @patch("workers.summary.LLMService")
    @patch("workers.soap_note.LLMService")
    def test_paste_flow_end_to_end(self, mock_soap_llm_cls, mock_summary_llm_cls):
        # Mock LLM responses
        mock_soap_llm = MagicMock()
        mock_soap_llm_cls.return_value = mock_soap_llm
        mock_soap_llm.generate_soap_note.return_value = {
            "subjective": "Patient reports headache x3 days",
            "objective": "BP 120/80, alert and oriented",
            "assessment": "Tension headache",
            "plan": "Ibuprofen 400mg PRN, follow up 2 weeks",
            "icd10_codes": ["R51.9"],
            "cpt_codes": ["99214"],
        }

        mock_summary_llm = MagicMock()
        mock_summary_llm_cls.return_value = mock_summary_llm
        mock_summary_llm.generate_patient_summary.return_value = {
            "summary_en": "You visited Dr. Smith today for a headache.",
            "summary_es": "Visitaste al Dr. Smith hoy por dolor de cabeza.",
            "medical_terms_explained": [
                {"term": "tension headache", "explanation": "a common headache caused by stress"}
            ],
        }

        # 1. Create patient
        resp = self.client.post("/api/v1/patients/", {
            "first_name": "John", "last_name": "Doe",
            "date_of_birth": "1990-01-15", "phone": "+15551234567",
        }, format="json")
        assert resp.status_code == 201
        patient_id = resp.data["id"]

        # 2. Create encounter
        resp = self.client.post("/api/v1/encounters/", {
            "patient": patient_id,
            "encounter_date": "2026-03-15",
            "input_method": "paste",
        }, format="json")
        assert resp.status_code == 201
        encounter_id = resp.data["id"]

        # 3. Paste text (triggers SOAP note + summary workers synchronously in test mode)
        resp = self.client.post(
            f"/api/v1/encounters/{encounter_id}/paste/",
            {"text": "Patient presents with tension headache for 3 days. No fever. BP 120/80."},
            format="json",
        )
        assert resp.status_code == 202

        # 4. Verify note was generated
        encounter = Encounter.objects.get(id=encounter_id)
        assert encounter.status == "ready_for_review"
        note = ClinicalNote.objects.get(encounter=encounter)
        assert note.subjective == "Patient reports headache x3 days"
        assert note.ai_generated is True

        # 5. Verify summary was generated
        summary = PatientSummary.objects.get(encounter=encounter)
        assert "Dr. Smith" in summary.summary_en

        # 6. Doctor reviews and approves note
        resp = self.client.post(f"/api/v1/encounters/{encounter_id}/note/approve/")
        assert resp.status_code == 200
        encounter.refresh_from_db()
        assert encounter.status == "approved"

        # 7. Doctor sends summary
        resp = self.client.post(
            f"/api/v1/encounters/{encounter_id}/summary/send/",
            {"delivery_method": "app"},
            format="json",
        )
        assert resp.status_code == 200
        encounter.refresh_from_db()
        assert encounter.status == "delivered"
        summary.refresh_from_db()
        assert summary.delivery_status == "sent"
```

- [ ] **Step 2 (2 min):** Run full test suite.

```bash
cd backend && python -m pytest --tb=short -v
```

Verify: All tests pass across all apps, workers, services, and integration.

---

## Summary of File Inventory

All files to create (61 files total):

**Config (9):** `config/settings/__init__.py`, `config/settings/base.py`, `config/settings/development.py`, `config/settings/production.py`, `config/settings/test.py`, `config/__init__.py`, `config/celery.py`, `config/asgi.py`, `config/urls.py`

**Accounts app (9):** `apps/__init__.py`, `apps/accounts/__init__.py`, `apps/accounts/apps.py`, `apps/accounts/models.py`, `apps/accounts/serializers.py`, `apps/accounts/adapters.py`, `apps/accounts/permissions.py`, `apps/accounts/views.py`, `apps/accounts/urls.py`, `apps/accounts/practice_urls.py`, `apps/accounts/practice_views.py`, `apps/accounts/admin.py`

**Patients app (6):** `apps/patients/__init__.py`, `apps/patients/apps.py`, `apps/patients/models.py`, `apps/patients/serializers.py`, `apps/patients/views.py`, `apps/patients/urls.py`, `apps/patients/filters.py`, `apps/patients/admin.py`

**Encounters app (6):** `apps/encounters/__init__.py`, `apps/encounters/apps.py`, `apps/encounters/models.py`, `apps/encounters/serializers.py`, `apps/encounters/views.py`, `apps/encounters/urls.py`, `apps/encounters/filters.py`, `apps/encounters/admin.py`

**Notes app (5):** `apps/notes/__init__.py`, `apps/notes/apps.py`, `apps/notes/models.py`, `apps/notes/serializers.py`, `apps/notes/views.py`, `apps/notes/urls.py`, `apps/notes/admin.py`

**Summaries app (6):** `apps/summaries/__init__.py`, `apps/summaries/apps.py`, `apps/summaries/models.py`, `apps/summaries/serializers.py`, `apps/summaries/views.py`, `apps/summaries/urls.py`, `apps/summaries/patient_views.py`, `apps/summaries/patient_urls.py`, `apps/summaries/admin.py`

**Widget app (4):** `apps/widget/__init__.py`, `apps/widget/apps.py`, `apps/widget/models.py`, `apps/widget/serializers.py`, `apps/widget/views.py`, `apps/widget/urls.py`

**Audit app (4):** `apps/audit/__init__.py`, `apps/audit/apps.py`, `apps/audit/models.py`, `apps/audit/middleware.py`, `apps/audit/admin.py`

**Realtime app (4):** `apps/realtime/__init__.py`, `apps/realtime/apps.py`, `apps/realtime/consumers.py`, `apps/realtime/routing.py`, `apps/realtime/middleware.py`

**Workers (5):** `workers/__init__.py`, `workers/transcription.py`, `workers/soap_note.py`, `workers/summary.py`, `workers/ocr.py`

**Services (6):** `services/__init__.py`, `services/llm_service.py`, `services/stt_service.py`, `services/ocr_service.py`, `services/storage_service.py`, `services/notification_service.py`

**Prompts (4):** `prompts/__init__.py`, `prompts/soap_note.py`, `prompts/patient_summary.py`, `prompts/medical_terms.py`

**Infra (4):** `backend/Dockerfile`, `infrastructure/docker-compose.yml`, `backend/.env.example`, `backend/.gitignore`, `backend/pyproject.toml`, `backend/requirements.txt`

**Tests (14):** One `__init__.py` and test file per app/service/worker module.

---
