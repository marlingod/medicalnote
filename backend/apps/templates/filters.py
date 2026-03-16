from django.db import models
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
