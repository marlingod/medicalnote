from django.contrib import admin
from .models import BusinessAssociateAgreement, BreachIncident


@admin.register(BusinessAssociateAgreement)
class BAAAdmin(admin.ModelAdmin):
    list_display = ["vendor_name", "vendor_type", "status", "effective_date", "expiration_date"]
    list_filter = ["status", "vendor_type"]
    search_fields = ["vendor_name"]


@admin.register(BreachIncident)
class BreachIncidentAdmin(admin.ModelAdmin):
    list_display = ["title", "severity", "status", "detected_at", "notification_deadline"]
    list_filter = ["status", "severity"]
    search_fields = ["title"]
