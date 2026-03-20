import json
import logging

from celery import shared_task
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class DataExportRequestSerializer(serializers.Serializer):
    patient_id = serializers.UUIDField()
    format = serializers.ChoiceField(choices=["json"], default="json")


class PatientDataExportView(APIView):
    """Patient right of access -- data export (HIPAA 164.524)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DataExportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        patient_id = str(serializer.validated_data["patient_id"])

        # Queue the export task
        export_patient_data.delay(patient_id, str(request.user.id))

        return Response(
            {
                "status": "queued",
                "message": "Data export has been queued. You will be notified when it is ready.",
                "patient_id": patient_id,
            },
            status=status.HTTP_202_ACCEPTED,
        )


@shared_task(name="patients.export_patient_data")
def export_patient_data(patient_id, requesting_user_id):
    """Collect all patient data for export."""
    from apps.patients.models import Patient
    from apps.encounters.models import Encounter, Transcript
    from apps.notes.models import ClinicalNote
    from apps.summaries.models import PatientSummary

    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        logger.error(f"Patient {patient_id} not found for export")
        return {"error": "Patient not found"}

    encounters = Encounter.objects.filter(patient=patient)
    export_data = {
        "patient": {
            "id": str(patient.id),
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "date_of_birth": str(patient.date_of_birth),
            "language_preference": patient.language_preference,
        },
        "encounters": [],
    }

    for encounter in encounters:
        enc_data = {
            "id": str(encounter.id),
            "date": str(encounter.encounter_date),
            "input_method": encounter.input_method,
            "status": encounter.status,
        }

        # Transcript
        try:
            transcript = encounter.transcript
            enc_data["transcript"] = {
                "raw_text": transcript.raw_text,
                "confidence_score": transcript.confidence_score,
                "language_detected": transcript.language_detected,
            }
        except Transcript.DoesNotExist:
            pass

        # Clinical note
        try:
            note = encounter.clinical_note
            enc_data["clinical_note"] = {
                "note_type": note.note_type,
                "subjective": note.subjective,
                "objective": note.objective,
                "assessment": note.assessment,
                "plan": note.plan,
                "icd10_codes": note.icd10_codes,
                "cpt_codes": note.cpt_codes,
            }
        except ClinicalNote.DoesNotExist:
            pass

        # Summary
        try:
            summary = encounter.patient_summary
            enc_data["patient_summary"] = {
                "summary_en": summary.summary_en,
                "summary_es": summary.summary_es,
                "reading_level": summary.reading_level,
                "medical_terms_explained": summary.medical_terms_explained,
            }
        except PatientSummary.DoesNotExist:
            pass

        export_data["encounters"].append(enc_data)

    logger.info(f"Patient data export completed for {patient_id}: {len(export_data['encounters'])} encounters")
    return export_data
