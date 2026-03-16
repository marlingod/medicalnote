import logging

import boto3
from django.conf import settings

logger = logging.getLogger(__name__)


class STTService:
    def __init__(self):
        self.client = boto3.client(
            "transcribe",
            region_name=settings.AWS_REGION,
        )

    def start_transcription(self, s3_uri: str, encounter_id: str) -> dict:
        job_name = f"medicalnote-{encounter_id}"
        try:
            response = self.client.start_medical_scribe_job(
                MedicalScribeJobName=job_name,
                Media={"MediaFileUri": s3_uri},
                OutputBucketName=settings.AWS_S3_BUCKET,
                DataAccessRoleArn=settings.AWS_KMS_KEY_ID,  # Role ARN in production
                Settings={
                    "ShowSpeakerLabels": True,
                    "MaxSpeakerLabels": 2,
                    "ChannelIdentification": False,
                },
            )
            job = response["MedicalScribeJob"]
            return {
                "job_name": job["MedicalScribeJobName"],
                "status": job["MedicalScribeJobStatus"],
            }
        except Exception as e:
            logger.error(f"Failed to start transcription for {encounter_id}: {e}")
            raise

    def get_transcription_result(self, job_name: str) -> dict:
        try:
            response = self.client.get_medical_scribe_job(
                MedicalScribeJobName=job_name
            )
            job = response["MedicalScribeJob"]
            result = {
                "status": job["MedicalScribeJobStatus"],
                "job_name": job_name,
            }
            if job["MedicalScribeJobStatus"] == "COMPLETED":
                output = job.get("MedicalScribeOutput", {})
                result["transcript_uri"] = output.get("TranscriptFileUri", "")
                result["clinical_uri"] = output.get("ClinicalDocumentUri", "")
            elif job["MedicalScribeJobStatus"] == "FAILED":
                result["failure_reason"] = job.get("FailureReason", "Unknown")
            return result
        except Exception as e:
            logger.error(f"Failed to get transcription result for {job_name}: {e}")
            raise
