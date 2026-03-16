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
