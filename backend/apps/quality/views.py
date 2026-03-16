from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.permissions import IsDoctorOrAdmin
from apps.encounters.models import Encounter
from apps.quality.models import QualityScore
from apps.quality.serializers import QualityScoreSerializer


@api_view(["GET"])
@permission_classes([IsDoctorOrAdmin])
def encounter_quality(request, encounter_id):
    """Get the quality score for an encounter."""
    try:
        encounter = Encounter.objects.get(
            id=encounter_id,
            doctor__practice=request.user.practice,
        )
    except Encounter.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    try:
        score = encounter.quality_score
    except QualityScore.DoesNotExist:
        return Response(
            {"error": "No quality score available."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = QualityScoreSerializer(score)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsDoctorOrAdmin])
def recheck_quality(request, encounter_id):
    """Trigger a quality re-check for an encounter."""
    try:
        encounter = Encounter.objects.get(
            id=encounter_id,
            doctor__practice=request.user.practice,
        )
    except Encounter.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if not hasattr(encounter, "clinical_note"):
        return Response(
            {"error": "No clinical note to evaluate."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from workers.quality_checker import quality_checker_task

    quality_checker_task.delay(str(encounter.id))

    return Response(
        {"status": "rechecking", "encounter_id": str(encounter.id)},
        status=status.HTTP_202_ACCEPTED,
    )
