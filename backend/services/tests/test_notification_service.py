from unittest.mock import MagicMock, patch
from django.test import TestCase
from services.notification_service import NotificationService


class NotificationServiceTest(TestCase):
    @patch("services.notification_service.Client")
    def test_send_sms(self, mock_twilio_cls):
        mock_client = MagicMock()
        mock_twilio_cls.return_value = mock_client
        service = NotificationService()
        service.send_sms("+15551234567", "Test message")
        mock_client.messages.create.assert_called_once()
