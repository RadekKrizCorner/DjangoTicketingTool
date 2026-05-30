# Project Management Backend Design

## Status

Approved for documentation milestone.

Implementation plan will be generated only after this specification is reviewed and
committed.

## Canonical Specification

The canonical product specification is:

```text
docs/product-specification.md
```

Related detailed documents:

```text
docs/architecture.md
docs/api/overview.md
docs/api/endpoints.md
docs/api/errors-pagination.md
docs/decisions/postgresql.md
docs/decisions/celery-scheduling.md
docs/decisions/redis-ha.md
docs/attachments.md
docs/security.md
docs/testing/strategy.md
docs/deployment/docker.md
docs/deployment/kubernetes.md
docs/deployment/cloudflare-tunnel.md
docs/operations/observability.md
docs/reviews/product-specification-review.md
```

## Design Summary

Build a Django REST Framework backend for project management with JWT user
authentication, email-based accounts, project roles, task workflow, comments,
attachments, notifications, scheduled Celery jobs, audit logging, soft delete, and
deployment-ready documentation.

The system uses PostgreSQL as the only supported database. Celery and Redis handle
background work. Docker Compose supports local development. Kubernetes and
Cloudflare Tunnel are documented deployment paths.

## Primary Architectural Rule

Business logic must not live in API views or serializers.

Each app follows this structure:

```text
models.py
selectors.py
services.py
policies.py
tasks.py
api/
  urls.py
  views.py
  serializers.py
  schema.py
  filters.py
  permissions.py
```

## Key Decisions

- `BigAutoField` integer primary keys.
- Custom user model with unique email login.
- Active account immediately after registration.
- Password reset through email.
- Future SSO-ready `ExternalIdentity` model.
- Project owner is an explicit `ProjectMembership` role.
- Exactly one project owner.
- Owner transfer is supported.
- Public projects are visible to authenticated users only.
- Anonymous users never see concrete domain data.
- Task status changes use an explicit transition endpoint.
- Attachments are allowed on tasks and comments.
- Attachments are limited to 1 MB per file, 200 MB globally, and 20 MB per project.
- OpenAPI schema is public.
- All important domain entities are soft-deleted.
- Audit log is owner-only per project.
- Background jobs are idempotent.
- Tests are unit, integration, and end-to-end.
- `pytest-kwparametrize` is used for behavior matrices.

## Review

The design has been reviewed in `docs/reviews/product-specification-review.md`.

Rating: 9/10.
