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
    partial_content = serializers.CharField(required=False, default="")


class CloneTemplateSerializer(serializers.Serializer):
    """Input for cloning a template."""
    name = serializers.CharField(max_length=255, required=False)
