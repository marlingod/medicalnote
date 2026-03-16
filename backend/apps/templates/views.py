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
        serializer = TemplateRatingSerializer(
            data={**request.data, "template": template.id}, context={"request": request}
        )
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
