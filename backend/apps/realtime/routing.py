from django.urls import re_path
from apps.realtime.consumers import JobStatusConsumer

websocket_urlpatterns = [
    re_path(
        r"api/v1/ws/jobs/(?P<encounter_id>[0-9a-f-]+)/$",
        JobStatusConsumer.as_asgi(),
    ),
]
