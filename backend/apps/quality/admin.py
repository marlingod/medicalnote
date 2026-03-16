from django.contrib import admin

from apps.quality.models import QualityFinding, QualityRule, QualityScore


@admin.register(QualityRule)
class QualityRuleAdmin(admin.ModelAdmin):
    list_display = [
        "rule_code",
        "name",
        "category",
        "severity",
        "points",
        "is_active",
    ]
    list_filter = ["category", "severity", "is_active"]
    search_fields = ["rule_code", "name"]


@admin.register(QualityScore)
class QualityScoreAdmin(admin.ModelAdmin):
    list_display = [
        "encounter",
        "overall_score",
        "completeness_score",
        "billing_score",
        "compliance_score",
        "suggested_em_level",
        "evaluated_at",
    ]
    list_filter = ["suggested_em_level"]
    readonly_fields = ["suggestions"]


@admin.register(QualityFinding)
class QualityFindingAdmin(admin.ModelAdmin):
    list_display = [
        "quality_score",
        "rule",
        "passed",
        "message",
        "created_at",
    ]
    list_filter = ["passed"]
    readonly_fields = ["details"]
