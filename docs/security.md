# Security

## Authentication

Use JWT access and refresh tokens.

Access tokens are sent as:

```text
Authorization: Bearer <token>
```

Refresh rotation and blacklist are required so logout and password reset can revoke
existing refresh tokens.

## Password Reset

Endpoints:

```text
POST /api/v1/users/password-reset/request/
POST /api/v1/users/password-reset/confirm/
```

The request endpoint returns the same response whether or not the email exists.

Justification: this avoids account enumeration.

## Throttling

Initial throttle targets:

```text
login: 5/min
password_reset: 3/min
upload: 20/hour/user
```

## CORS And CSRF

The API is bearer-token based and does not require CSRF tokens.

CORS allowed origins are configured through environment variables.

## Data Exposure

Anonymous users can access only public infrastructure endpoints and auth entrypoints.
They cannot read project, task, comment, attachment, membership, user search,
notification, or audit data.

Authenticated users without access to private resources receive `404`.

## Future SSO

Version 1 does not implement SSO, but the model allows it later through
`ExternalIdentity`.

Recommended future approach:

- OIDC for Azure AD, Google Workspace, or Keycloak.
- Map provider and `sub` claim to `ExternalIdentity`.
- Use local users as the internal identity for project roles.
- Allow SSO-only accounts through unusable passwords.
- Keep local password reset only for users with usable passwords.
