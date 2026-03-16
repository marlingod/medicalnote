from django.contrib import admin

from apps.summaries.models import PatientSummary


@admin.register(PatientSummary)
class PatientSummaryAdmin(admin.ModelAdmin):
    list_display = ("id", "encounter", "reading_level", "delivery_status", "delivered_at")
    list_filter = ("reading_level", "delivery_status", "delivery_method")
    readonly_fields = ("id", "created_at", "updated_at")
