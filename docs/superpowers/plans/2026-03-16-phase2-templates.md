# Phase 2: Specialty Templates + Marketplace Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development to implement this plan.

**Goal:** Add specialty-specific smart templates with AI auto-completion and a template marketplace to the MedicalNote platform, plus a quality checker worker that scores clinical notes against CMS E/M documentation requirements.

**Architecture:** Phase 2 extends the Phase 1 modular monolith by adding two new Django apps (`apps/templates/` and `apps/quality/`), one new Celery worker (`workers/quality_checker.py`), new LLM service methods for template auto-completion, and new Next.js pages/components for template browsing, editing, and marketplace. The template engine uses JSONField to store flexible template schemas (sections, fields, conditional logic) and integrates with the existing encounter pipeline so doctors can select a template before or during note generation.

**Tech Stack:** Django 5.x models with JSONField for template schemas, DRF ViewSets with django-filter for marketplace search, Celery worker for async quality scoring, Claude API for AI template auto-completion, AWS Comprehend Medical for medical entity extraction in quality checks, Next.js App Router pages with shadcn/ui components for the marketplace UI, TanStack Query hooks for data fetching.

---

## Table of Contents

1. [Data Model](#1-data-model)
2. [Backend: `apps/templates/` App](#2-backend-appstemplates-app)
3. [Backend: `apps/quality/` App](#3-backend-appsquality-app)
4. [Workers: Quality Checker](#4-workers-quality-checker)
5. [Services: Template LLM Service](#5-services-template-llm-service)
6. [API Endpoints](#6-api-endpoints)
7. [Web Dashboard: Templates Section](#7-web-dashboard-templates-section)
8. [Web Dashboard: Quality Score Integration](#8-web-dashboard-quality-score-integration)
9. [Configuration & Settings Updates](#9-configuration--settings-updates)
10. [Implementation Steps (Ordered)](#10-implementation-steps-ordered)

---

## 1. Data Model

### 1.1 Template Model (`apps/templates/models.py`)

```python
import uuid
from django.db import models


class MedicalSpecialty(models.TextChoices):
    PRIMARY_CARE = "primary_care", "Primary Care"
    DERMATOLOGY = "dermatology", "Dermatology"
    PSYCHIATRY = "psychiatry", "Psychiatry"
    CARDIOLOGY = "cardiology", "Cardiology"
    ORTHOPEDICS = "orthopedics", "Orthopedics"
    PEDIATRICS = "pediatrics", "Pediatrics"
    NEUROLOGY = "neurology", "Neurology"
    GASTROENTEROLOGY = "gastroenterology", "Gastroenterology"
    GENERAL = "general", "General"


class NoteTemplate(models.Model):
    """A clinical note template with structured sections and specialty-specific fields."""

    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        PRACTICE = "practice", "Practice"
        PUBLIC = "public", "Public (Marketplace)"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    specialty = models.CharField(
        max_length=30, choices=MedicalSpecialty.choices, default=MedicalSpecialty.GENERAL
    )
    note_type = models.CharField(
        max_length=20,
        choices=[("soap", "SOAP"), ("free_text", "Free Text"), ("h_and_p", "H&P")],
        default="soap",
    )

    # Template schema: sections, fields, conditional logic, default values
    # Example structure:
    # {
    #   "sections": [
    #     {
    #       "key": "subjective",
    #       "label": "Subjective",
    #       "fields": [
    #         {"key": "chief_complaint", "label": "Chief Complaint", "type": "text", "required": true},
    #         {"key": "hpi", "label": "HPI", "type": "textarea", "required": true,
    #          "ai_prompt": "Generate HPI based on chief complaint"},
    #         {"key": "ros", "label": "Review of Systems", "type": "checklist",
    #          "options": ["Constitutional", "HEENT", "Cardiovascular", ...],
    #          "conditional": {"show_if": {"specialty": "primary_care"}}},
    #       ],
    #       "default_content": ""
    #     },
    #     ...
    #   ],
    #   "conditional_logic": [
    #     {"if": {"field": "chief_complaint", "contains": "skin"}, "then": {"show_section": "dermatology_exam"}}
    #   ],
    #   "ai_instructions": "Focus on dermatological terminology and skin lesion descriptions"
    # }
    schema = models.JSONField(default=dict)

    # Ownership and visibility
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="created_templates"
    )
    practice = models.ForeignKey(
        "accounts.Practice", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="templates"
    )
    visibility = models.CharField(
        max_length=10, choices=Visibility.choices, default=Visibility.PRIVATE
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT
    )

    # Version control
    version = models.PositiveIntegerField(default=1)
    parent_template = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="derived_templates"
    )

    # Marketplace metadata
    tags = models.JSONField(default=list, blank=True)  # ["follow-up", "initial-visit", "annual-physical"]
    use_count = models.PositiveIntegerField(default=0)
    clone_count = models.PositiveIntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "note_templates"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["specialty", "status"]),
            models.Index(fields=["visibility", "status"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.specialty})"


class TemplateRating(models.Model):
    """Doctor ratings for marketplace templates."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        NoteTemplate, on_delete=models.CASCADE, related_name="ratings"
    )
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="template_ratings"
    )
    score = models.PositiveSmallIntegerField()  # 1-5
    review = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "template_ratings"
        unique_together = [("template", "user")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Rating {self.score}/5 for {self.template.name} by {self.user.email}"


class TemplateFavorite(models.Model):
    """Bookmarked/favorited templates for quick access."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        NoteTemplate, on_delete=models.CASCADE, related_name="favorites"
    )
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="template_favorites"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "template_favorites"
        unique_together = [("template", "user")]
```

### 1.2 Quality Score Model (`apps/quality/models.py`)

```python
import uuid
from django.db import models


class QualityScore(models.Model):
    """Quality score for a clinical note based on CMS E/M documentation requirements."""

    class ScoreLevel(models.TextChoices):
        EXCELLENT = "excellent", "Excellent (90-100%)"
        GOOD = "good", "Good (75-89%)"
        FAIR = "fair", "Fair (50-74%)"
        NEEDS_IMPROVEMENT = "needs_improvement", "Needs Improvement (<50%)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinical_note = models.OneToOneField(
        "notes.ClinicalNote", on_delete=models.CASCADE, related_name="quality_score"
    )
    encounter = models.OneToOneField(
        "encounters.Encounter", on_delete=models.CASCADE, related_name="quality_score"
    )

    # Overall score 0-100
    overall_score = models.FloatField(default=0.0)
    score_level = models.CharField(
        max_length=20, choices=ScoreLevel.choices, default=ScoreLevel.NEEDS_IMPROVEMENT
    )

    # Per-category scores (JSON)
    # {
    #   "history": {"score": 85, "max_score": 100, "items_found": [...], "items_missing": [...]},
    #   "examination": {"score": 70, "max_score": 100, ...},
    #   "medical_decision_making": {"score": 90, "max_score": 100, ...},
    #   "coding_accuracy": {"score": 80, "max_score": 100, ...}
    # }
    category_scores = models.JSONField(default=dict)

    # Detailed findings
    # [
    #   {"category": "history", "element": "HPI", "status": "present", "detail": "Chief complaint documented"},
    #   {"category": "history", "element": "ROS", "status": "missing", "suggestion": "Add review of systems"},
    #   ...
    # ]
    findings = models.JSONField(default=list)

    # Suggestions for improvement
    # ["Add review of systems to subjective section", "Include vital signs in objective", ...]
    suggestions = models.JSONField(default=list)

    # CMS E/M level determination
    em_level_suggested = models.CharField(max_length=10, blank=True, default="")  # e.g., "99214"
    em_level_documented = models.CharField(max_length=10, blank=True, default="")

    # Scoring metadata
    rules_version = models.CharField(max_length=20, default="1.0.0")
    scored_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "quality_scores"

    def __str__(self):
        return f"QualityScore {self.overall_score}% for note {self.clinical_note_id}"
```

### 1.3 Encounter Model Update

The `Encounter` model in `apps/encounters/models.py` needs an optional FK to `NoteTemplate`:

```python
# Add to Encounter model
template_used = models.ForeignKey(
    "templates.NoteTemplate",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="encounters",
)
```

---

## 2. Backend: `apps/templates/` App

### 2.1 File Structure

```
backend/apps/templates/
    __init__.py
    apps.py
    models.py              # NoteTemplate, TemplateRating, TemplateFavorite
    serializers.py          # Full CRUD + marketplace serializers
    views.py                # NoteTemplateViewSet + marketplace actions
    filters.py              # TemplateFilter for specialty, tags, search
    admin.py                # NoteTemplate admin
    urls.py                 # Router registration
    specialty_configs.py    # Pre-built template packs (3 specialties)
    tests/
        __init__.py
        test_models.py
        test_serializers.py
        test_views.py
        test_filters.py
        test_specialty_configs.py
```

### 2.2 `apps/templates/apps.py`

```python
from django.apps import AppConfig


class TemplatesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.templates"
    verbose_name = "Templates"
    label = "note_templates"  # Avoid conflict with Django's built-in "templates"
```

**CRITICAL NOTE:** The Django app label **must** be `note_templates` (not `templates`) because `templates` conflicts with Django's built-in template system. All ForeignKey references should use `"note_templates.NoteTemplate"`, and the `INSTALLED_APPS` entry should be `"apps.templates"` but the app label is `note_templates`.

### 2.3 `apps/templates/serializers.py`

```python
from rest_framework import serializers
from apps.templates.models import NoteTemplate, TemplateRating, TemplateFavorite


class TemplateRatingSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = TemplateRating
        fields = ["id", "template", "user", "user_name", "score", "review", "created_at"]
        read_only_fields = ["id", "user", "user_name", "created_at"]

    def get_user_name(self, obj):
        return f"Dr. {obj.user.last_name}" if obj.user.last_name else obj.user.email

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class NoteTemplateListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    average_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = NoteTemplate
        fields = [
            "id", "name", "description", "specialty", "note_type", "visibility",
            "status", "version", "tags", "use_count", "clone_count",
            "average_rating", "rating_count", "is_favorited", "author_name",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_average_rating(self, obj):
        ratings = obj.ratings.all()
        if not ratings:
            return None
        return round(sum(r.score for r in ratings) / len(ratings), 1)

    def get_rating_count(self, obj):
        return obj.ratings.count()

    def get_is_favorited(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.favorites.filter(user=request.user).exists()

    def get_author_name(self, obj):
        return f"Dr. {obj.created_by.last_name}" if obj.created_by.last_name else obj.created_by.email


class NoteTemplateDetailSerializer(NoteTemplateListSerializer):
    """Full serializer with schema for detail/edit views."""
    ratings = TemplateRatingSerializer(many=True, read_only=True)

    class Meta(NoteTemplateListSerializer.Meta):
        fields = NoteTemplateListSerializer.Meta.fields + ["schema", "ratings"]
        read_only_fields = [
            "id", "use_count", "clone_count", "average_rating",
            "rating_count", "is_favorited", "author_name", "created_at", "updated_at", "ratings",
        ]


class NoteTemplateCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoteTemplate
        fields = [
            "name", "description", "specialty", "note_type", "schema",
            "visibility", "status", "tags",
        ]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        validated_data["practice"] = self.context["request"].user.practice
        return super().create(validated_data)


class TemplateAutoCompleteSerializer(serializers.Serializer):
    """Input for AI auto-completion of template sections."""
    section_key = serializers.CharField()
    field_key = serializers.CharField(required=False, default="")
    encounter_context = serializers.DictField(required=False, default=dict)
    # encounter_context can include: transcript_text, chief_complaint, patient_age, etc.
    partial_content = serializers.CharField(required=False, default="")


class CloneTemplateSerializer(serializers.Serializer):
    """Input for cloning a template."""
    name = serializers.CharField(max_length=255, required=False)
```

### 2.4 `apps/templates/filters.py`

```python
from django_filters import rest_framework as filters
from apps.templates.models import NoteTemplate, MedicalSpecialty


class NoteTemplateFilter(filters.FilterSet):
    specialty = filters.ChoiceFilter(choices=MedicalSpecialty.choices)
    note_type = filters.ChoiceFilter(choices=[("soap", "SOAP"), ("free_text", "Free Text"), ("h_and_p", "H&P")])
    visibility = filters.ChoiceFilter(choices=NoteTemplate.Visibility.choices)
    status = filters.ChoiceFilter(choices=NoteTemplate.Status.choices)
    tag = filters.CharFilter(method="filter_by_tag")
    min_rating = filters.NumberFilter(method="filter_by_min_rating")
    search = filters.CharFilter(method="filter_by_search")

    class Meta:
        model = NoteTemplate
        fields = ["specialty", "note_type", "visibility", "status"]

    def filter_by_tag(self, queryset, name, value):
        return queryset.filter(tags__contains=[value])

    def filter_by_min_rating(self, queryset, name, value):
        # This requires annotation; handled in viewset get_queryset
        return queryset

    def filter_by_search(self, queryset, name, value):
        return queryset.filter(
            models.Q(name__icontains=value) | models.Q(description__icontains=value)
        )
```

### 2.5 `apps/templates/views.py`

```python
from django.db import models
from django.db.models import Avg, Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsDoctorOrAdmin
from apps.templates.models import NoteTemplate, TemplateRating, TemplateFavorite
from apps.templates.serializers import (
    NoteTemplateListSerializer,
    NoteTemplateDetailSerializer,
    NoteTemplateCreateSerializer,
    TemplateRatingSerializer,
    TemplateAutoCompleteSerializer,
    CloneTemplateSerializer,
)
from apps.templates.filters import NoteTemplateFilter


class NoteTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsDoctorOrAdmin]
    filterset_class = NoteTemplateFilter
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at", "updated_at", "use_count", "clone_count"]

    def get_queryset(self):
        user = self.request.user
        qs = NoteTemplate.objects.select_related("created_by", "practice")

        if self.action == "list" and self.request.query_params.get("scope") == "marketplace":
            # Marketplace: show all public + published templates
            qs = qs.filter(visibility="public", status="published")
        elif self.action == "list" and self.request.query_params.get("scope") == "mine":
            # My templates
            qs = qs.filter(created_by=user)
        else:
            # Default: show own templates + practice templates + public published
            qs = qs.filter(
                models.Q(created_by=user)
                | models.Q(practice=user.practice, visibility__in=["practice", "public"])
                | models.Q(visibility="public", status="published")
            )

        # Annotate with average rating
        qs = qs.annotate(
            avg_rating=Avg("ratings__score"),
            rating_count_annotated=Count("ratings"),
        )

        return qs.distinct()

    def get_serializer_class(self):
        if self.action in ("list",):
            return NoteTemplateListSerializer
        if self.action in ("create",):
            return NoteTemplateCreateSerializer
        return NoteTemplateDetailSerializer

    def perform_destroy(self, instance):
        # Only allow deleting own templates
        if instance.created_by != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only delete your own templates.")
        instance.delete()

    @action(detail=True, methods=["post"], url_path="clone")
    def clone_template(self, request, pk=None):
        """Clone a template to the current user's collection."""
        template = self.get_object()
        serializer = CloneTemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cloned = NoteTemplate.objects.create(
            name=serializer.validated_data.get("name", f"{template.name} (Copy)"),
            description=template.description,
            specialty=template.specialty,
            note_type=template.note_type,
            schema=template.schema,
            created_by=request.user,
            practice=request.user.practice,
            visibility="private",
            status="draft",
            version=1,
            parent_template=template,
            tags=template.tags,
        )

        # Increment clone count on original
        NoteTemplate.objects.filter(id=template.id).update(clone_count=models.F("clone_count") + 1)

        result_serializer = NoteTemplateDetailSerializer(cloned, context={"request": request})
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="rate")
    def rate_template(self, request, pk=None):
        """Rate a template (1-5 stars)."""
        template = self.get_object()
        serializer = TemplateRatingSerializer(data={**request.data, "template": template.id}, context={"request": request})
        serializer.is_valid(raise_exception=True)

        rating, created = TemplateRating.objects.update_or_create(
            template=template,
            user=request.user,
            defaults={
                "score": serializer.validated_data["score"],
                "review": serializer.validated_data.get("review", ""),
            },
        )

        result = TemplateRatingSerializer(rating)
        return Response(result.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=["post", "delete"], url_path="favorite")
    def toggle_favorite(self, request, pk=None):
        """Toggle favorite status for a template."""
        template = self.get_object()
        if request.method == "POST":
            TemplateFavorite.objects.get_or_create(template=template, user=request.user)
            return Response({"favorited": True})
        else:
            TemplateFavorite.objects.filter(template=template, user=request.user).delete()
            return Response({"favorited": False})

    @action(detail=True, methods=["post"], url_path="auto-complete")
    def auto_complete(self, request, pk=None):
        """AI auto-complete a template section based on encounter context."""
        template = self.get_object()
        serializer = TemplateAutoCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from services.template_llm_service import TemplateLLMService
        llm = TemplateLLMService()

        result = llm.auto_complete_section(
            template_schema=template.schema,
            section_key=serializer.validated_data["section_key"],
            field_key=serializer.validated_data.get("field_key", ""),
            encounter_context=serializer.validated_data.get("encounter_context", {}),
            partial_content=serializer.validated_data.get("partial_content", ""),
            specialty=template.specialty,
        )

        # Increment use count
        NoteTemplate.objects.filter(id=template.id).update(use_count=models.F("use_count") + 1)

        return Response(result)

    @action(detail=False, methods=["get"], url_path="specialties")
    def list_specialties(self, request):
        """List available specialties with template counts."""
        from apps.templates.models import MedicalSpecialty
        counts = (
            NoteTemplate.objects.filter(status="published", visibility="public")
            .values("specialty")
            .annotate(count=Count("id"))
        )
        count_map = {c["specialty"]: c["count"] for c in counts}
        result = [
            {"value": choice[0], "label": choice[1], "template_count": count_map.get(choice[0], 0)}
            for choice in MedicalSpecialty.choices
        ]
        return Response(result)

    @action(detail=False, methods=["get"], url_path="favorites")
    def list_favorites(self, request):
        """List templates favorited by the current user."""
        favorite_ids = TemplateFavorite.objects.filter(user=request.user).values_list("template_id", flat=True)
        qs = self.get_queryset().filter(id__in=favorite_ids)
        serializer = NoteTemplateListSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)
```

### 2.6 `apps/templates/urls.py`

```python
from rest_framework.routers import DefaultRouter
from apps.templates.views import NoteTemplateViewSet

router = DefaultRouter()
router.register("", NoteTemplateViewSet, basename="template")

urlpatterns = router.urls
```

### 2.7 `apps/templates/specialty_configs.py`

Pre-built template schemas for 3 initial specialties. This file contains the seed data that will be loaded via a Django management command or data migration.

```python
PRIMARY_CARE_TEMPLATES = [
    {
        "name": "Primary Care - Annual Physical",
        "description": "Comprehensive annual wellness exam template with preventive screening checklist",
        "specialty": "primary_care",
        "note_type": "soap",
        "tags": ["annual-physical", "wellness", "preventive"],
        "schema": {
            "sections": [
                {
                    "key": "subjective",
                    "label": "Subjective",
                    "fields": [
                        {"key": "chief_complaint", "label": "Chief Complaint", "type": "text", "required": True},
                        {"key": "hpi", "label": "History of Present Illness", "type": "textarea", "required": True,
                         "ai_prompt": "Generate HPI based on chief complaint and patient demographics"},
                        {"key": "pmh", "label": "Past Medical History", "type": "textarea", "required": False},
                        {"key": "medications", "label": "Current Medications", "type": "textarea", "required": False},
                        {"key": "allergies", "label": "Allergies", "type": "textarea", "required": False},
                        {"key": "family_history", "label": "Family History", "type": "textarea", "required": False},
                        {"key": "social_history", "label": "Social History", "type": "textarea", "required": False},
                        {"key": "ros", "label": "Review of Systems", "type": "checklist",
                         "options": ["Constitutional", "HEENT", "Cardiovascular", "Respiratory",
                                     "Gastrointestinal", "Genitourinary", "Musculoskeletal",
                                     "Integumentary", "Neurological", "Psychiatric", "Endocrine",
                                     "Hematologic/Lymphatic", "Allergic/Immunologic"],
                         "required": True},
                    ],
                },
                {
                    "key": "objective",
                    "label": "Objective",
                    "fields": [
                        {"key": "vitals", "label": "Vital Signs", "type": "structured",
                         "subfields": [
                             {"key": "bp", "label": "BP", "type": "text", "placeholder": "120/80"},
                             {"key": "hr", "label": "HR", "type": "text", "placeholder": "72"},
                             {"key": "temp", "label": "Temp", "type": "text", "placeholder": "98.6"},
                             {"key": "rr", "label": "RR", "type": "text", "placeholder": "16"},
                             {"key": "spo2", "label": "SpO2", "type": "text", "placeholder": "98%"},
                             {"key": "weight", "label": "Weight", "type": "text"},
                             {"key": "height", "label": "Height", "type": "text"},
                             {"key": "bmi", "label": "BMI", "type": "text"},
                         ]},
                        {"key": "physical_exam", "label": "Physical Examination", "type": "textarea", "required": True,
                         "ai_prompt": "Generate physical exam findings based on chief complaint"},
                    ],
                },
                {
                    "key": "assessment",
                    "label": "Assessment",
                    "fields": [
                        {"key": "diagnoses", "label": "Diagnoses", "type": "textarea", "required": True,
                         "ai_prompt": "Suggest assessment based on subjective and objective findings"},
                        {"key": "icd10", "label": "ICD-10 Codes", "type": "code_list"},
                    ],
                },
                {
                    "key": "plan",
                    "label": "Plan",
                    "fields": [
                        {"key": "treatment", "label": "Treatment Plan", "type": "textarea", "required": True},
                        {"key": "prescriptions", "label": "Prescriptions", "type": "textarea"},
                        {"key": "follow_up", "label": "Follow-up", "type": "text"},
                        {"key": "referrals", "label": "Referrals", "type": "textarea"},
                        {"key": "preventive_screening", "label": "Preventive Screening", "type": "checklist",
                         "options": ["Lipid Panel", "A1c", "Mammogram", "Colonoscopy",
                                     "Bone Density", "Vision Screening", "Depression Screening (PHQ-9)",
                                     "Immunizations Review"]},
                        {"key": "cpt", "label": "CPT Codes", "type": "code_list"},
                    ],
                },
            ],
            "ai_instructions": "Focus on comprehensive documentation. Include screening recommendations based on age and sex. Ensure all preventive care elements are addressed for annual visit documentation.",
        },
    },
    {
        "name": "Primary Care - Acute Visit",
        "description": "Template for acute/urgent care visits in primary care setting",
        "specialty": "primary_care",
        "note_type": "soap",
        "tags": ["acute", "urgent", "sick-visit"],
        "schema": {
            "sections": [
                {
                    "key": "subjective",
                    "label": "Subjective",
                    "fields": [
                        {"key": "chief_complaint", "label": "Chief Complaint", "type": "text", "required": True},
                        {"key": "hpi", "label": "HPI", "type": "textarea", "required": True,
                         "ai_prompt": "Generate focused HPI for acute visit"},
                        {"key": "associated_symptoms", "label": "Associated Symptoms", "type": "textarea"},
                        {"key": "medications_tried", "label": "Medications/Treatments Tried", "type": "textarea"},
                    ],
                },
                {
                    "key": "objective",
                    "label": "Objective",
                    "fields": [
                        {"key": "vitals", "label": "Vital Signs", "type": "structured",
                         "subfields": [
                             {"key": "bp", "label": "BP", "type": "text"},
                             {"key": "hr", "label": "HR", "type": "text"},
                             {"key": "temp", "label": "Temp", "type": "text"},
                             {"key": "rr", "label": "RR", "type": "text"},
                             {"key": "spo2", "label": "SpO2", "type": "text"},
                         ]},
                        {"key": "focused_exam", "label": "Focused Physical Examination", "type": "textarea", "required": True},
                    ],
                },
                {
                    "key": "assessment",
                    "label": "Assessment",
                    "fields": [
                        {"key": "diagnoses", "label": "Assessment/Diagnoses", "type": "textarea", "required": True},
                        {"key": "differential", "label": "Differential Diagnosis", "type": "textarea"},
                    ],
                },
                {
                    "key": "plan",
                    "label": "Plan",
                    "fields": [
                        {"key": "treatment", "label": "Treatment", "type": "textarea", "required": True},
                        {"key": "prescriptions", "label": "Prescriptions", "type": "textarea"},
                        {"key": "follow_up", "label": "Follow-up Instructions", "type": "text"},
                        {"key": "return_precautions", "label": "Return Precautions", "type": "textarea"},
                    ],
                },
            ],
            "ai_instructions": "Focus on the acute complaint. Generate concise, focused documentation. Include relevant differential diagnoses.",
        },
    },
]

DERMATOLOGY_TEMPLATES = [
    {
        "name": "Dermatology - Skin Lesion Evaluation",
        "description": "Comprehensive dermatology template for skin lesion assessment with ABCDE criteria",
        "specialty": "dermatology",
        "note_type": "soap",
        "tags": ["skin-lesion", "biopsy", "mole-check"],
        "schema": {
            "sections": [
                {
                    "key": "subjective",
                    "label": "Subjective",
                    "fields": [
                        {"key": "chief_complaint", "label": "Chief Complaint", "type": "text", "required": True},
                        {"key": "hpi", "label": "HPI", "type": "textarea", "required": True,
                         "ai_prompt": "Generate dermatology-focused HPI including onset, duration, changes, symptoms (itching, bleeding, pain)"},
                        {"key": "lesion_history", "label": "Lesion History", "type": "textarea",
                         "placeholder": "Duration, changes in size/color/shape, prior treatments"},
                        {"key": "skin_cancer_risk", "label": "Skin Cancer Risk Factors", "type": "checklist",
                         "options": ["Fair skin", "History of sunburns", "Family history melanoma",
                                     "Personal history skin cancer", "Immunosuppression",
                                     "Multiple dysplastic nevi", "Organ transplant"]},
                        {"key": "medications", "label": "Current Medications", "type": "textarea"},
                    ],
                },
                {
                    "key": "objective",
                    "label": "Objective",
                    "fields": [
                        {"key": "lesion_description", "label": "Lesion Description", "type": "textarea", "required": True,
                         "ai_prompt": "Generate dermatological lesion description using standard morphology terminology"},
                        {"key": "abcde", "label": "ABCDE Criteria", "type": "structured",
                         "subfields": [
                             {"key": "asymmetry", "label": "Asymmetry", "type": "select",
                              "options": ["Symmetric", "Asymmetric"]},
                             {"key": "border", "label": "Border", "type": "select",
                              "options": ["Regular", "Irregular", "Scalloped", "Poorly defined"]},
                             {"key": "color", "label": "Color", "type": "text",
                              "placeholder": "Uniform tan, variegated brown/black..."},
                             {"key": "diameter", "label": "Diameter", "type": "text",
                              "placeholder": "mm"},
                             {"key": "evolution", "label": "Evolution", "type": "select",
                              "options": ["Stable", "Changing", "New lesion"]},
                         ]},
                        {"key": "location", "label": "Location", "type": "text", "required": True},
                        {"key": "size", "label": "Size (cm)", "type": "text"},
                        {"key": "dermoscopy", "label": "Dermoscopy Findings", "type": "textarea"},
                        {"key": "photos", "label": "Clinical Photos", "type": "text",
                         "placeholder": "Number of photos taken and stored"},
                    ],
                },
                {
                    "key": "assessment",
                    "label": "Assessment",
                    "fields": [
                        {"key": "diagnoses", "label": "Clinical Impression", "type": "textarea", "required": True},
                        {"key": "differential", "label": "Differential Diagnosis", "type": "textarea"},
                    ],
                },
                {
                    "key": "plan",
                    "label": "Plan",
                    "fields": [
                        {"key": "procedure", "label": "Procedure", "type": "textarea",
                         "placeholder": "Biopsy type (shave/punch/excisional), anesthesia, site prep"},
                        {"key": "treatment", "label": "Treatment Plan", "type": "textarea", "required": True},
                        {"key": "prescriptions", "label": "Prescriptions", "type": "textarea"},
                        {"key": "wound_care", "label": "Wound Care Instructions", "type": "textarea"},
                        {"key": "follow_up", "label": "Follow-up", "type": "text"},
                        {"key": "pathology_pending", "label": "Pathology Pending", "type": "select",
                         "options": ["Yes", "No", "N/A"]},
                    ],
                },
            ],
            "ai_instructions": "Use precise dermatological morphology terminology (papule, plaque, macule, etc.). Include ABCDE criteria assessment for pigmented lesions. Document photographic evidence references.",
        },
    },
]

PSYCHIATRY_TEMPLATES = [
    {
        "name": "Psychiatry - Initial Psychiatric Evaluation",
        "description": "Comprehensive initial psychiatric assessment template with PHQ-9, GAD-7 scoring",
        "specialty": "psychiatry",
        "note_type": "soap",
        "tags": ["initial-eval", "psychiatric-assessment", "mental-health"],
        "schema": {
            "sections": [
                {
                    "key": "subjective",
                    "label": "Subjective",
                    "fields": [
                        {"key": "chief_complaint", "label": "Chief Complaint / Reason for Visit", "type": "text", "required": True},
                        {"key": "hpi", "label": "History of Present Illness", "type": "textarea", "required": True,
                         "ai_prompt": "Generate psychiatric HPI including onset, duration, severity, triggers, current symptoms, functional impact"},
                        {"key": "psychiatric_history", "label": "Past Psychiatric History", "type": "textarea",
                         "placeholder": "Prior diagnoses, hospitalizations, past medications and response, suicide attempts"},
                        {"key": "substance_use", "label": "Substance Use History", "type": "textarea",
                         "placeholder": "Alcohol, tobacco, cannabis, other substances - frequency, quantity, last use"},
                        {"key": "trauma_history", "label": "Trauma History", "type": "textarea"},
                        {"key": "family_psychiatric", "label": "Family Psychiatric History", "type": "textarea"},
                        {"key": "social_history", "label": "Social History", "type": "textarea",
                         "placeholder": "Living situation, employment, relationships, support system, legal issues"},
                        {"key": "current_medications", "label": "Current Medications", "type": "textarea"},
                        {"key": "allergies", "label": "Allergies", "type": "textarea"},
                    ],
                },
                {
                    "key": "objective",
                    "label": "Objective / Mental Status Examination",
                    "fields": [
                        {"key": "appearance", "label": "Appearance", "type": "textarea",
                         "placeholder": "Age-appropriate, grooming, attire, psychomotor activity"},
                        {"key": "behavior", "label": "Behavior", "type": "textarea",
                         "placeholder": "Cooperative, eye contact, rapport"},
                        {"key": "speech", "label": "Speech", "type": "textarea",
                         "placeholder": "Rate, rhythm, volume, tone"},
                        {"key": "mood", "label": "Mood (Patient-reported)", "type": "text"},
                        {"key": "affect", "label": "Affect (Observed)", "type": "text",
                         "placeholder": "Range, congruence, stability"},
                        {"key": "thought_process", "label": "Thought Process", "type": "text",
                         "placeholder": "Linear, goal-directed, tangential, circumstantial"},
                        {"key": "thought_content", "label": "Thought Content", "type": "textarea",
                         "placeholder": "Delusions, obsessions, phobias, ideas of reference"},
                        {"key": "perceptions", "label": "Perceptions", "type": "textarea",
                         "placeholder": "Hallucinations (AH, VH), illusions"},
                        {"key": "cognition", "label": "Cognition", "type": "textarea",
                         "placeholder": "Alert, oriented, attention, concentration, memory"},
                        {"key": "insight", "label": "Insight", "type": "select",
                         "options": ["Good", "Fair", "Limited", "Poor"]},
                        {"key": "judgment", "label": "Judgment", "type": "select",
                         "options": ["Good", "Fair", "Limited", "Poor"]},
                        {"key": "suicidal_ideation", "label": "Suicidal Ideation", "type": "textarea", "required": True,
                         "placeholder": "Denies SI/HI. If present: frequency, plan, intent, means, protective factors"},
                        {"key": "homicidal_ideation", "label": "Homicidal Ideation", "type": "textarea", "required": True},
                        {"key": "phq9_score", "label": "PHQ-9 Score", "type": "text"},
                        {"key": "gad7_score", "label": "GAD-7 Score", "type": "text"},
                    ],
                },
                {
                    "key": "assessment",
                    "label": "Assessment",
                    "fields": [
                        {"key": "diagnoses", "label": "Diagnoses (DSM-5)", "type": "textarea", "required": True},
                        {"key": "risk_assessment", "label": "Risk Assessment", "type": "textarea", "required": True,
                         "placeholder": "Risk level (low/moderate/high), risk factors, protective factors"},
                    ],
                },
                {
                    "key": "plan",
                    "label": "Plan",
                    "fields": [
                        {"key": "medication_plan", "label": "Medication Plan", "type": "textarea"},
                        {"key": "therapy_recommendations", "label": "Therapy Recommendations", "type": "textarea"},
                        {"key": "safety_plan", "label": "Safety Plan", "type": "textarea",
                         "conditional": {"show_if": {"field": "suicidal_ideation", "not_empty": True}}},
                        {"key": "follow_up", "label": "Follow-up", "type": "text", "required": True},
                        {"key": "crisis_resources", "label": "Crisis Resources Provided", "type": "select",
                         "options": ["Yes", "No", "N/A"]},
                    ],
                },
            ],
            "ai_instructions": "Use psychiatric terminology accurately. Always document suicide/homicide risk assessment. Include PHQ-9 and GAD-7 scores when available. Follow DSM-5 diagnostic criteria in assessment. Ensure safety planning is documented when appropriate.",
        },
    },
]

ALL_SPECIALTY_TEMPLATES = PRIMARY_CARE_TEMPLATES + DERMATOLOGY_TEMPLATES + PSYCHIATRY_TEMPLATES
```

### 2.8 `apps/templates/admin.py`

```python
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
```

---

## 3. Backend: `apps/quality/` App

### 3.1 File Structure

```
backend/apps/quality/
    __init__.py
    apps.py
    models.py              # QualityScore model
    serializers.py          # QualityScoreSerializer
    views.py                # QualityScore views (trigger scoring, get score)
    rules_engine.py         # CMS E/M documentation rules
    admin.py
    urls.py
    tests/
        __init__.py
        test_models.py
        test_rules_engine.py
        test_views.py
        test_quality_worker.py
```

### 3.2 `apps/quality/apps.py`

```python
from django.apps import AppConfig


class QualityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.quality"
    verbose_name = "Quality Checker"
```

### 3.3 `apps/quality/rules_engine.py`

The rules engine evaluates clinical notes against CMS E/M documentation requirements (2021+ guidelines based on MDM or time).

```python
"""
CMS E/M Documentation Quality Rules Engine

Evaluates clinical notes against CMS Evaluation and Management (E/M) documentation
requirements based on the 2021+ guidelines (medical decision making or time-based).

Scoring categories:
1. History (HPI elements, ROS, PFSH)
2. Examination (body systems, organ systems examined)
3. Medical Decision Making (diagnoses, data, risk)
4. Coding Accuracy (ICD-10/CPT appropriateness)
"""

import re
from dataclasses import dataclass, field


@dataclass
class RuleFinding:
    category: str
    element: str
    status: str  # "present", "missing", "insufficient"
    detail: str = ""
    suggestion: str = ""
    weight: float = 1.0  # Scoring weight


@dataclass
class CategoryScore:
    score: float
    max_score: float
    items_found: list = field(default_factory=list)
    items_missing: list = field(default_factory=list)


class CMSRulesEngine:
    """Evaluates clinical notes against CMS E/M documentation requirements."""

    VERSION = "1.0.0"

    # HPI elements per CMS guidelines
    HPI_ELEMENTS = [
        ("location", ["location", "site", "area", "region"]),
        ("quality", ["quality", "sharp", "dull", "aching", "burning", "throbbing"]),
        ("severity", ["severity", "scale", "mild", "moderate", "severe", "/10"]),
        ("duration", ["duration", "days", "weeks", "months", "years", "since", "onset"]),
        ("timing", ["timing", "constant", "intermittent", "frequent", "occasional"]),
        ("context", ["context", "after", "when", "during", "triggered"]),
        ("modifying_factors", ["better", "worse", "relieved", "aggravated", "alleviating"]),
        ("associated_signs", ["associated", "accompanied", "also", "with", "without"]),
    ]

    # Review of Systems categories
    ROS_SYSTEMS = [
        "constitutional", "heent", "cardiovascular", "respiratory",
        "gastrointestinal", "genitourinary", "musculoskeletal",
        "integumentary", "neurological", "psychiatric", "endocrine",
        "hematologic", "allergic",
    ]

    # Physical exam body areas
    EXAM_SYSTEMS = [
        ("vitals", ["bp", "blood pressure", "heart rate", "pulse", "temperature",
                     "respiratory rate", "spo2", "oxygen", "weight", "bmi"]),
        ("heent", ["head", "eyes", "ears", "nose", "throat", "pupils", "conjunctiva"]),
        ("neck", ["neck", "thyroid", "lymph", "jugular"]),
        ("cardiovascular", ["heart", "cardiac", "murmur", "rhythm", "s1", "s2"]),
        ("respiratory", ["lungs", "breath sounds", "wheezing", "rales", "rhonchi"]),
        ("abdomen", ["abdomen", "bowel sounds", "tender", "distension", "hepatomegaly"]),
        ("musculoskeletal", ["extremities", "range of motion", "joint", "muscle", "gait"]),
        ("neurological", ["cranial nerves", "motor", "sensory", "reflexes", "coordination"]),
        ("skin", ["skin", "rash", "lesion", "wound", "erythema"]),
        ("psychiatric", ["mood", "affect", "orientation", "judgment", "insight"]),
    ]

    def score_note(self, subjective: str, objective: str, assessment: str, plan: str,
                   icd10_codes: list = None, cpt_codes: list = None) -> dict:
        """Score a clinical note and return detailed results."""
        icd10_codes = icd10_codes or []
        cpt_codes = cpt_codes or []

        findings = []

        # Score each category
        history_score = self._score_history(subjective, findings)
        exam_score = self._score_examination(objective, findings)
        mdm_score = self._score_medical_decision_making(assessment, plan, icd10_codes, findings)
        coding_score = self._score_coding(icd10_codes, cpt_codes, assessment, findings)

        # Calculate overall score
        category_scores = {
            "history": {
                "score": history_score.score,
                "max_score": history_score.max_score,
                "items_found": history_score.items_found,
                "items_missing": history_score.items_missing,
            },
            "examination": {
                "score": exam_score.score,
                "max_score": exam_score.max_score,
                "items_found": exam_score.items_found,
                "items_missing": exam_score.items_missing,
            },
            "medical_decision_making": {
                "score": mdm_score.score,
                "max_score": mdm_score.max_score,
                "items_found": mdm_score.items_found,
                "items_missing": mdm_score.items_missing,
            },
            "coding_accuracy": {
                "score": coding_score.score,
                "max_score": coding_score.max_score,
                "items_found": coding_score.items_found,
                "items_missing": coding_score.items_missing,
            },
        }

        total_score = sum(cs["score"] for cs in category_scores.values())
        total_max = sum(cs["max_score"] for cs in category_scores.values())
        overall_pct = round((total_score / total_max * 100) if total_max > 0 else 0, 1)

        # Determine score level
        if overall_pct >= 90:
            score_level = "excellent"
        elif overall_pct >= 75:
            score_level = "good"
        elif overall_pct >= 50:
            score_level = "fair"
        else:
            score_level = "needs_improvement"

        # Generate suggestions from findings
        suggestions = [f.suggestion for f in findings if f.status in ("missing", "insufficient") and f.suggestion]

        # Determine E/M level
        em_level = self._determine_em_level(history_score, exam_score, mdm_score)

        return {
            "overall_score": overall_pct,
            "score_level": score_level,
            "category_scores": category_scores,
            "findings": [
                {"category": f.category, "element": f.element, "status": f.status,
                 "detail": f.detail, "suggestion": f.suggestion}
                for f in findings
            ],
            "suggestions": suggestions,
            "em_level_suggested": em_level,
            "rules_version": self.VERSION,
        }

    def _score_history(self, subjective: str, findings: list) -> CategoryScore:
        text_lower = subjective.lower()
        found = []
        missing = []
        score = 0
        max_score = len(self.HPI_ELEMENTS) + 2  # +2 for ROS and PFSH

        # Check HPI elements
        for element_name, keywords in self.HPI_ELEMENTS:
            if any(kw in text_lower for kw in keywords):
                found.append(element_name)
                score += 1
                findings.append(RuleFinding("history", element_name, "present",
                                            f"HPI element '{element_name}' documented"))
            else:
                missing.append(element_name)
                findings.append(RuleFinding("history", element_name, "missing",
                                            f"HPI element '{element_name}' not found",
                                            f"Consider documenting {element_name} in HPI"))

        # Check for ROS
        ros_count = sum(1 for sys in self.ROS_SYSTEMS if sys in text_lower or sys[:4] in text_lower)
        if ros_count >= 10:
            found.append("complete_ros")
            score += 1
            findings.append(RuleFinding("history", "ROS", "present",
                                        f"Complete ROS documented ({ros_count} systems)"))
        elif ros_count >= 2:
            found.append("partial_ros")
            score += 0.5
            findings.append(RuleFinding("history", "ROS", "insufficient",
                                        f"Partial ROS ({ros_count} systems)",
                                        "Document at least 10 systems for complete ROS"))
        else:
            missing.append("ros")
            findings.append(RuleFinding("history", "ROS", "missing",
                                        "Review of Systems not documented",
                                        "Add Review of Systems to subjective section"))

        # Check for PFSH (Past/Family/Social History)
        pfsh_keywords = ["past medical", "pmh", "family history", "social history",
                         "surgical history", "medications", "allergies"]
        pfsh_count = sum(1 for kw in pfsh_keywords if kw in text_lower)
        if pfsh_count >= 3:
            found.append("pfsh")
            score += 1
            findings.append(RuleFinding("history", "PFSH", "present", "PFSH documented"))
        elif pfsh_count >= 1:
            found.append("partial_pfsh")
            score += 0.5
            findings.append(RuleFinding("history", "PFSH", "insufficient",
                                        "Partial PFSH documented",
                                        "Include past medical, family, and social history"))
        else:
            missing.append("pfsh")
            findings.append(RuleFinding("history", "PFSH", "missing",
                                        "Past/Family/Social History not documented",
                                        "Add PFSH to subjective section"))

        return CategoryScore(score, max_score, found, missing)

    def _score_examination(self, objective: str, findings: list) -> CategoryScore:
        text_lower = objective.lower()
        found = []
        missing = []
        score = 0
        max_score = len(self.EXAM_SYSTEMS)

        for system_name, keywords in self.EXAM_SYSTEMS:
            if any(kw in text_lower for kw in keywords):
                found.append(system_name)
                score += 1
                findings.append(RuleFinding("examination", system_name, "present",
                                            f"Exam system '{system_name}' documented"))
            else:
                missing.append(system_name)
                findings.append(RuleFinding("examination", system_name, "missing",
                                            f"Exam system '{system_name}' not documented",
                                            f"Consider documenting {system_name} examination"))

        return CategoryScore(score, max_score, found, missing)

    def _score_medical_decision_making(self, assessment: str, plan: str,
                                       icd10_codes: list, findings: list) -> CategoryScore:
        text_lower = (assessment + " " + plan).lower()
        found = []
        missing = []
        score = 0
        max_score = 5

        # Check for documented diagnoses
        if len(assessment.strip()) > 20:
            found.append("diagnoses_documented")
            score += 1
            findings.append(RuleFinding("medical_decision_making", "diagnoses", "present",
                                        "Diagnoses/assessment documented"))
        else:
            missing.append("diagnoses")
            findings.append(RuleFinding("medical_decision_making", "diagnoses", "missing",
                                        "Assessment section is too brief",
                                        "Expand assessment with clinical reasoning and diagnoses"))

        # Check for differential diagnosis
        diff_keywords = ["differential", "rule out", "r/o", "consider", "versus", "vs"]
        if any(kw in text_lower for kw in diff_keywords):
            found.append("differential")
            score += 1
            findings.append(RuleFinding("medical_decision_making", "differential", "present",
                                        "Differential diagnosis considered"))
        else:
            missing.append("differential")
            findings.append(RuleFinding("medical_decision_making", "differential", "missing",
                                        "No differential diagnosis documented",
                                        "Include differential diagnoses in assessment"))

        # Check for treatment plan
        plan_keywords = ["prescribe", "medication", "refer", "follow-up", "follow up",
                         "return", "lab", "test", "imaging", "treatment"]
        if any(kw in text_lower for kw in plan_keywords):
            found.append("treatment_plan")
            score += 1
            findings.append(RuleFinding("medical_decision_making", "treatment_plan", "present",
                                        "Treatment plan documented"))
        else:
            missing.append("treatment_plan")
            findings.append(RuleFinding("medical_decision_making", "treatment_plan", "missing",
                                        "Treatment plan not clearly documented",
                                        "Document specific treatment plan, medications, or referrals"))

        # Check for risk assessment
        risk_keywords = ["risk", "prognosis", "monitoring", "precaution", "emergency",
                         "hospitalization", "complication"]
        if any(kw in text_lower for kw in risk_keywords):
            found.append("risk_assessment")
            score += 1
            findings.append(RuleFinding("medical_decision_making", "risk_assessment", "present",
                                        "Risk level documented"))
        else:
            missing.append("risk_assessment")
            findings.append(RuleFinding("medical_decision_making", "risk_assessment", "missing",
                                        "Risk assessment not documented",
                                        "Consider documenting risk level and management considerations"))

        # Check ICD-10 codes
        if len(icd10_codes) > 0:
            found.append("icd10_codes")
            score += 1
            findings.append(RuleFinding("medical_decision_making", "icd10_codes", "present",
                                        f"{len(icd10_codes)} ICD-10 code(s) documented"))
        else:
            missing.append("icd10_codes")
            findings.append(RuleFinding("medical_decision_making", "icd10_codes", "missing",
                                        "No ICD-10 codes documented",
                                        "Add appropriate ICD-10 codes for diagnoses"))

        return CategoryScore(score, max_score, found, missing)

    def _score_coding(self, icd10_codes: list, cpt_codes: list,
                      assessment: str, findings: list) -> CategoryScore:
        found = []
        missing = []
        score = 0
        max_score = 3

        # ICD-10 format validation
        icd10_pattern = re.compile(r'^[A-Z]\d{2}(\.\d{1,4})?$')
        if icd10_codes:
            valid_codes = [c for c in icd10_codes if icd10_pattern.match(c)]
            if len(valid_codes) == len(icd10_codes):
                found.append("icd10_format_valid")
                score += 1
                findings.append(RuleFinding("coding_accuracy", "icd10_format", "present",
                                            "ICD-10 codes are properly formatted"))
            else:
                found.append("icd10_partial_valid")
                score += 0.5
                findings.append(RuleFinding("coding_accuracy", "icd10_format", "insufficient",
                                            f"{len(valid_codes)}/{len(icd10_codes)} ICD-10 codes valid",
                                            "Review ICD-10 code formatting (e.g., R51.9)"))
        else:
            missing.append("icd10_codes")
            findings.append(RuleFinding("coding_accuracy", "icd10_codes", "missing",
                                        "No ICD-10 codes", "Add ICD-10 codes for documented diagnoses"))

        # CPT code presence
        if cpt_codes:
            found.append("cpt_codes")
            score += 1
            findings.append(RuleFinding("coding_accuracy", "cpt_codes", "present",
                                        f"{len(cpt_codes)} CPT code(s) documented"))
        else:
            missing.append("cpt_codes")
            findings.append(RuleFinding("coding_accuracy", "cpt_codes", "missing",
                                        "No CPT codes documented",
                                        "Add appropriate CPT/E&M codes"))

        # Code-assessment alignment (basic check)
        if icd10_codes and len(assessment.strip()) > 10:
            found.append("code_alignment")
            score += 1
            findings.append(RuleFinding("coding_accuracy", "code_alignment", "present",
                                        "Codes appear aligned with assessment"))
        elif icd10_codes:
            missing.append("code_alignment")
            findings.append(RuleFinding("coding_accuracy", "code_alignment", "insufficient",
                                        "Assessment may not fully support codes",
                                        "Ensure documented assessment supports all coded diagnoses"))

        return CategoryScore(score, max_score, found, missing)

    def _determine_em_level(self, history: CategoryScore, exam: CategoryScore,
                            mdm: CategoryScore) -> str:
        """Determine suggested E/M level based on MDM complexity (2021+ guidelines)."""
        mdm_pct = (mdm.score / mdm.max_score * 100) if mdm.max_score > 0 else 0

        if mdm_pct >= 80:
            return "99215"  # High complexity
        elif mdm_pct >= 60:
            return "99214"  # Moderate complexity
        elif mdm_pct >= 40:
            return "99213"  # Low complexity
        elif mdm_pct >= 20:
            return "99212"  # Straightforward
        else:
            return "99211"  # Minimal
```

### 3.4 `apps/quality/serializers.py`

```python
from rest_framework import serializers
from apps.quality.models import QualityScore


class QualityScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualityScore
        fields = [
            "id", "clinical_note", "encounter", "overall_score", "score_level",
            "category_scores", "findings", "suggestions",
            "em_level_suggested", "em_level_documented",
            "rules_version", "scored_at", "updated_at",
        ]
        read_only_fields = fields
```

### 3.5 `apps/quality/views.py`

```python
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.permissions import IsDoctorOrAdmin
from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote
from apps.quality.models import QualityScore
from apps.quality.serializers import QualityScoreSerializer


@api_view(["GET"])
@permission_classes([IsDoctorOrAdmin])
def encounter_quality_score(request, encounter_id):
    """Get quality score for an encounter's clinical note."""
    try:
        encounter = Encounter.objects.get(
            id=encounter_id, doctor__practice=request.user.practice
        )
    except Encounter.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    try:
        score = QualityScore.objects.get(encounter=encounter)
    except QualityScore.DoesNotExist:
        return Response(
            {"error": "No quality score available. Score is generated after note creation."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = QualityScoreSerializer(score)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsDoctorOrAdmin])
def trigger_quality_score(request, encounter_id):
    """Manually trigger quality scoring for a note."""
    try:
        encounter = Encounter.objects.get(
            id=encounter_id, doctor__practice=request.user.practice
        )
    except Encounter.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    try:
        note = encounter.clinical_note
    except ClinicalNote.DoesNotExist:
        return Response(
            {"error": "No clinical note available for this encounter."},
            status=status.HTTP_404_NOT_FOUND,
        )

    from workers.quality_checker import quality_check_task
    quality_check_task.delay(str(encounter.id))

    return Response(
        {"status": "scoring", "encounter_id": str(encounter.id)},
        status=status.HTTP_202_ACCEPTED,
    )
```

### 3.6 `apps/quality/urls.py`

```python
from django.urls import path
from apps.quality.views import encounter_quality_score, trigger_quality_score

urlpatterns = [
    path("<uuid:encounter_id>/quality/", encounter_quality_score, name="encounter-quality-score"),
    path("<uuid:encounter_id>/quality/score/", trigger_quality_score, name="trigger-quality-score"),
]
```

---

## 4. Workers: Quality Checker

### 4.1 `workers/quality_checker.py`

```python
import logging

from celery import shared_task
from django.db import transaction

from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote
from apps.quality.models import QualityScore
from apps.quality.rules_engine import CMSRulesEngine

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=5,
    retry_backoff=True,
    time_limit=60,
    name="workers.quality_checker.quality_check_task",
)
def quality_check_task(self, encounter_id: str):
    """Score a clinical note against CMS E/M documentation requirements."""
    try:
        encounter = Encounter.objects.get(id=encounter_id)
        note = ClinicalNote.objects.get(encounter=encounter)
    except (Encounter.DoesNotExist, ClinicalNote.DoesNotExist):
        logger.error(f"Encounter or note not found for quality check: {encounter_id}")
        return

    try:
        engine = CMSRulesEngine()
        result = engine.score_note(
            subjective=note.subjective,
            objective=note.objective,
            assessment=note.assessment,
            plan=note.plan,
            icd10_codes=note.icd10_codes,
            cpt_codes=note.cpt_codes,
        )

        with transaction.atomic():
            QualityScore.objects.update_or_create(
                encounter=encounter,
                defaults={
                    "clinical_note": note,
                    "overall_score": result["overall_score"],
                    "score_level": result["score_level"],
                    "category_scores": result["category_scores"],
                    "findings": result["findings"],
                    "suggestions": result["suggestions"],
                    "em_level_suggested": result["em_level_suggested"],
                    "em_level_documented": note.cpt_codes[0] if note.cpt_codes else "",
                    "rules_version": result["rules_version"],
                },
            )

        logger.info(f"Quality score for {encounter_id}: {result['overall_score']}% ({result['score_level']})")
        _send_ws_update(encounter_id, "quality_scored", result["overall_score"])

    except Exception as exc:
        logger.error(f"Quality check failed for {encounter_id}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)


def _send_ws_update(encounter_id: str, event_type: str, score: float = None):
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"encounter_{encounter_id}",
            {
                "type": "job_status_update",
                "status": event_type,
                "encounter_id": encounter_id,
                "quality_score": score,
            },
        )
    except Exception as e:
        logger.warning(f"WebSocket update failed: {e}")
```

---

## 5. Services: Template LLM Service

### 5.1 `services/template_llm_service.py`

```python
import json
import logging

import anthropic
from django.conf import settings

logger = logging.getLogger(__name__)

TEMPLATE_AUTO_COMPLETE_SYSTEM = """You are a medical documentation assistant specialized in auto-completing clinical note template sections.

You are working within a {specialty} clinical note template.

Template AI instructions: {ai_instructions}

Given the encounter context and the section/field being filled, generate appropriate clinical content.

Rules:
- Use proper medical terminology for the specialty
- Be concise but thorough
- Follow standard documentation conventions
- Generate content appropriate for the specific field type
- If partial content is provided, continue from where it left off
- Output ONLY the text content for the field, no JSON wrapping unless the field is structured

Output strict JSON:
{{
  "content": "generated text content",
  "confidence": 0.0-1.0,
  "suggestions": ["optional alternative phrasings"]
}}"""


class TemplateLLMService:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"

    def auto_complete_section(
        self,
        template_schema: dict,
        section_key: str,
        field_key: str,
        encounter_context: dict,
        partial_content: str,
        specialty: str,
    ) -> dict:
        """Auto-complete a template section/field using AI."""

        # Find the section and field in schema
        section = None
        target_field = None
        for s in template_schema.get("sections", []):
            if s["key"] == section_key:
                section = s
                if field_key:
                    for f in s.get("fields", []):
                        if f["key"] == field_key:
                            target_field = f
                            break
                break

        if not section:
            return {"content": "", "confidence": 0, "error": "Section not found"}

        ai_instructions = template_schema.get("ai_instructions", "")
        field_ai_prompt = target_field.get("ai_prompt", "") if target_field else ""

        system = TEMPLATE_AUTO_COMPLETE_SYSTEM.format(
            specialty=specialty.replace("_", " ").title(),
            ai_instructions=ai_instructions,
        )

        # Build the user prompt with context
        context_parts = []
        if encounter_context.get("transcript_text"):
            context_parts.append(f"Transcript: {encounter_context['transcript_text'][:3000]}")
        if encounter_context.get("chief_complaint"):
            context_parts.append(f"Chief Complaint: {encounter_context['chief_complaint']}")
        if encounter_context.get("patient_age"):
            context_parts.append(f"Patient Age: {encounter_context['patient_age']}")
        if encounter_context.get("patient_sex"):
            context_parts.append(f"Patient Sex: {encounter_context['patient_sex']}")
        if encounter_context.get("existing_sections"):
            for key, value in encounter_context["existing_sections"].items():
                context_parts.append(f"Already documented - {key}: {value[:500]}")

        context_text = "\n".join(context_parts) if context_parts else "No additional context provided."

        user_prompt = f"""
Section: {section.get('label', section_key)}
Field: {target_field.get('label', field_key) if target_field else 'entire section'}
Field type: {target_field.get('type', 'textarea') if target_field else 'textarea'}
Field-specific instructions: {field_ai_prompt}

Encounter context:
{context_text}

{'Partial content to continue: ' + partial_content if partial_content else 'Generate fresh content.'}
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system,
                messages=[{"role": "user", "content": user_prompt}],
            )
            raw = response.content[0].text
            return self._parse_json(raw)
        except Exception as e:
            logger.error(f"Template auto-complete failed: {e}")
            return {"content": "", "confidence": 0, "error": str(e)}

    def _parse_json(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse template LLM JSON: {e}")
            return {"content": text, "confidence": 0.5, "suggestions": []}
```

### 5.2 `prompts/template_auto_complete.py`

```python
TEMPLATE_AUTO_COMPLETE_PROMPT_V1 = """You are a medical documentation assistant specialized in auto-completing clinical note template sections.

Specialty: {specialty}
Template context: {ai_instructions}

Given encounter context and the target field, generate appropriate clinical documentation content.

Rules:
- Use proper medical terminology for the {specialty} specialty
- Be concise but clinically thorough
- Follow standard documentation conventions
- If partial content is provided, continue seamlessly from where it left off

Output strict JSON:
{{
  "content": "generated text content for the field",
  "confidence": 0.0-1.0,
  "suggestions": ["alternative phrasings if applicable"]
}}"""
```

---

## 6. API Endpoints

### 6.1 URL Configuration Updates

**`config/urls.py`** -- add new routes:

```python
urlpatterns = [
    # ... existing routes ...
    path("api/v1/templates/", include("apps.templates.urls")),
    path("api/v1/encounters/", include("apps.quality.urls")),  # Quality score under encounters
]
```

### 6.2 Celery Configuration Update

**`config/celery.py`** -- add quality_checker route:

```python
app.autodiscover_tasks(["workers"])

app.conf.task_routes = {
    "workers.transcription.*": {"queue": "transcription"},
    "workers.soap_note.*": {"queue": "soap_note"},
    "workers.summary.*": {"queue": "summary"},
    "workers.ocr.*": {"queue": "ocr"},
    "workers.quality_checker.*": {"queue": "quality"},  # NEW
}
```

### 6.3 Complete API Endpoint Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/templates/` | List templates (query params: `scope=marketplace\|mine`, specialty, search) |
| POST | `/api/v1/templates/` | Create new template |
| GET | `/api/v1/templates/{id}/` | Get template detail with schema |
| PATCH | `/api/v1/templates/{id}/` | Update template |
| DELETE | `/api/v1/templates/{id}/` | Delete own template |
| POST | `/api/v1/templates/{id}/clone/` | Clone template to own collection |
| POST | `/api/v1/templates/{id}/rate/` | Rate template (1-5) |
| POST/DELETE | `/api/v1/templates/{id}/favorite/` | Toggle favorite |
| POST | `/api/v1/templates/{id}/auto-complete/` | AI auto-complete a section |
| GET | `/api/v1/templates/specialties/` | List specialties with counts |
| GET | `/api/v1/templates/favorites/` | List user's favorite templates |
| GET | `/api/v1/encounters/{id}/quality/` | Get quality score |
| POST | `/api/v1/encounters/{id}/quality/score/` | Trigger quality scoring |

---

## 7. Web Dashboard: Templates Section

### 7.1 New Frontend Files

```
web/src/
    types/index.ts                                    # UPDATE: add Template types
    lib/api-client.ts                                 # UPDATE: add templates + quality API methods
    hooks/use-templates.ts                            # NEW: TanStack Query hooks
    hooks/use-quality.ts                              # NEW: Quality score hooks
    components/shared/sidebar.tsx                     # UPDATE: add Templates nav item
    components/templates/
        template-card.tsx                              # Template card for list/marketplace
        template-editor.tsx                            # Schema-driven template editor
        template-section-form.tsx                      # Individual section form with AI auto-complete
        specialty-filter.tsx                            # Specialty filter bar
        rating-stars.tsx                                # Star rating component
        template-schema-builder.tsx                    # Visual template schema builder (create/edit)
    components/quality/
        quality-score-badge.tsx                         # Compact score badge
        quality-score-detail.tsx                        # Full score breakdown card
    app/(dashboard)/templates/
        page.tsx                                        # Templates list/browse page
        templates-list.tsx                              # List component with marketplace tabs
        [id]/
            page.tsx                                    # Template detail page
            template-detail.tsx                        # Detail component
        new/
            page.tsx                                    # Create new template page
            new-template-form.tsx                      # Create form component
        edit/[id]/
            page.tsx                                    # Edit template page
            edit-template-form.tsx                     # Edit form component
```

### 7.2 TypeScript Types (`web/src/types/index.ts` additions)

```typescript
// ============ Template Types ============

export type MedicalSpecialty =
  | "primary_care" | "dermatology" | "psychiatry" | "cardiology"
  | "orthopedics" | "pediatrics" | "neurology" | "gastroenterology" | "general";

export type TemplateVisibility = "private" | "practice" | "public";
export type TemplateStatus = "draft" | "published" | "archived";

export interface TemplateField {
  key: string;
  label: string;
  type: "text" | "textarea" | "checklist" | "select" | "structured" | "code_list";
  required?: boolean;
  ai_prompt?: string;
  placeholder?: string;
  options?: string[];
  subfields?: TemplateField[];
  conditional?: Record<string, unknown>;
}

export interface TemplateSection {
  key: string;
  label: string;
  fields: TemplateField[];
  default_content?: string;
}

export interface TemplateSchema {
  sections: TemplateSection[];
  conditional_logic?: Array<Record<string, unknown>>;
  ai_instructions?: string;
}

export interface NoteTemplate {
  id: string;
  name: string;
  description: string;
  specialty: MedicalSpecialty;
  note_type: NoteType;
  schema: TemplateSchema;
  visibility: TemplateVisibility;
  status: TemplateStatus;
  version: number;
  tags: string[];
  use_count: number;
  clone_count: number;
  average_rating: number | null;
  rating_count: number;
  is_favorited: boolean;
  author_name: string;
  created_at: string;
  updated_at: string;
  ratings?: TemplateRating[];
}

export interface NoteTemplateListItem {
  id: string;
  name: string;
  description: string;
  specialty: MedicalSpecialty;
  note_type: NoteType;
  visibility: TemplateVisibility;
  status: TemplateStatus;
  version: number;
  tags: string[];
  use_count: number;
  clone_count: number;
  average_rating: number | null;
  rating_count: number;
  is_favorited: boolean;
  author_name: string;
  created_at: string;
  updated_at: string;
}

export interface CreateTemplateRequest {
  name: string;
  description?: string;
  specialty: MedicalSpecialty;
  note_type: NoteType;
  schema: TemplateSchema;
  visibility?: TemplateVisibility;
  status?: TemplateStatus;
  tags?: string[];
}

export interface TemplateRating {
  id: string;
  template: string;
  user: string;
  user_name: string;
  score: number;
  review: string;
  created_at: string;
}

export interface AutoCompleteRequest {
  section_key: string;
  field_key?: string;
  encounter_context?: Record<string, unknown>;
  partial_content?: string;
}

export interface AutoCompleteResponse {
  content: string;
  confidence: number;
  suggestions?: string[];
}

export interface SpecialtyInfo {
  value: MedicalSpecialty;
  label: string;
  template_count: number;
}

// ============ Quality Types ============

export type QualityScoreLevel = "excellent" | "good" | "fair" | "needs_improvement";

export interface QualityCategoryScore {
  score: number;
  max_score: number;
  items_found: string[];
  items_missing: string[];
}

export interface QualityFinding {
  category: string;
  element: string;
  status: "present" | "missing" | "insufficient";
  detail: string;
  suggestion: string;
}

export interface QualityScore {
  id: string;
  clinical_note: string;
  encounter: string;
  overall_score: number;
  score_level: QualityScoreLevel;
  category_scores: Record<string, QualityCategoryScore>;
  findings: QualityFinding[];
  suggestions: string[];
  em_level_suggested: string;
  em_level_documented: string;
  rules_version: string;
  scored_at: string;
  updated_at: string;
}
```

### 7.3 API Client Additions (`web/src/lib/api-client.ts`)

Add these to the `apiClient` object:

```typescript
templates: {
  list: (params?: Record<string, string>) =>
    http.get<PaginatedResponse<NoteTemplateListItem>>("/templates/", { params }).then(r => r.data),
  get: (id: string) =>
    http.get<NoteTemplate>(`/templates/${id}/`).then(r => r.data),
  create: (data: CreateTemplateRequest) =>
    http.post<NoteTemplate>("/templates/", data).then(r => r.data),
  update: (id: string, data: Partial<CreateTemplateRequest>) =>
    http.patch<NoteTemplate>(`/templates/${id}/`, data).then(r => r.data),
  delete: (id: string) =>
    http.delete(`/templates/${id}/`).then(r => r.data),
  clone: (id: string, name?: string) =>
    http.post<NoteTemplate>(`/templates/${id}/clone/`, { name }).then(r => r.data),
  rate: (id: string, score: number, review?: string) =>
    http.post<TemplateRating>(`/templates/${id}/rate/`, { score, review, template: id }).then(r => r.data),
  favorite: (id: string) =>
    http.post(`/templates/${id}/favorite/`).then(r => r.data),
  unfavorite: (id: string) =>
    http.delete(`/templates/${id}/favorite/`).then(r => r.data),
  autoComplete: (id: string, data: AutoCompleteRequest) =>
    http.post<AutoCompleteResponse>(`/templates/${id}/auto-complete/`, data).then(r => r.data),
  specialties: () =>
    http.get<SpecialtyInfo[]>("/templates/specialties/").then(r => r.data),
  favorites: () =>
    http.get<NoteTemplateListItem[]>("/templates/favorites/").then(r => r.data),
},

quality: {
  get: (encounterId: string) =>
    http.get<QualityScore>(`/encounters/${encounterId}/quality/`).then(r => r.data),
  trigger: (encounterId: string) =>
    http.post<{ status: string; encounter_id: string }>(`/encounters/${encounterId}/quality/score/`).then(r => r.data),
},
```

### 7.4 Sidebar Update

Add to `navItems` in `web/src/components/shared/sidebar.tsx`:

```typescript
import { LayoutTemplate } from "lucide-react";  // Add import

// Add to navItems array:
{ href: "/templates", label: "Templates", icon: LayoutTemplate },
```

---

## 8. Web Dashboard: Quality Score Integration

### 8.1 Quality Score on Encounter Detail

Add a quality score card to `EncounterDetail` that displays when a note has been scored. Hooks pattern follows the existing `useNote`/`useSummary` pattern.

### 8.2 Auto-trigger Quality Scoring

Modify the existing `workers/soap_note.py` to trigger quality scoring after SOAP note generation (before summary generation):

```python
# In generate_soap_note_task, after creating the ClinicalNote:
from workers.quality_checker import quality_check_task
quality_check_task.delay(encounter_id)
```

---

## 9. Configuration & Settings Updates

### 9.1 `config/settings/base.py` Changes

```python
INSTALLED_APPS = [
    # ... existing apps ...
    # Local apps
    "apps.accounts",
    "apps.patients",
    "apps.encounters",
    "apps.notes",
    "apps.summaries",
    "apps.widget",
    "apps.audit",
    "apps.realtime",
    "apps.templates",  # NEW
    "apps.quality",    # NEW
]
```

### 9.2 `requirements.txt` Additions

No new Python packages required. All dependencies (DRF, django-filter, Celery, anthropic) are already present.

### 9.3 HIPAA Audit Middleware Update

Add template and quality URLs to `PHI_URL_PATTERNS` in `apps/audit/middleware.py`:

```python
(re.compile(r"^/api/v1/templates/"), "template", None),
(re.compile(r"^/api/v1/encounters/[0-9a-f-]+/quality/?"), "quality_score", None),
```

Also add `"template"` and `"quality_score"` to `AuditLog.ResourceType.choices`.

---

## 10. Implementation Steps (Ordered)

Each step is a TDD unit of work. Tests first, then implementation.

### Step 1: Create `apps/templates/` Django App (Backend)

**Files to create:**
1. `backend/apps/templates/__init__.py`
2. `backend/apps/templates/apps.py` -- AppConfig with label `note_templates`
3. `backend/apps/templates/models.py` -- NoteTemplate, TemplateRating, TemplateFavorite
4. `backend/apps/templates/admin.py`
5. `backend/apps/templates/tests/__init__.py`
6. `backend/apps/templates/tests/test_models.py`

**Tests to write first:**
- `test_create_note_template` -- create template, verify fields
- `test_template_schema_json_field` -- verify JSON schema storage/retrieval
- `test_template_rating_unique_per_user` -- verify unique constraint
- `test_template_favorite_toggle`
- `test_template_version_tracking`

**Then:** Run `python manage.py makemigrations note_templates && python manage.py migrate`

### Step 2: Template Serializers and Filters (Backend)

**Files to create:**
1. `backend/apps/templates/serializers.py`
2. `backend/apps/templates/filters.py`
3. `backend/apps/templates/tests/test_serializers.py`
4. `backend/apps/templates/tests/test_filters.py`

**Tests to write first:**
- `test_template_list_serializer_fields`
- `test_template_detail_serializer_includes_schema`
- `test_template_create_serializer_sets_created_by`
- `test_specialty_filter`
- `test_search_filter`
- `test_tag_filter`

### Step 3: Template ViewSet and URLs (Backend)

**Files to create:**
1. `backend/apps/templates/views.py`
2. `backend/apps/templates/urls.py`
3. `backend/apps/templates/tests/test_views.py`

**Files to modify:**
1. `backend/config/urls.py` -- add templates URL include
2. `backend/config/settings/base.py` -- add `apps.templates` to INSTALLED_APPS

**Tests to write first:**
- `test_list_templates_returns_own_and_public`
- `test_create_template`
- `test_update_own_template`
- `test_delete_own_template`
- `test_cannot_delete_others_template`
- `test_clone_template`
- `test_rate_template`
- `test_toggle_favorite`
- `test_list_specialties`
- `test_marketplace_scope_filter`
- `test_list_favorites`

### Step 4: Specialty Configuration Seed Data (Backend)

**Files to create:**
1. `backend/apps/templates/specialty_configs.py`
2. `backend/apps/templates/management/__init__.py`
3. `backend/apps/templates/management/commands/__init__.py`
4. `backend/apps/templates/management/commands/seed_templates.py`
5. `backend/apps/templates/tests/test_specialty_configs.py`

**Tests to write first:**
- `test_primary_care_templates_have_required_schema`
- `test_dermatology_templates_have_abcde_fields`
- `test_psychiatry_templates_have_mse_fields`
- `test_seed_command_creates_templates`

### Step 5: Template LLM Service (Backend)

**Files to create:**
1. `backend/services/template_llm_service.py`
2. `backend/prompts/template_auto_complete.py`
3. `backend/services/tests/test_template_llm_service.py`

**Tests to write first (mock Claude API):**
- `test_auto_complete_section_returns_content`
- `test_auto_complete_uses_specialty_context`
- `test_auto_complete_handles_partial_content`
- `test_auto_complete_handles_api_error`

### Step 6: Template Auto-Complete Endpoint (Backend)

**Modify:** `backend/apps/templates/views.py` -- add `auto_complete` action (already in Step 3 viewset, but wire up the service)

**Tests to write first:**
- `test_auto_complete_endpoint_calls_llm_service`
- `test_auto_complete_increments_use_count`
- `test_auto_complete_requires_auth`

### Step 7: Create `apps/quality/` Django App (Backend)

**Files to create:**
1. `backend/apps/quality/__init__.py`
2. `backend/apps/quality/apps.py`
3. `backend/apps/quality/models.py`
4. `backend/apps/quality/admin.py`
5. `backend/apps/quality/tests/__init__.py`
6. `backend/apps/quality/tests/test_models.py`

**Tests to write first:**
- `test_create_quality_score`
- `test_quality_score_level_choices`
- `test_quality_score_one_per_encounter`

**Then:** `python manage.py makemigrations quality && python manage.py migrate`

### Step 8: Quality Rules Engine (Backend)

**Files to create:**
1. `backend/apps/quality/rules_engine.py`
2. `backend/apps/quality/tests/test_rules_engine.py`

**Tests to write first:**
- `test_score_note_with_complete_soap` -- score >= 80%
- `test_score_note_with_minimal_content` -- score < 50%
- `test_hpi_elements_detection`
- `test_ros_detection`
- `test_exam_systems_detection`
- `test_mdm_scoring`
- `test_coding_accuracy_scoring`
- `test_em_level_determination`
- `test_suggestions_generated_for_missing_elements`

### Step 9: Quality Checker Worker (Backend)

**Files to create:**
1. `backend/workers/quality_checker.py`
2. `backend/workers/tests/test_quality_checker.py`

**Files to modify:**
1. `backend/config/celery.py` -- add quality queue route
2. `backend/config/settings/base.py` -- add `apps.quality` to INSTALLED_APPS

**Tests to write first:**
- `test_quality_check_task_creates_score`
- `test_quality_check_task_handles_missing_note`
- `test_quality_check_task_retries_on_error`
- `test_quality_check_sends_ws_update`

### Step 10: Quality Score API Endpoints (Backend)

**Files to create:**
1. `backend/apps/quality/serializers.py`
2. `backend/apps/quality/views.py`
3. `backend/apps/quality/urls.py`
4. `backend/apps/quality/tests/test_views.py`

**Files to modify:**
1. `backend/config/urls.py` -- add quality URL include

**Tests to write first:**
- `test_get_quality_score`
- `test_trigger_quality_score`
- `test_quality_score_404_when_no_note`
- `test_quality_score_requires_same_practice`

### Step 11: Auto-trigger Quality Scoring in Pipeline (Backend)

**Files to modify:**
1. `backend/workers/soap_note.py` -- dispatch `quality_check_task` after note creation

**Tests to write first:**
- `test_soap_note_task_triggers_quality_check`

### Step 12: Encounter Model Update (Backend)

**Files to modify:**
1. `backend/apps/encounters/models.py` -- add `template_used` FK
2. `backend/apps/encounters/serializers.py` -- add `template_used` to serializers

**Then:** `python manage.py makemigrations encounters && python manage.py migrate`

**Tests:**
- `test_encounter_with_template_reference`

### Step 13: HIPAA Audit Updates (Backend)

**Files to modify:**
1. `backend/apps/audit/middleware.py` -- add template/quality URL patterns
2. `backend/apps/audit/models.py` -- extend ResourceType choices

### Step 14: Frontend TypeScript Types (Web)

**Files to modify:**
1. `web/src/types/index.ts` -- add all Template, Quality, and Specialty types

### Step 15: Frontend API Client (Web)

**Files to modify:**
1. `web/src/lib/api-client.ts` -- add `templates` and `quality` API sections
2. `web/src/lib/api-client.test.ts` -- add tests for new API methods

### Step 16: Frontend Template Hooks (Web)

**Files to create:**
1. `web/src/hooks/use-templates.ts`
2. `web/src/hooks/use-templates.test.ts`
3. `web/src/hooks/use-quality.ts`
4. `web/src/hooks/use-quality.test.ts`

### Step 17: Frontend Sidebar Update (Web)

**Files to modify:**
1. `web/src/components/shared/sidebar.tsx` -- add Templates nav item

### Step 18: Template Card Component (Web)

**Files to create:**
1. `web/src/components/templates/template-card.tsx`
2. `web/src/components/templates/rating-stars.tsx`
3. `web/src/components/templates/specialty-filter.tsx`

### Step 19: Templates List/Browse Page (Web)

**Files to create:**
1. `web/src/app/(dashboard)/templates/page.tsx`
2. `web/src/app/(dashboard)/templates/templates-list.tsx`

Features: My Templates tab, Marketplace tab, specialty filters, search, sort by rating/usage.

### Step 20: Template Detail Page (Web)

**Files to create:**
1. `web/src/app/(dashboard)/templates/[id]/page.tsx`
2. `web/src/app/(dashboard)/templates/[id]/template-detail.tsx`

Features: View schema, clone, rate, favorite, preview, edit (if own).

### Step 21: Create/Edit Template Pages (Web)

**Files to create:**
1. `web/src/app/(dashboard)/templates/new/page.tsx`
2. `web/src/app/(dashboard)/templates/new/new-template-form.tsx`
3. `web/src/app/(dashboard)/templates/edit/[id]/page.tsx`
4. `web/src/app/(dashboard)/templates/edit/[id]/edit-template-form.tsx`
5. `web/src/components/templates/template-schema-builder.tsx`

### Step 22: Template Section Form with AI Auto-Complete (Web)

**Files to create:**
1. `web/src/components/templates/template-section-form.tsx`

Features: Render fields from schema, AI auto-complete button per field, loading states.

### Step 23: Quality Score Components (Web)

**Files to create:**
1. `web/src/components/quality/quality-score-badge.tsx`
2. `web/src/components/quality/quality-score-detail.tsx`

### Step 24: Quality Score in Encounter Detail (Web)

**Files to modify:**
1. `web/src/app/(dashboard)/encounters/[id]/encounter-detail.tsx` -- add QualityScoreDetail card

### Step 25: "Use Template" Flow in New Encounter (Web)

**Files to modify:**
1. `web/src/app/(dashboard)/encounters/new/new-encounter-form.tsx` -- add template selector step before input method

Flow: Select patient -> Select template (optional) -> Choose input method -> AI fills template sections from transcript

### Step 26: Integration Tests (Backend)

**Files to create/modify:**
1. `backend/tests/test_integration.py` -- add template + quality integration test

**Test:**
- `test_full_flow_with_template_and_quality_score` -- create encounter with template, paste text, verify SOAP note generated with template context, verify quality score auto-generated

### Step 27: Frontend Constants Update (Web)

**Files to modify:**
1. `web/src/lib/constants.ts` -- add specialty labels, quality score level labels

---

## Appendix A: Database Migration Sequence

```
1. python manage.py makemigrations note_templates  # Creates NoteTemplate, TemplateRating, TemplateFavorite
2. python manage.py makemigrations quality          # Creates QualityScore
3. python manage.py makemigrations encounters       # Adds template_used FK
4. python manage.py migrate                         # Apply all
5. python manage.py seed_templates                  # Load specialty template packs
```

## Appendix B: Celery Queue Configuration

```
Existing queues: transcription, soap_note, summary, ocr
New queue: quality

Worker command: celery -A config worker -Q quality -l info --concurrency=2
```

## Appendix C: Test Fixture Summary

All tests follow the pattern established in Phase 1:
- Use `django.test.TestCase` for unit/integration tests
- Use `rest_framework.test.APIClient` with `force_authenticate` for API tests
- Mock LLM service with `unittest.mock.patch`
- Create Practice, User (doctor), Patient, Encounter fixtures in setUp
- Use `@pytest.mark.slow` for tests that hit real services

---

### Critical Files for Implementation
- `/Users/yemalin.godonou/Documents/works/tiko/medicalnote/backend/apps/encounters/models.py` - Must add `template_used` FK; central model that connects to templates and quality scoring
- `/Users/yemalin.godonou/Documents/works/tiko/medicalnote/backend/services/llm_service.py` - Pattern to follow for `template_llm_service.py`; contains Claude API wrapper conventions
- `/Users/yemalin.godonou/Documents/works/tiko/medicalnote/backend/workers/soap_note.py` - Must modify to auto-trigger quality scoring; pattern to follow for `quality_checker.py` worker
- `/Users/yemalin.godonou/Documents/works/tiko/medicalnote/backend/config/settings/base.py` - Must add new apps to INSTALLED_APPS; contains Celery, DRF, and middleware configuration
- `/Users/yemalin.godonou/Documents/works/tiko/medicalnote/web/src/lib/api-client.ts` - Must add templates and quality API methods; defines the full API client pattern to follow
