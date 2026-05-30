"""Common domain errors."""

from http import HTTPStatus


class DomainError(Exception):
    """Represent a domain error that can be rendered by the API layer."""

    def __init__(
        self,
        code: str,
        detail: str,
        field: str | None = None,
        status_code: int = HTTPStatus.BAD_REQUEST,
    ) -> None:
        """Initialize the domain error."""
        self.code = code
        self.detail = detail
        self.field = field
        self.status_code = int(status_code)
        super().__init__(detail)
