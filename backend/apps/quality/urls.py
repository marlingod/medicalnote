from django.urls import path

from apps.quality.views import encounter_quality, recheck_quality

urlpatterns = [
    path(
        "<uuid:encounter_id>/quality/",
        encounter_quality,
        name="encounter-quality",
    ),
    path(
        "<uuid:encounter_id>/quality/recheck/",
        recheck_quality,
        name="encounter-quality-recheck",
    ),
]
