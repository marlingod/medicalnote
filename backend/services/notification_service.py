import json
import logging
import os

from django.conf import settings
from twilio.rest import Client

logger = logging.getLogger(__name__)

_firebase_initialized = False


def _initialize_firebase():
    """Initialize Firebase Admin SDK from environment credentials."""
    global _firebase_initialized
    if _firebase_initialized:
        return

    import firebase_admin
    from firebase_admin import credentials

    # Try FIREBASE_CREDENTIALS_JSON first (inline JSON), then GOOGLE_APPLICATION_CREDENTIALS (file path)
    creds_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
    if creds_json:
        cred = credentials.Certificate(json.loads(creds_json))
        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        return

    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path:
        cred = credentials.Certificate(creds_path)
        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        return

    logger.warning("No Firebase credentials found. Push notifications will not be sent.")


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
        """Send a push notification via Firebase Cloud Messaging."""
        try:
            _initialize_firebase()
        except Exception as e:
            logger.error(f"Firebase initialization failed: {e}")
            return

        if not _firebase_initialized:
            logger.warning(f"Firebase not initialized. Skipping push to {device_token}: {title}")
            return

        from firebase_admin import messaging

        notification = messaging.Notification(title=title, body=body)
        message = messaging.Message(
            notification=notification,
            token=device_token,
            data=data or {},
        )
        try:
            response = messaging.send(message)
            logger.info(f"Push notification sent successfully: {response}")
        except Exception as e:
            logger.error(f"Push notification failed to {device_token}: {e}")
            raise
