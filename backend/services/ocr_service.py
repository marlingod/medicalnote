import logging
import boto3
from django.conf import settings

logger = logging.getLogger(__name__)


class OCRService:
    def __init__(self):
        self.client = boto3.client("textract", region_name=settings.AWS_REGION)

    def extract_text_from_s3(self, s3_uri: str) -> str:
        parts = s3_uri.replace("s3://", "").split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        try:
            response = self.client.detect_document_text(
                Document={"S3Object": {"Bucket": bucket, "Name": key}}
            )
            lines = [
                block["Text"]
                for block in response.get("Blocks", [])
                if block["BlockType"] == "LINE"
            ]
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"OCR failed for {s3_uri}: {e}")
            raise
