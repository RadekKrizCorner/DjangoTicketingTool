"""Authentication classes for account-owned credentials."""

from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied

from apps.accounts import services


class PersonalAccessTokenAuthentication(BaseAuthentication):
    """Authenticate requests with hashed personal access tokens."""

    bearer_keyword = b"bearer"

    def authenticate(self, request):
        """Authenticate a request carrying a personal access token bearer value."""
        raw_token = self._raw_bearer_token(request)
        if raw_token is None:
            return None
        if not raw_token.startswith(services.PERSONAL_ACCESS_TOKEN_PREFIX):
            return None

        token = services.authenticate_personal_access_token(raw_token=raw_token)
        if token is None:
            raise AuthenticationFailed(
                "Personal access token is invalid, revoked, or expired.",
                code="token_not_valid",
            )
        if not token.allows_method(request.method):
            raise PermissionDenied(
                "Personal access token scope does not allow this request.",
                code="permission_denied",
            )
        services.mark_personal_access_token_used(token=token)
        return token.user, token

    def authenticate_header(self, request) -> str:
        """Return the authentication challenge header."""
        return "Bearer"

    def _raw_bearer_token(self, request) -> str | None:
        """Return the bearer token string from the request header."""
        header = get_authorization_header(request).split()
        if not header or header[0].lower() != self.bearer_keyword:
            return None
        if len(header) != 2:
            return None
        try:
            return header[1].decode("utf-8")
        except UnicodeDecodeError:
            return None
