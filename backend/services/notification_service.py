import logging
from django.conf import settings
from twilio.rest import Client

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self):
        self.twilio_client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
        )
        self.from_number = settings.TWILIO_PHONE_NUMBER

    def send_sms(self, to: str, body: str) -> None:
        try:
            self.twilio_client.messages.create(
                to=to, from_=self.from_number, body=body
            )
        except Exception as e:
            logger.error(f"SMS send failed to {to}: {e}")
            raise

    def send_push_notification(self, device_token: str, title: str, body: str, data: dict = None) -> None:
        # FCM integration - placeholder for Phase 1
        # In production, use firebase-admin SDK
        logger.info(f"Push notification to {device_token}: {title}")
