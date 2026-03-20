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
    (re.compile(r"^/api/v1/templates/(?P<id>[0-9a-f-]+)/?$"), "template", "view"),
    (re.compile(r"^/api/v1/templates/?$"), "template", None),
    (re.compile(r"^/api/v1/templates/[0-9a-f-]+/auto-complete/?$"), "template", None),
    (re.compile(r"^/api/v1/encounters/[0-9a-f-]+/quality/?"), "quality_score", None),
    (re.compile(r"^/api/v1/encounters/[0-9a-f-]+/telehealth/?"), "telehealth", None),
    (re.compile(r"^/api/v1/encounters/[0-9a-f-]+/fhir/push/?"), "fhir_push", None),
    (re.compile(r"^/api/v1/encounters/[0-9a-f-]+/fhir/logs/?"), "fhir_push", None),
    (re.compile(r"^/api/v1/fhir/connections/?"), "fhir_push", None),
    (re.compile(r"^/api/v1/telehealth/"), "telehealth", None),
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

        # Determine user and outcome
        user = None
        user_role = ""
        if hasattr(request, "user") and request.user.is_authenticated:
            user = request.user
            user_role = getattr(request.user, "role", "")

        outcome = "success" if response.status_code < 400 else "failure"
        if response.status_code >= 500:
            outcome = "error"

        action = METHOD_TO_ACTION.get(request.method, "view")

        # Get session ID safely
        session_id = ""
        if hasattr(request, "session") and request.session.session_key:
            session_id = request.session.session_key

        try:
            from apps.audit.models import AuditLog

            AuditLog.objects.create(
                user=user,
                action=action,
                resource_type=matched_resource,
                resource_id=uuid.UUID(resource_id) if resource_id else uuid.uuid4(),
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                phi_accessed=True,
                outcome=outcome,
                user_role=user_role,
                session_id=session_id,
                source_system="api",
                details={
                    "path": path,
                    "method": request.method,
                    "status_code": response.status_code,
                },
            )
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")

        return response

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "0.0.0.0")
