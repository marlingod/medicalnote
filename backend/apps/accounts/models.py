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

    class LLMProviderChoice(models.TextChoices):
        CLAUDE = "claude", "Claude Only"
        GEMINI = "gemini", "Gemini Only (Most Affordable)"
        CLAUDE_GEMINI = "claude+gemini", "Claude + Gemini (Best Value)"

    llm_provider = models.CharField(
        max_length=20,
        choices=LLMProviderChoice.choices,
        default=LLMProviderChoice.CLAUDE,
        help_text="AI model provider for note generation and summaries",
    )

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


class DeviceToken(models.Model):
    class Platform(models.TextChoices):
        IOS = "ios", "iOS"
        ANDROID = "android", "Android"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="device_tokens",
    )
    token = models.CharField(max_length=500, unique=True)
    platform = models.CharField(max_length=10, choices=Platform.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "device_tokens"
        ordering = ["-created_at"]

    def __str__(self):
        return f"DeviceToken({self.platform}) for {self.user.email}"


class PasswordHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_history",
    )
    password_hash = models.CharField(max_length=256)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "password_history"
        ordering = ["-created_at"]

    def __str__(self):
        return f"PasswordHistory for {self.user_id} at {self.created_at}"
