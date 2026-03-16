from rest_framework import serializers

from apps.quality.models import QualityFinding, QualityRule, QualityScore


class QualityRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualityRule
        fields = [
            "id",
            "rule_code",
            "name",
            "description",
            "category",
            "severity",
            "points",
            "is_active",
        ]
        read_only_fields = fields


class QualityFindingSerializer(serializers.ModelSerializer):
    rule = QualityRuleSerializer(read_only=True)

    class Meta:
        model = QualityFinding
        fields = [
            "id",
            "rule",
            "passed",
            "message",
            "details",
            "created_at",
        ]
        read_only_fields = fields


class QualityScoreSerializer(serializers.ModelSerializer):
    findings = QualityFindingSerializer(many=True, read_only=True)

    class Meta:
        model = QualityScore
        fields = [
            "id",
            "encounter",
            "clinical_note",
            "overall_score",
            "completeness_score",
            "billing_score",
            "compliance_score",
            "suggested_em_level",
            "suggestions",
            "findings",
            "evaluated_at",
            "created_at",
        ]
        read_only_fields = fields
