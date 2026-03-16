from django_filters import rest_framework as filters

from apps.encounters.models import Encounter


class EncounterFilter(filters.FilterSet):
    status = filters.ChoiceFilter(choices=Encounter.Status.choices)
    input_method = filters.ChoiceFilter(choices=Encounter.InputMethod.choices)
    date_from = filters.DateFilter(field_name="encounter_date", lookup_expr="gte")
    date_to = filters.DateFilter(field_name="encounter_date", lookup_expr="lte")
    patient = filters.UUIDFilter(field_name="patient_id")

    class Meta:
        model = Encounter
        fields = ["status", "input_method", "patient"]
