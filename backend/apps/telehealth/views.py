from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.permissions import IsDoctorOrAdmin
from apps.encounters.models import Encounter
from apps.telehealth.models import StateComplianceRule, TelehealthEncounter
from apps.telehealth.serializers import (
    ComplianceCheckSerializer,
    StateComplianceRuleSerializer,
    TelehealthEncounterCreateSerializer,
    TelehealthEncounterSerializer,
)
from services.compliance_service import ComplianceService


@api_view(["GET", "POST"])
@permission_classes([IsDoctorOrAdmin])
def encounter_telehealth(request, encounter_id):
    try:
        encounter = Encounter.objects.get(
            id=encounter_id,
            doctor__practice=request.user.practice,
        )
    except Encounter.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        try:
            telehealth = encounter.telehealth
        except TelehealthEncounter.DoesNotExist:
            return Response(
                {"error": "No telehealth data for this encounter."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = TelehealthEncounterSerializer(telehealth)
        return Response(serializer.data)

    if request.method == "POST":
        data = request.data.copy()
        data["encounter"] = str(encounter.id)
        serializer = TelehealthEncounterCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            TelehealthEncounterSerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED,
        )


@api_view(["PATCH"])
@permission_classes([IsDoctorOrAdmin])
def update_telehealth(request, encounter_id):
    try:
        encounter = Encounter.objects.get(
            id=encounter_id,
            doctor__practice=request.user.practice,
        )
    except Encounter.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    try:
        telehealth = encounter.telehealth
    except TelehealthEncounter.DoesNotExist:
        return Response(
            {"error": "No telehealth data for this encounter."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = TelehealthEncounterSerializer(
        telehealth, data=request.data, partial=True
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsDoctorOrAdmin])
def check_compliance(request):
    """Pre-check compliance before creating a telehealth encounter."""
    serializer = ComplianceCheckSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    service = ComplianceService()
    report = service.generate_compliance_report(
        patient_state=serializer.validated_data["patient_state"],
        provider_state=serializer.validated_data["provider_state"],
        patient_setting=serializer.validated_data["patient_setting"],
        modality=serializer.validated_data["modality"],
    )
    return Response(report)


@api_view(["GET"])
@permission_classes([IsDoctorOrAdmin])
def list_state_rules(request):
    """List all active state compliance rules."""
    rules = StateComplianceRule.objects.filter(is_active=True)
    serializer = StateComplianceRuleSerializer(rules, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsDoctorOrAdmin])
def get_state_rule(request, state_code):
    """Get compliance rules for a specific state."""
    try:
        rule = StateComplianceRule.objects.get(
            state_code=state_code.upper(), is_active=True
        )
    except StateComplianceRule.DoesNotExist:
        return Response(
            {"error": f"No compliance rules found for state {state_code}."},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = StateComplianceRuleSerializer(rule)
    return Response(serializer.data)
