from django.core.management.base import BaseCommand

from apps.telehealth.models import StateComplianceRule

# Telehealth compliance rules for all 50 states + DC
# Sources: Interstate Medical Licensure Compact, state telehealth statutes
# Recording consent: two_party states include CA, CT, FL, IL, MA, MD, MT, NH, OR, PA, WA
STATE_RULES = [
    {"state_code": "AL", "state_name": "Alabama", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "AK", "state_name": "Alaska", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": False},
    {"state_code": "AZ", "state_name": "Arizona", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "AR", "state_name": "Arkansas", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "CA", "state_name": "California", "consent_type": "verbal", "consent_statute": "Cal. Bus. & Prof. Code 2290.5", "recording_consent": "two_party", "interstate_compact": False},
    {"state_code": "CO", "state_name": "Colorado", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "CT", "state_name": "Connecticut", "consent_type": "verbal", "recording_consent": "two_party", "interstate_compact": False},
    {"state_code": "DE", "state_name": "Delaware", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "DC", "state_name": "District of Columbia", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "FL", "state_name": "Florida", "consent_type": "verbal", "consent_statute": "FL Stat. 456.47", "recording_consent": "two_party", "interstate_compact": True, "prescribing_restrictions": "No controlled substances via telehealth without prior in-person visit"},
    {"state_code": "GA", "state_name": "Georgia", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "HI", "state_name": "Hawaii", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": False},
    {"state_code": "ID", "state_name": "Idaho", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "IL", "state_name": "Illinois", "consent_type": "verbal", "recording_consent": "two_party", "interstate_compact": True},
    {"state_code": "IN", "state_name": "Indiana", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "IA", "state_name": "Iowa", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "KS", "state_name": "Kansas", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "KY", "state_name": "Kentucky", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "LA", "state_name": "Louisiana", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "ME", "state_name": "Maine", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "MD", "state_name": "Maryland", "consent_type": "verbal", "recording_consent": "two_party", "interstate_compact": True},
    {"state_code": "MA", "state_name": "Massachusetts", "consent_type": "written", "recording_consent": "two_party", "interstate_compact": False},
    {"state_code": "MI", "state_name": "Michigan", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "MN", "state_name": "Minnesota", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "MS", "state_name": "Mississippi", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "MO", "state_name": "Missouri", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "MT", "state_name": "Montana", "consent_type": "verbal", "recording_consent": "two_party", "interstate_compact": True},
    {"state_code": "NE", "state_name": "Nebraska", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "NV", "state_name": "Nevada", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "NH", "state_name": "New Hampshire", "consent_type": "verbal", "recording_consent": "two_party", "interstate_compact": True},
    {"state_code": "NJ", "state_name": "New Jersey", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "NM", "state_name": "New Mexico", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "NY", "state_name": "New York", "consent_type": "written", "consent_statute": "NY PHL 2999-cc", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "NC", "state_name": "North Carolina", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "ND", "state_name": "North Dakota", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "OH", "state_name": "Ohio", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "OK", "state_name": "Oklahoma", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "OR", "state_name": "Oregon", "consent_type": "verbal", "recording_consent": "two_party", "interstate_compact": False},
    {"state_code": "PA", "state_name": "Pennsylvania", "consent_type": "verbal", "recording_consent": "two_party", "interstate_compact": True},
    {"state_code": "RI", "state_name": "Rhode Island", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": False},
    {"state_code": "SC", "state_name": "South Carolina", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "SD", "state_name": "South Dakota", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "TN", "state_name": "Tennessee", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "TX", "state_name": "Texas", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "UT", "state_name": "Utah", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "VT", "state_name": "Vermont", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "VA", "state_name": "Virginia", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "WA", "state_name": "Washington", "consent_type": "verbal", "recording_consent": "two_party", "interstate_compact": True},
    {"state_code": "WV", "state_name": "West Virginia", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "WI", "state_name": "Wisconsin", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
    {"state_code": "WY", "state_name": "Wyoming", "consent_type": "verbal", "recording_consent": "one_party", "interstate_compact": True},
]


class Command(BaseCommand):
    help = "Seed initial state telehealth compliance rules for all 50 states + DC"

    def handle(self, *args, **options):
        created_count = 0
        for rule_data in STATE_RULES:
            _, created = StateComplianceRule.objects.update_or_create(
                state_code=rule_data["state_code"],
                defaults={
                    "state_name": rule_data.get("state_name", ""),
                    "consent_type": rule_data.get("consent_type", "verbal"),
                    "consent_required": True,
                    "consent_statute": rule_data.get("consent_statute", ""),
                    "recording_consent": rule_data.get(
                        "recording_consent", "one_party"
                    ),
                    "prescribing_restrictions": rule_data.get(
                        "prescribing_restrictions", ""
                    ),
                    "interstate_compact": rule_data.get(
                        "interstate_compact", False
                    ),
                    "medicaid_coverage": True,
                    "is_active": True,
                },
            )
            if created:
                created_count += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created_count} new state rules "
                f"({len(STATE_RULES)} total)"
            )
        )
