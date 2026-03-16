from django.contrib import admin

from apps.fhir.models import FHIRConnection, FHIRPushLog


@admin.register(FHIRConnection)
class FHIRConnectionAdmin(admin.ModelAdmin):
    list_display = [
        "display_name",
        "ehr_system",
        "practice",
        "is_active",
        "connection_status",
        "last_connected_at",
    ]
    list_filter = ["ehr_system", "is_active", "connection_status"]
    readonly_fields = [
        "access_token",
        "refresh_token",
        "token_expires_at",
        "last_connected_at",
    ]


@admin.register(FHIRPushLog)
class FHIRPushLogAdmin(admin.ModelAdmin):
    list_display = [
        "encounter",
        "resource_type",
        "status",
        "response_code",
        "fhir_resource_id",
        "created_at",
    ]
    list_filter = ["status", "resource_type"]
    readonly_fields = [
        "connection",
        "encounter",
        "clinical_note",
        "response_body",
        "error_message",
    ]
