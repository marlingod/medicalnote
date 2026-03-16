import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("medicalnote")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(["workers"])

app.conf.task_routes = {
    "workers.transcription.*": {"queue": "transcription"},
    "workers.soap_note.*": {"queue": "soap_note"},
    "workers.summary.*": {"queue": "summary"},
    "workers.ocr.*": {"queue": "ocr"},
    "workers.quality_checker.*": {"queue": "quality"},
}

app.conf.task_default_queue = "default"
