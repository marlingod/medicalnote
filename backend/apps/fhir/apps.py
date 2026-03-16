from django.apps import AppConfig


class FHIRConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.fhir"
    verbose_name = "FHIR Integration"
