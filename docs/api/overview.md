# API Overview

## Base Path

```text
/api/v1/
```

## Authentication

JWT access tokens and personal access tokens are sent through:

```text
Authorization: Bearer <token>
```

CSRF is not required for API requests because the API uses bearer tokens instead of
cookie session authentication.

## Public Endpoints

Anonymous users may access only endpoints that do not reveal concrete application data.

```text
/api/v1/health/live/
/api/v1/health/ready/
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

Public documentation routes:

```text
/api/v1/schema/
/api/v1/docs/
/api/v1/redoc/
```

## Health

Live health confirms the application process can respond:

```json
{
  "data": {
    "status": "ok"
  }
}
```

Ready health confirms the application can reach required infrastructure:

```json
{
  "data": {
    "status": "ok",
    "database": "ok",
    "redis": "ok"
  }
}
```

## User Management

User accounts use email as the login identifier. Registration normalizes email
addresses to lowercase and returns the created user under `data`.

JWT endpoints also use the standard success envelope:

```json
{
  "data": {
    "access": "<access-token>",
    "refresh": "<refresh-token>"
  }
}
```

Personal access tokens are available for script and API-client testing:

```text
GET    /api/v1/users/personal-tokens/
POST   /api/v1/users/personal-tokens/
DELETE /api/v1/users/personal-tokens/{token_id}/
```

Create returns the raw token once:

```json
{
  "data": {
    "id": 1,
    "name": "Postman",
    "token_prefix": "rkriz_pat_abc123...",
    "token": "rkriz_pat_abc123...",
    "scopes": ["full_access"],
    "expires_at": null,
    "revoked_at": null,
    "last_used_at": null,
    "created_at": "2026-06-01T12:00:00Z"
  }
}
```

The server stores only a hash of the raw token. `full_access` allows normal API
use. `read_only` allows only safe HTTP methods.

Logout blacklists the submitted refresh token and returns:

```json
{
  "data": {
    "status": "logged_out"
  }
}
```

## Response Contract

Success:

```json
{
  "data": {}
}
```

Authenticated application responses may include UI helper fields such as
`capabilities`, `my_membership`, and nested user summaries. These fields are
additive and are derived from the same backend policy checks that protect the
write endpoints.

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
