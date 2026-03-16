import sys
from unittest.mock import MagicMock, patch

from django.test import TestCase

from services.notification_service import NotificationService


class NotificationServiceSMSTest(TestCase):
    @patch("services.notification_service.Client")
    def test_send_sms(self, mock_twilio_cls):
        mock_client = MagicMock()
        mock_twilio_cls.return_value = mock_client
        service = NotificationService()
        service.send_sms("+15551234567", "Test message")
        mock_client.messages.create.assert_called_once()


class NotificationServicePushTest(TestCase):
    def setUp(self):
        # Reset firebase initialization state between tests
        import services.notification_service as ns
        ns._firebase_initialized = False

    @patch("services.notification_service._initialize_firebase")
    @patch("services.notification_service._firebase_initialized", True)
    @patch("services.notification_service.Client")
    def test_send_push_notification(self, mock_twilio_cls, mock_init):
        mock_messaging = MagicMock()
        mock_messaging.send.return_value = "projects/test/messages/123"

        # Patch the firebase_admin.messaging submodule in sys.modules
        # so that `from firebase_admin import messaging` picks up our mock.
        original = sys.modules.get("firebase_admin.messaging")
        sys.modules["firebase_admin.messaging"] = mock_messaging
        try:
            service = NotificationService()
            service.send_push_notification(
                device_token="fcm-token-abc",
                title="Test Title",
                body="Test Body",
                data={"key": "value"},
            )
            mock_messaging.Notification.assert_called_once_with(title="Test Title", body="Test Body")
            mock_messaging.Message.assert_called_once()
            mock_messaging.send.assert_called_once()
        finally:
            if original is not None:
                sys.modules["firebase_admin.messaging"] = original
            else:
                sys.modules.pop("firebase_admin.messaging", None)

    @patch("services.notification_service._initialize_firebase")
    @patch("services.notification_service._firebase_initialized", True)
    @patch("services.notification_service.Client")
    def test_send_push_notification_with_empty_data(self, mock_twilio_cls, mock_init):
        mock_messaging = MagicMock()
        mock_messaging.send.return_value = "projects/test/messages/456"

        original = sys.modules.get("firebase_admin.messaging")
        sys.modules["firebase_admin.messaging"] = mock_messaging
        try:
            service = NotificationService()
            service.send_push_notification(
                device_token="fcm-token-abc",
                title="Title",
                body="Body",
            )
            call_kwargs = mock_messaging.Message.call_args
            assert call_kwargs[1]["data"] == {}
        finally:
            if original is not None:
                sys.modules["firebase_admin.messaging"] = original
            else:
                sys.modules.pop("firebase_admin.messaging", None)

    @patch("services.notification_service._initialize_firebase")
    @patch("services.notification_service._firebase_initialized", False)
    @patch("services.notification_service.Client")
    def test_send_push_skipped_when_firebase_not_initialized(self, mock_twilio_cls, mock_init):
        service = NotificationService()
        # Should not raise, just log warning
        service.send_push_notification(
            device_token="fcm-token-abc",
            title="Title",
            body="Body",
        )

    @patch("services.notification_service._initialize_firebase")
    @patch("services.notification_service._firebase_initialized", True)
    @patch("services.notification_service.Client")
    def test_send_push_notification_raises_on_failure(self, mock_twilio_cls, mock_init):
        mock_messaging = MagicMock()
        mock_messaging.send.side_effect = Exception("FCM error")

        original = sys.modules.get("firebase_admin.messaging")
        sys.modules["firebase_admin.messaging"] = mock_messaging
        try:
            service = NotificationService()
            with self.assertRaises(Exception):
                service.send_push_notification(
                    device_token="fcm-token-abc",
                    title="Title",
                    body="Body",
                )
        finally:
            if original is not None:
                sys.modules["firebase_admin.messaging"] = original
            else:
                sys.modules.pop("firebase_admin.messaging", None)
