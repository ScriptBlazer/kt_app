"""Thread-local request user for audit logging outside views."""

import threading

_local = threading.local()


def get_audit_request_user():
    """Authenticated user for the current HTTP request, or None."""
    return getattr(_local, 'audit_user', None)


class AuditRequestUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        _local.audit_user = user if user is not None and user.is_authenticated else None
        try:
            return self.get_response(request)
        finally:
            _local.audit_user = None
