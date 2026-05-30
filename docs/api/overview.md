# API Overview

## Base Path

```text
/api/v1/
```

## Authentication

JWT access tokens are sent through:

```text
Authorization: Bearer <token>
```

CSRF is not required for API requests because the API uses bearer tokens instead of
cookie session authentication.

## Public Endpoints

Anonymous users may access only endpoints that do not reveal concrete application data.

```text
/api/v1/health/live/
/api/v1/schema/
/api/v1/docs/
/api/v1/redoc/
/api/v1/users/register/
/api/v1/users/token/
/api/v1/users/token/refresh/
/api/v1/users/token/verify/
/api/v1/users/password-reset/request/
/api/v1/users/password-reset/confirm/
```

## OpenAPI

OpenAPI schema and documentation are public.

The schema exposes request and response contracts. It does not expose projects,
tasks, comments, users, memberships, attachments, notifications, or audit data.

## Response Contract

Success:

```json
{
  "data": {}
}
```

Error:

```json
{
  "errors": [
    {
      "code": "permission_denied",
      "detail": "You do not have permission to perform this action.",
      "field": null
    }
  ]
}
```

## Leak Policy

| Situation | Status |
| --- | --- |
| Anonymous request to protected endpoint | `401` |
| Authenticated request to private resource without access | `404` |
| Authenticated request to visible resource without write permission | `403` |
| Nonexistent resource | `404` |
