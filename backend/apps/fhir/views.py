from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.permissions import IsDoctorOrAdmin
from apps.encounters.models import Encounter
from apps.fhir.models import FHIRConnection, FHIRPushLog
from apps.fhir.serializers import (
    FHIRConnectionCreateSerializer,
    FHIRConnectionSerializer,
    FHIRPushLogSerializer,
)
from apps.notes.models import ClinicalNote


class FHIRConnectionViewSet(viewsets.ModelViewSet):
    serializer_class = FHIRConnectionSerializer
    permission_classes = [IsDoctorOrAdmin]

    def get_queryset(self):
        return FHIRConnection.objects.filter(
            practice=self.request.user.practice
        )

    def get_serializer_class(self):
        if self.action == "create":
            return FHIRConnectionCreateSerializer
        return FHIRConnectionSerializer

    @action(detail=True, methods=["post"], url_path="test")
    def test_connection(self, request, pk=None):
        connection = self.get_object()
        from services.fhir_service import FHIRService

        service = FHIRService(connection)
        try:
            service._get_access_token()
            connection.connection_status = "connected"
            connection.save(
                update_fields=["connection_status", "updated_at"]
            )
            return Response(
                {"status": "connected", "message": "Connection successful"}
            )
        except Exception as e:
            connection.connection_status = "error"
            connection.save(
                update_fields=["connection_status", "updated_at"]
            )
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        connection = self.get_object()
        connection.is_active = True
        connection.save(update_fields=["is_active", "updated_at"])
        return Response(FHIRConnectionSerializer(connection).data)

    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, pk=None):
        connection = self.get_object()
        connection.is_active = False
        connection.save(update_fields=["is_active", "updated_at"])
        return Response(FHIRConnectionSerializer(connection).data)


@api_view(["POST"])
@permission_classes([IsDoctorOrAdmin])
def push_note_to_ehr(request, encounter_id):
    """Push an approved clinical note to the connected EHR."""
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
            {"error": "No clinical note."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not note.approved_at:
        return Response(
            {"error": "Note must be approved before pushing to EHR."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    connection = FHIRConnection.objects.filter(
        practice=request.user.practice, is_active=True
    ).first()
    if not connection:
        return Response(
            {"error": "No active FHIR connection."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from services.fhir_service import FHIRService

    service = FHIRService(connection)
    result = service.push_note_to_ehr(note, encounter)
    return Response(
        result,
        status=(
            status.HTTP_200_OK
            if result["status"] == "success"
            else status.HTTP_502_BAD_GATEWAY
        ),
    )


@api_view(["GET"])
@permission_classes([IsDoctorOrAdmin])
def encounter_push_logs(request, encounter_id):
    """Get FHIR push logs for an encounter."""
    try:
        encounter = Encounter.objects.get(
            id=encounter_id,
            doctor__practice=request.user.practice,
        )
    except Encounter.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    logs = FHIRPushLog.objects.filter(encounter=encounter)
    serializer = FHIRPushLogSerializer(logs, many=True)
    return Response(serializer.data)
