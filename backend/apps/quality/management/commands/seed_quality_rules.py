from django.core.management.base import BaseCommand

from apps.quality.models import QualityRule

QUALITY_RULES = [
    {
        "rule_code": "COMP_SUBJ",
        "name": "Subjective section present",
        "description": "Check that subjective section is non-empty and substantive",
        "category": "completeness",
        "severity": "error",
        "points": 15,
    },
    {
        "rule_code": "COMP_OBJ",
        "name": "Objective section present",
        "description": "Check that objective section is non-empty and substantive",
        "category": "completeness",
        "severity": "error",
        "points": 15,
    },
    {
        "rule_code": "COMP_ASSESS",
        "name": "Assessment section present",
        "description": "Check that assessment section is non-empty",
        "category": "completeness",
        "severity": "error",
        "points": 15,
    },
    {
        "rule_code": "COMP_PLAN",
        "name": "Plan section present",
        "description": "Check that plan section is non-empty",
        "category": "completeness",
        "severity": "error",
        "points": 15,
    },
    {
        "rule_code": "COMP_HPI",
        "name": "HPI elements documented",
        "description": (
            "HPI should include location, quality, severity, timing, "
            "context, modifying factors, and associated signs/symptoms"
        ),
        "category": "completeness",
        "severity": "warning",
        "points": 10,
    },
    {
        "rule_code": "COMP_ROS",
        "name": "Review of Systems documented",
        "description": "Review of Systems should cover at least 2 organ systems",
        "category": "completeness",
        "severity": "warning",
        "points": 5,
    },
    {
        "rule_code": "BILL_ICD10",
        "name": "ICD-10 codes present",
        "description": "At least one ICD-10 diagnosis code should be present",
        "category": "billing",
        "severity": "warning",
        "points": 10,
    },
    {
        "rule_code": "BILL_CPT",
        "name": "CPT codes present",
        "description": "At least one CPT procedure code should be present",
        "category": "billing",
        "severity": "warning",
        "points": 5,
    },
    {
        "rule_code": "BILL_EM_MATCH",
        "name": "E/M level matches documentation",
        "description": "Verify E/M code level is supported by documentation",
        "category": "billing",
        "severity": "info",
        "points": 5,
    },
    {
        "rule_code": "CMS_MDM",
        "name": "Medical Decision Making documented",
        "description": "Assessment and plan should demonstrate medical decision making",
        "category": "compliance",
        "severity": "warning",
        "points": 10,
    },
]


class Command(BaseCommand):
    help = "Seed default quality rules"

    def handle(self, *args, **options):
        created_count = 0
        for rule_data in QUALITY_RULES:
            _, created = QualityRule.objects.update_or_create(
                rule_code=rule_data["rule_code"],
                defaults={
                    "name": rule_data["name"],
                    "description": rule_data.get("description", ""),
                    "category": rule_data["category"],
                    "severity": rule_data["severity"],
                    "points": rule_data["points"],
                    "is_active": True,
                },
            )
            if created:
                created_count += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created_count} new quality rules "
                f"({len(QUALITY_RULES)} total)"
            )
        )
