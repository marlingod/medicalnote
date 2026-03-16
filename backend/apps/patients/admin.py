from django.contrib import admin

from apps.patients.models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("id", "practice", "language_preference", "created_at")
    list_filter = ("practice", "language_preference")
    # Do not display encrypted fields in list view
    readonly_fields = ("name_search_hash",)
