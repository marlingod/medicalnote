import json
import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger(__name__)


class JobStatusConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.encounter_id = self.scope["url_route"]["kwargs"]["encounter_id"]
        self.group_name = f"encounter_{self.encounter_id}"

        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def job_status_update(self, event):
        await self.send_json({
            "type": "status_update",
            "status": event["status"],
            "encounter_id": event["encounter_id"],
        })
