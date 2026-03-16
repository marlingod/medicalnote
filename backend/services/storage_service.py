import logging
import uuid
import boto3
from django.conf import settings

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        self.client = boto3.client("s3", region_name=settings.AWS_REGION)
        self.bucket = settings.AWS_S3_BUCKET

    def upload_audio(self, file_obj, encounter_id: str) -> str:
        ext = file_obj.name.rsplit(".", 1)[-1] if hasattr(file_obj, "name") and "." in file_obj.name else "wav"
        key = f"audio/{encounter_id}/{uuid.uuid4()}.{ext}"
        self.client.upload_fileobj(
            file_obj, self.bucket, key,
            ExtraArgs={"ServerSideEncryption": "aws:kms", "SSEKMSKeyId": settings.AWS_KMS_KEY_ID},
        )
        return f"s3://{self.bucket}/{key}"

    def upload_scan(self, file_obj, encounter_id: str) -> str:
        ext = file_obj.name.rsplit(".", 1)[-1] if hasattr(file_obj, "name") and "." in file_obj.name else "jpg"
        key = f"scans/{encounter_id}/{uuid.uuid4()}.{ext}"
        self.client.upload_fileobj(
            file_obj, self.bucket, key,
            ExtraArgs={"ServerSideEncryption": "aws:kms", "SSEKMSKeyId": settings.AWS_KMS_KEY_ID},
        )
        return f"s3://{self.bucket}/{key}"

    def get_presigned_url(self, s3_uri: str, expiry: int = 3600) -> str:
        parts = s3_uri.replace("s3://", "").split("/", 1)
        bucket, key = parts[0], parts[1]
        return self.client.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expiry
        )
