import hashlib
import hmac

from django.conf import settings
from django_filters import rest_framework as filters

from apps.patients.models import Patient


class PatientFilter(filters.FilterSet):
    name = filters.CharFilter(method="filter_by_name")

    class Meta:
        model = Patient
        fields = ["language_preference"]

    def filter_by_name(self, queryset, name, value):
        """Search patients by blind index hash of normalized name."""
        normalized = value.strip().lower()
        search_hash = hmac.new(
            settings.FIELD_ENCRYPTION_KEY.encode(),
            normalized.encode(),
            hashlib.sha256,
        ).hexdigest()
        return queryset.filter(name_search_hash=search_hash)
