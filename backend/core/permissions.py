from rest_framework.permissions import BasePermission


class IsCounterStaff(BasePermission):
    """Counter staff or managers who are assigned to a theatre."""
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role in ("COUNTER_STAFF", "MANAGER") and u.theatre_id)