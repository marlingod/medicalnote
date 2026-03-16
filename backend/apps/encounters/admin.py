from django.contrib import admin

from apps.encounters.models import Encounter, Recording, Transcript


@admin.register(Encounter)
class EncounterAdmin(admin.ModelAdmin):
    list_display = ("id", "doctor", "patient", "encounter_date", "status", "input_method")
    list_filter = ("status", "input_method", "encounter_date")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Recording)
class RecordingAdmin(admin.ModelAdmin):
    list_display = ("id", "encounter", "format", "transcription_status", "duration_seconds")
    list_filter = ("format", "transcription_status")


@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ("id", "encounter", "language_detected", "confidence_score")
    readonly_fields = ("id", "created_at", "updated_at")
