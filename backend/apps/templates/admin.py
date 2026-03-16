from django.contrib import admin
from apps.templates.models import NoteTemplate, TemplateRating, TemplateFavorite


@admin.register(NoteTemplate)
class NoteTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "specialty", "note_type", "visibility", "status", "use_count", "created_by")
    list_filter = ("specialty", "note_type", "visibility", "status")
    search_fields = ("name", "description")
    readonly_fields = ("id", "use_count", "clone_count", "created_at", "updated_at")


@admin.register(TemplateRating)
class TemplateRatingAdmin(admin.ModelAdmin):
    list_display = ("template", "user", "score", "created_at")
    list_filter = ("score",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(TemplateFavorite)
class TemplateFavoriteAdmin(admin.ModelAdmin):
    list_display = ("template", "user", "created_at")
    readonly_fields = ("id", "created_at")
