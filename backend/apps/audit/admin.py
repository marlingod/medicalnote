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
