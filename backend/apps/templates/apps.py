from django.apps import AppConfig


class TemplatesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.templates"
    verbose_name = "Templates"
    label = "note_templates"  # Avoid conflict with Django's built-in "templates"
