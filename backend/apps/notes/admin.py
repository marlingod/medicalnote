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
