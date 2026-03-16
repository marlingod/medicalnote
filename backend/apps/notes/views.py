from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.permissions import IsDoctorOrAdmin
from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote
from apps.notes.serializers import ClinicalNoteSerializer


@api_view(["GET", "PATCH"])
@permission_classes([IsDoctorOrAdmin])
def encounter_note(request, encounter_id):
    try:
        encounter = Encounter.objects.get(
            id=encounter_id,
            doctor__practice=request.user.practice,
        )
    except Encounter.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    try:
        note = encounter.clinical_note
    except ClinicalNote.DoesNotExist:
        return Response(
            {"error": "No note available for this encounter."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        serializer = ClinicalNoteSerializer(note)
        return Response(serializer.data)

    if request.method == "PATCH":
        serializer = ClinicalNoteSerializer(note, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsDoctorOrAdmin])
def approve_note(request, encounter_id):
    try:
        encounter = Encounter.objects.get(
            id=encounter_id,
            doctor__practice=request.user.practice,
        )
    except Encounter.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    try:
        note = encounter.clinical_note
    except ClinicalNote.DoesNotExist:
        return Response(
            {"error": "No note available for this encounter."},
            status=status.HTTP_404_NOT_FOUND,
        )

    note.approved_at = timezone.now()
    note.approved_by = request.user
    note.save(update_fields=["approved_at", "approved_by", "updated_at"])

    encounter.status = Encounter.Status.APPROVED
    encounter.save(update_fields=["status", "updated_at"])

    serializer = ClinicalNoteSerializer(note)
    return Response(serializer.data)
