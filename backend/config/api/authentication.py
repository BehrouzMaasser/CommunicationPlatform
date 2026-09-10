from rest_framework.authentication import SessionAuthentication


class SessionAuthentication401(SessionAuthentication):
    """
    Django session authentication that returns 401 rather than 403
    when no authenticated session is present.

    Authenticated unsafe requests still use DRF's normal CSRF checks.
    """

    def authenticate_header(self, request):
        return "Session"
