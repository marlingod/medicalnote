import logging
import re
import uuid

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

PHI_URL_PATTERNS = [
    (re.compile(r"^/api/v1/patients/(?P<id>[0-9a-f-]+)/?$"), "patient", "view"),
    (re.compile(r"^/api/v1/patients/?$"), "patient", None),
    (re.compile(r"^/api/v1/encounters/(?P<id>[0-9a-f-]+)/?$"), "encounter", "view"),
    (re.compile(r"^/api/v1/encounters/?$"), "encounter", None),
    (re.compile(r"^/api/v1/encounters/[0-9a-f-]+/note/?$"), "note", None),
    (re.compile(r"^/api/v1/encounters/[0-9a-f-]+/summary/?$"), "summary", None),
    (re.compile(r"^/api/v1/encounters/[0-9a-f-]+/transcript/?$"), "recording", "view"),
    (re.compile(r"^/api/v1/encounters/[0-9a-f-]+/recording/?$"), "recording", None),
    (re.compile(r"^/api/v1/patient/summaries/?"), "summary", None),
]

METHOD_TO_ACTION = {
    "GET": "view",
    "POST": "create",
    "PUT": "update",
    "PATCH": "update",
    "DELETE": "delete",
}


class HIPAAAuditMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return response

        if response.status_code >= 400:
            return response

        path = request.path
        matched_resource = None
        resource_id = None

        for pattern, resource_type, forced_action in PHI_URL_PATTERNS:
            match = pattern.match(path)
            if match:
                matched_resource = resource_type
                groups = match.groupdict()
                if "id" in groups:
                    resource_id = groups["id"]
                break

        if matched_resource is None:
            return response

        action = METHOD_TO_ACTION.get(request.method, "view")

        try:
            from apps.audit.models import AuditLog

            AuditLog.objects.create(
                user=request.user,
                action=action,
                resource_type=matched_resource,
                resource_id=uuid.UUID(resource_id) if resource_id else uuid.uuid4(),
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                phi_accessed=True,
                details={"path": path, "method": request.method, "status_code": response.status_code},
            )
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")

        return response

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "0.0.0.0")
