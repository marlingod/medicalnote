from rest_framework.permissions import BasePermission


class IsDoctor(BasePermission):
    """Allow access only to users with doctor role."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "doctor"
        )


class IsAdmin(BasePermission):
    """Allow access only to users with admin role."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )


class IsDoctorOrAdmin(BasePermission):
    """Allow access to doctors and admins."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ("doctor", "admin")
        )


class IsPatient(BasePermission):
    """Allow access only to users with patient role."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "patient"
        )


class IsSamePractice(BasePermission):
    """Ensure user can only access resources within their practice."""

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "practice"):
            return obj.practice_id == request.user.practice_id
        if hasattr(obj, "patient"):
            return obj.patient.practice_id == request.user.practice_id
        if hasattr(obj, "doctor"):
            return obj.doctor.practice_id == request.user.practice_id
        return False
