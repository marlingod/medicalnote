import json
from unittest.mock import MagicMock, patch
from channels.testing import WebsocketCommunicator
from django.test import TestCase
from apps.realtime.consumers import JobStatusConsumer


class JobStatusConsumerTest(TestCase):
    async def test_connect_and_receive_status(self):
        communicator = WebsocketCommunicator(
            JobStatusConsumer.as_asgi(),
            "/api/v1/ws/jobs/test-encounter-id/",
        )
        communicator.scope["url_route"] = {
            "kwargs": {"encounter_id": "test-encounter-id"}
        }
        communicator.scope["user"] = MagicMock(is_authenticated=True, id="user-1")

        connected, _ = await communicator.connect()
        assert connected

        # Simulate sending a status update from the channel layer
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            "encounter_test-encounter-id",
            {
                "type": "job_status_update",
                "status": "generating_note",
                "encounter_id": "test-encounter-id",
            },
        )

        response = await communicator.receive_json_from()
        assert response["status"] == "generating_note"

        await communicator.disconnect()
