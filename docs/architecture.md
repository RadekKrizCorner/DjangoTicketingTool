# Architecture

## Runtime Components

Version 1 uses:

- Django application container.
- PostgreSQL database.
- Redis broker.
- Celery worker.
- Celery beat scheduler.
- Mailpit for local email inspection.
- MkDocs documentation container.

## Application Layout

Each application keeps API, schema, read logic, business logic, and policy decisions
separate.

```text
apps/<app>/
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

## Layer Responsibilities

| Layer | Responsibility |
| --- | --- |
| `api/views.py` | HTTP orchestration only. |
| `api/serializers.py` | Input validation and output representation. |
| `api/schema.py` | OpenAPI metadata and examples. |
| `api/filters.py` | Explicit filtering and ordering definitions. |
| `api/permissions.py` | DRF wrappers around domain policies. |
| `selectors.py` | Read/query logic and access-scoped querysets. |
| `services.py` | Business operations, transactions, audit, notifications. |
| `policies.py` | Role and permission decisions independent of DRF. |
| `tasks.py` | Celery entrypoints that call services. |

API code must not contain business logic. Services must not import DRF.

## Request Flow

Example:

```text
POST /api/v1/projects/
  -> ProjectCreateInputSerializer
  -> project_services.create_project(actor, validated_data)
  -> transaction creates project + owner membership + audit log
  -> ProjectDetailOutputSerializer
  -> {"data": ...}
```

## URL Structure

URLs are owned by application routers and included by the API root.

```text
config/urls.py
config/api_urls.py
apps/accounts/api/urls.py
apps/projects/api/urls.py
apps/tasks/api/urls.py
apps/attachments/api/urls.py
apps/notifications/api/urls.py
apps/health/api/urls.py
```

Each app owns its API surface while `/api/v1/` stays consistent.

## Data Access

The code should use Django ORM for persistence operations. Raw SQL should be avoided.

Soft delete filtering must be explicit in selectors instead of hidden in a global
default manager.

Explicit selectors make audit and admin use cases easier to reason
about and avoid hidden behavior during debugging.
