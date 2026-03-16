from django.urls import path
from rest_framework.routers import DefaultRouter
from apps.encounters.views import EncounterViewSet
from apps.notes.views import encounter_note, approve_note
from apps.summaries.views import encounter_summary, send_summary

router = DefaultRouter()
router.register("", EncounterViewSet, basename="encounter")

urlpatterns = router.urls + [
    path("<uuid:encounter_id>/note/", encounter_note, name="encounter-note"),
    path("<uuid:encounter_id>/note/approve/", approve_note, name="encounter-note-approve"),
    path("<uuid:encounter_id>/summary/", encounter_summary, name="encounter-summary"),
    path("<uuid:encounter_id>/summary/send/", send_summary, name="encounter-summary-send"),
]
