# Project Management Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Django/DRF/Celery project management backend defined in the approved product specification.

**Architecture:** The project uses a layered Django architecture: API views orchestrate HTTP only, serializers define request/response contracts, selectors own read queries, services own business operations and transactions, and policies own permission decisions. PostgreSQL is the only supported database, Redis is the Celery broker, Celery Beat drives scheduled work, and all domain mutations are audit-friendly.

**Tech Stack:** Python 3.12, Django 5.2 LTS, Django REST Framework, SimpleJWT, drf-spectacular, django-filter, Celery, Redis, PostgreSQL, pytest, pytest-django, pytest-kwparametrize, Docker Compose, GHCR, MkDocs.

---

## Implementation Rules

- Keep each milestone as one Git commit.
- Use the existing ticket prefix from the repository: `PROJECT-002`, `PROJECT-003`, and so on.
- Every custom Python function and method must have a simple docstring that says what it does.
- Write tests before implementation in each milestone.
- Use `pytest.mark.kwparametrize` for finite behavior matrices.
- Do not put business logic in API views or serializers.
- Do not use raw SQL for domain operations.
- Use Django ORM and explicit selectors.
- Keep soft-deleted rows out of normal API responses through selectors.
- Add docs updates in the same milestone when behavior changes.
- Run the listed verification command before each commit.

## Planned Milestones

```text
PROJECT-002 Bootstrap dockerized Django project
PROJECT-003 Add API contract, schema, and health checks
PROJECT-004 Add JWT user management and password reset
PROJECT-005 Add project memberships, lifecycle, and audit foundation
PROJECT-006 Add task workflow, comments, and attachments
PROJECT-007 Add notifications, email delivery, and Celery scheduled jobs
PROJECT-008 Add unit, integration, and e2e coverage hardening
PROJECT-009 Add GHCR image publishing workflow
PROJECT-010 Add Kubernetes and deployment artifacts
```

## Final File Structure

```text
.
├── .github/workflows/ci.yml
├── Dockerfile
├── README.md
├── docker-compose.yml
├── docker-compose.release.yml
├── manage.py
├── mkdocs.yml
├── pyproject.toml
├── apps/
│   ├── accounts/
│   ├── api/
│   ├── attachments/
│   ├── audit/
│   ├── common/
│   ├── health/
│   ├── notifications/
│   ├── projects/
│   └── tasks/
├── config/
│   ├── api_urls.py
│   ├── asgi.py
│   ├── celery.py
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   ├── production.py
│   │   └── test.py
│   ├── urls.py
│   └── wsgi.py
├── deploy/
│   └── k8s/
├── docs/
└── tests/
    ├── e2e/
    ├── integration/
    └── unit/
```

## Shared Code Conventions

### Base Service Pattern

Services receive an `actor` argument and never import DRF.

```text
create_project(*, actor: User, data: dict) -> Project
```

### Base Selector Pattern

Selectors return querysets scoped to the caller.

```text
visible_projects_for_user(user: User) -> QuerySet[Project]
```

### Base Policy Pattern

Policies return booleans or raise domain exceptions; DRF permission classes wrap them.

```text
can_manage_project_membership(*, actor: User, project: Project) -> bool
```

### API Response Pattern

Views return wrapped data only.

```python
return Response({"data": serializer.data}, status=status.HTTP_200_OK)
```

### Error Pattern

Domain exceptions map to a stable error shape.

```json
{
  "errors": [
    {
      "code": "project_closed",
      "detail": "Tasks cannot be modified after project is closed.",
      "field": null
    }
  ]
}
```

---

## Task 1: PROJECT-002 Bootstrap Dockerized Django Project

**Files:**

- Create: `pyproject.toml`
- Create: `manage.py`
- Create: `Dockerfile`
- Modify: `docker-compose.yml`
- Create: `config/__init__.py`
- Create: `config/asgi.py`
- Create: `config/wsgi.py`
- Create: `config/urls.py`
- Create: `config/api_urls.py`
- Create: `config/celery.py`
- Create: `config/settings/__init__.py`
- Create: `config/settings/base.py`
- Create: `config/settings/local.py`
- Create: `config/settings/test.py`
- Create: `config/settings/production.py`
- Create: package directories under `apps/`
- Create: `tests/conftest.py`
- Create: `tests/unit/test_project_bootstrap.py`
- Modify: `docs/deployment/docker.md`

### Steps

- [ ] **Step 1: Write failing bootstrap tests**

Create `tests/unit/test_project_bootstrap.py`:

```python
from django.conf import settings
def test_django_settings_load():
    """Verify Django settings load for the test suite."""
    assert settings.ROOT_URLCONF == "config.urls"
    assert settings.DEFAULT_AUTO_FIELD == "django.db.models.BigAutoField"


def test_api_root_is_mounted(client):
    """Verify the API root path is mounted."""
    response = client.get("/api/v1/")
    assert response.status_code in {200, 404}
```

- [ ] **Step 2: Run bootstrap tests and verify they fail**

Run:

```bash
docker compose run --rm api pytest tests/unit/test_project_bootstrap.py -v
```

Expected before implementation:

```text
ERROR: service "api" has neither an image nor a build context specified
```

- [ ] **Step 3: Add Python project dependencies**

Create `pyproject.toml` with project metadata, dependencies, and test configuration:

```toml
[project]
name = "rkriz-django-demo"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = [
  "celery[redis]>=5.4,<6.0",
  "dj-database-url>=2.2,<3.0",
  "django>=5.2,<5.3",
  "django-cors-headers>=4.4,<5.0",
  "django-filter>=24.3,<25.0",
  "djangorestframework>=3.15,<4.0",
  "djangorestframework-simplejwt>=5.3,<6.0",
  "drf-spectacular>=0.27,<1.0",
  "gunicorn>=22.0,<23.0",
  "psycopg[binary]>=3.2,<4.0",
  "python-decouple>=3.8,<4.0",
  "whitenoise>=6.7,<7.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3,<9.0",
  "pytest-django>=4.9,<5.0",
  "pytest-kwparametrize>=0.0.3,<1.0",
  "pytest-cov>=5.0,<6.0",
  "ruff>=0.6,<1.0",
  "httpx>=0.27,<1.0",
]

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.test"
python_files = ["test_*.py", "*_test.py"]
testpaths = ["tests"]
markers = [
  "unit: unit tests",
  "integration: integration tests",
  "e2e: end-to-end tests",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "DJ"]
ignore = []
```

- [ ] **Step 4: Add Dockerfile**

Create `Dockerfile`:

```dockerfile
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
  && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/
RUN pip install --upgrade pip \
  && pip install ".[dev]"

COPY . /app/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/v1/health/live/ || exit 1

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

- [ ] **Step 5: Expand Docker Compose**

Modify `docker-compose.yml` to include the application runtime:

```yaml
services:
  api:
    build:
      context: .
    command: python manage.py runserver 0.0.0.0:8000
    environment:
      DJANGO_SETTINGS_MODULE: config.settings.local
      DATABASE_URL: postgres://app:app@db:5432/app
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/1
      DJANGO_SECRET_KEY: local-development-secret
      DJANGO_ALLOWED_HOSTS: localhost,127.0.0.1,api
      DJANGO_CORS_ALLOWED_ORIGINS: http://localhost:3000
      EMAIL_HOST: mailpit
      EMAIL_PORT: "1025"
    ports:
      - "8000:8000"
    volumes:
      - .:/app
      - media:/app/media
    depends_on:
      - db
      - redis
      - mailpit
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://127.0.0.1:8000/api/v1/health/live/"]
      interval: 30s
      timeout: 5s
      retries: 3

  db:
    image: postgres:16
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  celery-worker:
    build:
      context: .
    command: celery -A config worker -l info
    environment:
      DJANGO_SETTINGS_MODULE: config.settings.local
      DATABASE_URL: postgres://app:app@db:5432/app
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/1
      DJANGO_SECRET_KEY: local-development-secret
      EMAIL_HOST: mailpit
      EMAIL_PORT: "1025"
    volumes:
      - .:/app
      - media:/app/media
    depends_on:
      - api
      - redis
      - db

  celery-beat:
    build:
      context: .
    command: celery -A config beat -l info
    environment:
      DJANGO_SETTINGS_MODULE: config.settings.local
      DATABASE_URL: postgres://app:app@db:5432/app
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/1
      DJANGO_SECRET_KEY: local-development-secret
      EMAIL_HOST: mailpit
      EMAIL_PORT: "1025"
    volumes:
      - .:/app
      - media:/app/media
    depends_on:
      - api
      - redis
      - db

  mailpit:
    image: axllent/mailpit:latest
    ports:
      - "8025:8025"
      - "1025:1025"

  docs:
    image: squidfunk/mkdocs-material:9
    command: serve --dev-addr=0.0.0.0:8000
    ports:
      - "8001:8000"
    volumes:
      - .:/docs
    working_dir: /docs

volumes:
  postgres_data:
  media:
```

- [ ] **Step 6: Add Django settings and entrypoints**

Create `manage.py`:

```python
#!/usr/bin/env python
"""Run Django management commands."""

import os
import sys


def main() -> None:
    """Run the selected Django management command."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

Create `config/settings/base.py` with installed apps, middleware, REST framework,
database URL parsing, Celery URLs, media settings, and attachment limits:

```python
"""Base Django settings shared by all environments."""

from pathlib import Path

from decouple import Csv, config
from dj_database_url import parse as parse_database_url

BASE_DIR = Path(__file__).resolve().parents[2]
SECRET_KEY = config("DJANGO_SECRET_KEY", default="unsafe-local-secret")
DEBUG = config("DJANGO_DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "apps.common",
    "apps.accounts",
    "apps.audit",
    "apps.projects",
    "apps.tasks",
    "apps.attachments",
    "apps.notifications",
    "apps.health",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

DATABASES = {
    "default": parse_database_url(
        config("DATABASE_URL", default="postgres://app:app@db:5432/app"),
        conn_max_age=60,
    )
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ),
    "EXCEPTION_HANDLER": "apps.api.exceptions.api_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Project Management API",
    "DESCRIPTION": "Django/DRF project management backend API.",
    "VERSION": "1.0.0",
}

CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://redis:6379/1")

EMAIL_HOST = config("EMAIL_HOST", default="localhost")
EMAIL_PORT = config("EMAIL_PORT", default=1025, cast=int)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@example.test")

ATTACHMENT_MAX_FILE_SIZE_BYTES = config(
    "ATTACHMENT_MAX_FILE_SIZE_BYTES", default=1048576, cast=int
)
ATTACHMENT_MAX_TOTAL_BYTES = config(
    "ATTACHMENT_MAX_TOTAL_BYTES", default=209715200, cast=int
)
ATTACHMENT_MAX_PROJECT_BYTES = config(
    "ATTACHMENT_MAX_PROJECT_BYTES", default=20971520, cast=int
)
DATA_UPLOAD_MAX_MEMORY_SIZE = ATTACHMENT_MAX_FILE_SIZE_BYTES + 1024 * 128
FILE_UPLOAD_MAX_MEMORY_SIZE = ATTACHMENT_MAX_FILE_SIZE_BYTES
```

Add missing dependency `dj-database-url>=2.2,<3.0` to `pyproject.toml` because
`base.py` uses it.

- [ ] **Step 7: Run bootstrap verification**

Run:

```bash
docker compose build api
docker compose run --rm api python manage.py check
docker compose run --rm api pytest tests/unit/test_project_bootstrap.py -v
docker compose config
```

Expected:

```text
System check identified no issues
2 passed
```

- [ ] **Step 8: Commit milestone**

Run:

```bash
git add Dockerfile docker-compose.yml manage.py pyproject.toml config apps tests docs
git commit -m "PROJECT-002 Bootstrap dockerized Django project"
```

---

## Task 2: PROJECT-003 Add API Contract, Schema, And Health Checks

**Files:**

- Create: `apps/api/exceptions.py`
- Create: `apps/api/pagination.py`
- Create: `apps/api/responses.py`
- Create: `apps/common/errors.py`
- Create: `apps/health/api/urls.py`
- Create: `apps/health/api/views.py`
- Modify: `config/api_urls.py`
- Modify: `config/urls.py`
- Modify: `config/settings/base.py`
- Test: `tests/unit/test_api_errors.py`
- Test: `tests/integration/test_health_api.py`
- Test: `tests/integration/test_openapi_schema.py`
- Modify: `docs/api/errors-pagination.md`
- Modify: `docs/api/overview.md`

### Steps

- [ ] **Step 1: Write failing API infrastructure tests**

Create `tests/integration/test_health_api.py`:

```python
import pytest


@pytest.mark.integration
def test_live_health_is_public(client):
    """Verify live health endpoint is public."""
    response = client.get("/api/v1/health/live/")
    assert response.status_code == 200
    assert response.json() == {"data": {"status": "ok"}}


@pytest.mark.integration
def test_ready_health_returns_dependency_status(client):
    """Verify ready health endpoint returns dependency status."""
    response = client.get("/api/v1/health/ready/")
    assert response.status_code == 200
    assert response.json()["data"]["database"] == "ok"
```

Create `tests/integration/test_openapi_schema.py`:

```python
import pytest


@pytest.mark.integration
def test_openapi_schema_is_public(client):
    """Verify OpenAPI schema is publicly accessible."""
    response = client.get("/api/v1/schema/")
    assert response.status_code == 200
    assert "openapi" in response.json()
```

- [ ] **Step 2: Run failing API infrastructure tests**

Run:

```bash
docker compose run --rm api pytest tests/integration/test_health_api.py tests/integration/test_openapi_schema.py -v
```

Expected:

```text
FAILED tests/integration/test_health_api.py::test_live_health_is_public - assert 404 == 200
```

- [ ] **Step 3: Add response helpers**

Create `apps/api/responses.py`:

```python
"""Helpers for consistent API responses."""

from rest_framework.response import Response


def data_response(data, *, status_code: int = 200) -> Response:
    """Return a response wrapped in the standard data envelope."""
    return Response({"data": data}, status=status_code)


def empty_response(*, status_code: int = 204) -> Response:
    """Return an empty API response."""
    return Response(status=status_code)
```

- [ ] **Step 4: Add domain error type and exception handler**

Create `apps/common/errors.py`:

```python
"""Domain error classes for API and service layers."""


class DomainError(Exception):
    """Represent an application-level domain error."""

    def __init__(self, *, code: str, detail: str, field: str | None = None, status_code: int = 400):
        """Initialize the domain error."""
        self.code = code
        self.detail = detail
        self.field = field
        self.status_code = status_code
        super().__init__(detail)
```

Create `apps/api/exceptions.py`:

```python
"""DRF exception handling for the standard error envelope."""

from rest_framework.views import exception_handler
from rest_framework.response import Response

from apps.common.errors import DomainError


def api_exception_handler(exc, context):
    """Convert exceptions into the standard API error envelope."""
    if isinstance(exc, DomainError):
        return Response(
            {"errors": [{"code": exc.code, "detail": exc.detail, "field": exc.field}]},
            status=exc.status_code,
        )

    response = exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data
    if isinstance(detail, dict):
        errors = [
            {"code": "validation_error", "detail": str(value), "field": key}
            for key, value in detail.items()
        ]
    else:
        errors = [{"code": "error", "detail": str(detail), "field": None}]
    response.data = {"errors": errors}
    return response
```

- [ ] **Step 5: Add pagination helper**

Create `apps/api/pagination.py`:

```python
"""Pagination classes for API list endpoints."""

from math import ceil

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPageNumberPagination(PageNumberPagination):
    """Paginate results with the standard metadata envelope."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        """Return paginated response with metadata."""
        page_size = self.get_page_size(self.request) or self.page_size
        total_pages = ceil(self.page.paginator.count / page_size) if page_size else 0
        return Response(
            {
                "data": data,
                "meta": {
                    "pagination": {
                        "count": self.page.paginator.count,
                        "page": self.page.number,
                        "page_size": page_size,
                        "total_pages": total_pages,
                        "next": self.get_next_link(),
                        "previous": self.get_previous_link(),
                    }
                },
            }
        )
```

- [ ] **Step 6: Add health endpoints**

Create `apps/health/api/views.py`:

```python
"""Health check API views."""

from django.db import connection
from rest_framework.views import APIView

from apps.api.responses import data_response


class LiveHealthView(APIView):
    """Return process liveness status."""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        """Return live health status."""
        return data_response({"status": "ok"})


class ReadyHealthView(APIView):
    """Return dependency readiness status."""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        """Return ready health status."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return data_response({"status": "ok", "database": "ok"})
```

Create `apps/health/api/urls.py`:

```python
"""Health API routes."""

from django.urls import path

from apps.health.api.views import LiveHealthView, ReadyHealthView

urlpatterns = [
    path("live/", LiveHealthView.as_view(), name="health-live"),
    path("ready/", ReadyHealthView.as_view(), name="health-ready"),
]
```

- [ ] **Step 7: Add root URL wiring and schema views**

Create `config/api_urls.py`:

```python
"""Versioned API URL routes."""

from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("health/", include("apps.health.api.urls")),
]
```

Modify `config/urls.py`:

```python
"""Root URL configuration."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("config.api_urls")),
]
```

- [ ] **Step 8: Run API verification**

Run:

```bash
docker compose run --rm api pytest tests/integration/test_health_api.py tests/integration/test_openapi_schema.py -v
docker compose run --rm api python manage.py spectacular --file /tmp/schema.yml --validate
```

Expected:

```text
3 passed
Schema generation summary
```

- [ ] **Step 9: Commit milestone**

Run:

```bash
git add apps config tests docs
git commit -m "PROJECT-003 Add API contract schema and health checks"
```

---

## Task 3: PROJECT-004 Add JWT User Management And Password Reset

**Files:**

- Create: `apps/accounts/models.py`
- Create: `apps/accounts/managers.py`
- Create: `apps/accounts/services.py`
- Create: `apps/accounts/selectors.py`
- Create: `apps/accounts/policies.py`
- Create: `apps/accounts/tokens.py`
- Create: `apps/accounts/api/urls.py`
- Create: `apps/accounts/api/views.py`
- Create: `apps/accounts/api/serializers.py`
- Create: `apps/accounts/api/schema.py`
- Create: `apps/accounts/admin.py`
- Create: `apps/accounts/migrations/0001_initial.py`
- Modify: `config/api_urls.py`
- Modify: `config/settings/base.py`
- Test: `tests/unit/accounts/test_user_model.py`
- Test: `tests/integration/accounts/test_auth_api.py`
- Test: `tests/integration/accounts/test_password_reset.py`
- Test: `tests/integration/accounts/test_user_search.py`
- Modify: `docs/security.md`
- Modify: `docs/api/endpoints.md`

### Steps

- [ ] **Step 1: Write failing user model tests**

Create `tests/unit/accounts/test_user_model.py`:

```python
import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError


@pytest.mark.django_db
@pytest.mark.unit
def test_user_uses_unique_email_login():
    """Verify users authenticate by unique normalized email."""
    user_model = get_user_model()
    user = user_model.objects.create_user(email="USER@Example.com", password="secret-pass-123")
    assert user.email == "user@example.com"
    assert user_model.USERNAME_FIELD == "email"


@pytest.mark.django_db
@pytest.mark.unit
def test_duplicate_email_is_rejected_case_insensitively():
    """Verify duplicate emails are rejected regardless of case."""
    user_model = get_user_model()
    user_model.objects.create_user(email="user@example.com", password="secret-pass-123")
    with pytest.raises(IntegrityError):
        user_model.objects.create_user(email="USER@example.com", password="secret-pass-123")
```

- [ ] **Step 2: Write failing auth API tests**

Create `tests/integration/accounts/test_auth_api.py`:

```python
import pytest


@pytest.mark.integration
@pytest.mark.django_db
def test_register_login_and_me_flow(client):
    """Verify a user can register, login, and read their identity."""
    register = client.post(
        "/api/v1/users/register/",
        {
            "email": "user@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
            "display_name": "Example User",
        },
        content_type="application/json",
    )
    assert register.status_code == 201
    assert register.json()["data"]["email"] == "user@example.com"

    token = client.post(
        "/api/v1/users/token/",
        {"email": "user@example.com", "password": "StrongPass123!"},
        content_type="application/json",
    )
    assert token.status_code == 200
    access = token.json()["data"]["access"]

    me = client.get("/api/v1/users/me/", HTTP_AUTHORIZATION=f"Bearer {access}")
    assert me.status_code == 200
    assert me.json()["data"]["email"] == "user@example.com"
```

Create `tests/integration/accounts/test_password_reset.py`:

```python
import pytest
from django.core import mail


@pytest.mark.integration
@pytest.mark.django_db
def test_password_reset_request_does_not_reveal_missing_email(client):
    """Verify password reset request hides account existence."""
    response = client.post(
        "/api/v1/users/password-reset/request/",
        {"email": "missing@example.com"},
        content_type="application/json",
    )
    assert response.status_code == 202
    assert response.json()["data"]["accepted"] is True
    assert len(mail.outbox) == 0
```

- [ ] **Step 3: Run failing account tests**

Run:

```bash
docker compose run --rm api pytest tests/unit/accounts tests/integration/accounts -v
```

Expected:

```text
FAILED tests/unit/accounts/test_user_model.py::test_user_uses_unique_email_login
```

- [ ] **Step 4: Implement custom user and profile models**

Create `apps/accounts/managers.py`:

```python
"""Account model managers."""

from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """Create users with email as the login identifier."""

    def normalize_email(self, email):
        """Normalize email to lowercase."""
        return super().normalize_email(email).lower()

    def create_user(self, email, password=None, **extra_fields):
        """Create a regular user."""
        if not email:
            raise ValueError("Email is required.")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create a superuser."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)
```

Create `apps/accounts/models.py`:

```python
"""Account models."""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower

from apps.accounts.managers import UserManager


class User(AbstractUser):
    """Represent an application user identified by email."""

    username = None
    email = models.EmailField(unique=False)
    display_name = models.CharField(max_length=150)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_lower_unique"),
        ]

    def __str__(self) -> str:
        """Return the user's display label."""
        return self.email


class UserProfile(models.Model):
    """Store editable profile details for a user."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    timezone = models.CharField(max_length=64, default="UTC")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ExternalIdentity(models.Model):
    """Store a future SSO identity link for a user."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="external_identities")
    provider = models.CharField(max_length=64)
    provider_subject = models.CharField(max_length=255)
    email_at_link_time = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_subject"],
                name="accounts_external_identity_provider_subject_unique",
            )
        ]
```

- [ ] **Step 5: Add account serializers and services**

Create `apps/accounts/services.py`:

```python
"""Business services for user accounts."""

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings

from apps.accounts.models import UserProfile


def register_user(*, email: str, password: str, display_name: str):
    """Register a new active user."""
    user_model = get_user_model()
    user = user_model.objects.create_user(
        email=email,
        password=password,
        display_name=display_name,
        is_active=True,
    )
    UserProfile.objects.create(user=user)
    return user


def request_password_reset(*, email: str) -> None:
    """Send a password reset email when the account exists."""
    user_model = get_user_model()
    user = user_model.objects.filter(email=email.lower(), is_active=True).first()
    if user is None or not user.has_usable_password():
        return
    token = PasswordResetTokenGenerator().make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    send_mail(
        subject="Password reset",
        message=f"Use uid={uid} token={token} to reset your password.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
```

Create serializers for registration, profile, password change, and password reset.
The registration serializer must validate matching passwords and call `register_user`.

- [ ] **Step 6: Add account API routes**

Create `apps/accounts/api/urls.py`:

```python
"""Account API routes."""

from django.urls import path

from apps.accounts.api import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="users-register"),
    path("token/", views.TokenView.as_view(), name="users-token"),
    path("token/refresh/", views.TokenRefreshView.as_view(), name="users-token-refresh"),
    path("token/verify/", views.TokenVerifyView.as_view(), name="users-token-verify"),
    path("logout/", views.LogoutView.as_view(), name="users-logout"),
    path("me/", views.MeView.as_view(), name="users-me"),
    path("profile/", views.ProfileView.as_view(), name="users-profile"),
    path("password/", views.PasswordChangeView.as_view(), name="users-password"),
    path(
        "password-reset/request/",
        views.PasswordResetRequestView.as_view(),
        name="users-password-reset-request",
    ),
    path(
        "password-reset/confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="users-password-reset-confirm",
    ),
    path("search/", views.UserSearchView.as_view(), name="users-search"),
]
```

Modify `config/api_urls.py` to include:

```python
path("users/", include("apps.accounts.api.urls")),
```

- [ ] **Step 7: Run account migrations and tests**

Run:

```bash
docker compose run --rm api python manage.py makemigrations accounts
docker compose run --rm api python manage.py migrate
docker compose run --rm api pytest tests/unit/accounts tests/integration/accounts -v
```

Expected:

```text
passed
```

- [ ] **Step 8: Commit milestone**

Run:

```bash
git add apps/accounts config tests docs
git commit -m "PROJECT-004 Add JWT user management and password reset"
```

---

## Task 4: PROJECT-005 Add Project Memberships, Lifecycle, And Audit Foundation

**Files:**

- Create: `apps/common/models.py`
- Create: `apps/audit/models.py`
- Create: `apps/audit/services.py`
- Create: `apps/audit/selectors.py`
- Create: `apps/projects/models.py`
- Create: `apps/projects/policies.py`
- Create: `apps/projects/selectors.py`
- Create: `apps/projects/services.py`
- Create: `apps/projects/api/urls.py`
- Create: `apps/projects/api/views.py`
- Create: `apps/projects/api/serializers.py`
- Create: `apps/projects/api/filters.py`
- Create: `apps/projects/admin.py`
- Create: migrations for `audit` and `projects`
- Modify: `config/api_urls.py`
- Test: `tests/unit/projects/test_project_policies.py`
- Test: `tests/integration/projects/test_project_api.py`
- Test: `tests/integration/projects/test_membership_api.py`
- Test: `tests/integration/projects/test_lifecycle_api.py`
- Test: `tests/integration/projects/test_audit_log_api.py`
- Modify: `docs/product-specification.md`

### Steps

- [ ] **Step 1: Write failing role matrix tests**

Create `tests/unit/projects/test_project_policies.py`:

```python
import pytest


@pytest.mark.unit
@pytest.mark.kwparametrize(
    dict(role="owner", action="delete_project", expected=True),
    dict(role="manager", action="delete_project", expected=False),
    dict(role="member", action="delete_project", expected=False),
    dict(role="viewer", action="delete_project", expected=False),
    dict(role="owner", action="manage_members", expected=True),
    dict(role="manager", action="manage_members", expected=False),
    dict(role="member", action="manage_members", expected=False),
    dict(role="viewer", action="manage_members", expected=False),
)
def test_project_role_permissions(role, action, expected):
    """Verify project role permission matrix."""
    from apps.projects.policies import role_allows_action

    assert role_allows_action(role=role, action=action) is expected
```

- [ ] **Step 2: Write failing project API tests**

Create `tests/integration/projects/test_project_api.py`:

```python
import pytest


@pytest.mark.integration
@pytest.mark.django_db
def test_create_project_creates_owner_membership(auth_client, user):
    """Verify project creation creates owner membership."""
    response = auth_client.post(
        "/api/v1/projects/",
        {"name": "CRM", "description": "Customer work", "visibility": "private"},
        content_type="application/json",
    )
    assert response.status_code == 201
    project_id = response.json()["data"]["id"]

    members = auth_client.get(f"/api/v1/projects/{project_id}/members/")
    assert members.status_code == 200
    assert members.json()["data"][0]["role"] == "owner"
```

- [ ] **Step 3: Run failing project tests**

Run:

```bash
docker compose run --rm api pytest tests/unit/projects tests/integration/projects -v
```

Expected:

```text
FAILED tests/unit/projects/test_project_policies.py::test_project_role_permissions - ModuleNotFoundError: No module named 'apps.projects.policies'
```

- [ ] **Step 4: Add shared audit model**

Create `apps/common/models.py`:

```python
"""Shared abstract models."""

from django.conf import settings
from django.db import models


class TimestampedAuditModel(models.Model):
    """Add timestamp and actor audit fields."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_%(class)ss",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="updated_%(class)ss",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deleted_%(class)ss",
    )

    class Meta:
        abstract = True
```

- [ ] **Step 5: Add audit log model and service**

Create `apps/audit/models.py`:

```python
"""Audit log models."""

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Record an auditable domain action."""

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=100)
    entity_id = models.BigIntegerField()
    project = models.ForeignKey("projects.Project", null=True, blank=True, on_delete=models.SET_NULL)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["project", "-created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="audit_log_idempotency_key_unique",
            )
        ]
```

Create `apps/audit/services.py`:

```python
"""Audit log business services."""

from apps.audit.models import AuditLog


def record_audit_log(**kwargs) -> AuditLog:
    """Create an audit log entry."""
    return AuditLog.objects.create(**kwargs)
```

- [ ] **Step 6: Add project and membership models**

Create `apps/projects/models.py`:

```python
"""Project domain models."""

from django.conf import settings
from django.db import models

from apps.common.models import TimestampedAuditModel


class Project(TimestampedAuditModel):
    """Represent a project."""

    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        PUBLIC = "public", "Public"

    class State(models.TextChoices):
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"

    class PublicCommentPolicy(models.TextChoices):
        MEMBERS_ONLY = "members_only", "Members only"
        AUTHENTICATED_USERS = "authenticated_users", "Authenticated users"

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_projects")
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.PRIVATE)
    state = models.CharField(max_length=20, choices=State.choices, default=State.ACTIVE)
    public_comment_policy = models.CharField(
        max_length=40,
        choices=PublicCommentPolicy.choices,
        default=PublicCommentPolicy.MEMBERS_ONLY,
    )
    publish_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    close_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)


class ProjectMembership(TimestampedAuditModel):
    """Represent a user's role in a project."""

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MANAGER = "manager", "Manager"
        MEMBER = "member", "Member"
        VIEWER = "viewer", "Viewer"

    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="project_memberships")
    role = models.CharField(max_length=20, choices=Role.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "user"],
                condition=models.Q(deleted_at__isnull=True),
                name="projects_active_membership_project_user_unique",
            ),
            models.UniqueConstraint(
                fields=["project"],
                condition=models.Q(role="owner", deleted_at__isnull=True),
                name="projects_one_active_owner_membership",
            ),
        ]
```

- [ ] **Step 7: Add project policy and service functions**

Create `apps/projects/policies.py`:

```python
"""Project permission policies."""

OWNER_ACTIONS = {"delete_project", "manage_members", "schedule", "transfer", "audit_log", "close", "reopen"}
MANAGER_ACTIONS = {"manage_tasks"}
MEMBER_ACTIONS = {"read"}
VIEWER_ACTIONS = {"read"}


def role_allows_action(*, role: str, action: str) -> bool:
    """Return whether a role allows an action."""
    allowed = {
        "owner": OWNER_ACTIONS | MANAGER_ACTIONS | MEMBER_ACTIONS | VIEWER_ACTIONS,
        "manager": MANAGER_ACTIONS | MEMBER_ACTIONS | VIEWER_ACTIONS,
        "member": MEMBER_ACTIONS,
        "viewer": VIEWER_ACTIONS,
    }
    return action in allowed.get(role, set())
```

Create service functions with these exact signatures and behaviors:

```python
def create_project(*, actor: User, data: dict) -> Project:
    """Create a project and owner membership in one transaction."""

def transfer_project_ownership(*, actor: User, project: Project, new_owner: User) -> Project:
    """Transfer project ownership to a new owner in one transaction."""

def soft_delete_project(*, actor: User, project: Project) -> None:
    """Soft delete a project and keep audit history."""

def close_project(*, actor: User | None, project: Project) -> Project:
    """Close a project and clear the pending close schedule."""

def reopen_project(*, actor: User, project: Project) -> Project:
    """Reopen a closed project and clear close timestamps."""
```

Each function must use `transaction.atomic()` and write an audit log.

- [ ] **Step 8: Run project verification**

Run:

```bash
docker compose run --rm api python manage.py makemigrations audit projects
docker compose run --rm api python manage.py migrate
docker compose run --rm api pytest tests/unit/projects tests/integration/projects -v
```

Expected:

```text
passed
```

- [ ] **Step 9: Commit milestone**

Run:

```bash
git add apps/common apps/audit apps/projects config tests docs
git commit -m "PROJECT-005 Add project memberships lifecycle and audit foundation"
```

---

## Task 5: PROJECT-006 Add Task Workflow, Comments, And Attachments

**Files:**

- Create: `apps/tasks/models.py`
- Create: `apps/tasks/workflow.py`
- Create: `apps/tasks/policies.py`
- Create: `apps/tasks/selectors.py`
- Create: `apps/tasks/services.py`
- Create: `apps/tasks/api/urls.py`
- Create: `apps/tasks/api/views.py`
- Create: `apps/tasks/api/serializers.py`
- Create: `apps/tasks/api/filters.py`
- Create: `apps/attachments/models.py`
- Create: `apps/attachments/services.py`
- Create: `apps/attachments/selectors.py`
- Create: `apps/attachments/api/urls.py`
- Create: `apps/attachments/api/views.py`
- Create: `apps/attachments/api/serializers.py`
- Create: admin and migration files
- Modify: `config/api_urls.py`
- Test: `tests/unit/tasks/test_task_workflow.py`
- Test: `tests/integration/tasks/test_task_api.py`
- Test: `tests/integration/tasks/test_comment_api.py`
- Test: `tests/integration/attachments/test_attachment_api.py`
- Test: `tests/integration/attachments/test_attachment_quota.py`
- Modify: `docs/attachments.md`
- Modify: `docs/api/endpoints.md`

### Steps

- [ ] **Step 1: Write failing workflow matrix tests**

Create `tests/unit/tasks/test_task_workflow.py`:

```python
import pytest


@pytest.mark.unit
@pytest.mark.kwparametrize(
    dict(current="new", target="accepted", allowed=True),
    dict(current="new", target="in_progress", allowed=False),
    dict(current="new", target="cancelled", allowed=True),
    dict(current="accepted", target="in_progress", allowed=True),
    dict(current="accepted", target="on_hold", allowed=True),
    dict(current="accepted", target="completed", allowed=False),
    dict(current="in_progress", target="on_hold", allowed=True),
    dict(current="in_progress", target="completed", allowed=True),
    dict(current="on_hold", target="in_progress", allowed=True),
    dict(current="completed", target="accepted", allowed=True),
    dict(current="cancelled", target="accepted", allowed=True),
)
def test_task_transition_matrix(current, target, allowed):
    """Verify task workflow transition matrix."""
    from apps.tasks.workflow import is_transition_allowed

    assert is_transition_allowed(current=current, target=target) is allowed
```

- [ ] **Step 2: Write failing attachment quota tests**

Create `tests/integration/attachments/test_attachment_quota.py`:

```python
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile


@pytest.mark.integration
@pytest.mark.django_db
def test_attachment_larger_than_one_mb_is_rejected(auth_client, project_task):
    """Verify oversized attachment uploads are rejected."""
    project, task = project_task
    file_obj = SimpleUploadedFile(
        "large.log",
        b"x" * (1024 * 1024 + 1),
        content_type="text/plain",
    )
    response = auth_client.post(
        f"/api/v1/projects/{project.id}/tasks/{task.id}/attachments/",
        {"file": file_obj},
    )
    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "attachment_too_large"
```

- [ ] **Step 3: Run failing task and attachment tests**

Run:

```bash
docker compose run --rm api pytest tests/unit/tasks tests/integration/tasks tests/integration/attachments -v
```

Expected:

```text
FAILED tests/unit/tasks/test_task_workflow.py::test_task_transition_matrix - ModuleNotFoundError: No module named 'apps.tasks.workflow'
```

- [ ] **Step 4: Add task workflow**

Create `apps/tasks/workflow.py`:

```python
"""Task workflow transition rules."""

ALLOWED_TRANSITIONS = {
    "new": {"accepted", "cancelled"},
    "accepted": {"in_progress", "on_hold", "cancelled"},
    "in_progress": {"on_hold", "completed", "cancelled"},
    "on_hold": {"in_progress", "cancelled"},
    "completed": {"accepted"},
    "cancelled": {"accepted"},
}


def is_transition_allowed(*, current: str, target: str) -> bool:
    """Return whether a task status transition is allowed."""
    return target in ALLOWED_TRANSITIONS.get(current, set())
```

- [ ] **Step 5: Add task and comment models**

Create `apps/tasks/models.py`:

```python
"""Task domain models."""

from django.conf import settings
from django.db import models

from apps.common.models import TimestampedAuditModel


class Task(TimestampedAuditModel):
    """Represent a project task."""

    class Status(models.TextChoices):
        NEW = "new", "New"
        ACCEPTED = "accepted", "Accepted"
        IN_PROGRESS = "in_progress", "In progress"
        ON_HOLD = "on_hold", "On hold"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    project = models.ForeignKey("projects.Project", on_delete=models.PROTECT, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assigned_tasks")
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.NEW)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    due_at = models.DateTimeField(null=True, blank=True)


class TaskComment(TimestampedAuditModel):
    """Represent a comment on a task."""

    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="task_comments")
    body = models.TextField()
```

- [ ] **Step 6: Add attachment model**

Create `apps/attachments/models.py`:

```python
"""Attachment models."""

from django.conf import settings
from django.db import models

from apps.common.models import TimestampedAuditModel


class Attachment(TimestampedAuditModel):
    """Represent a file attached to a task or comment."""

    task = models.ForeignKey("tasks.Task", null=True, blank=True, on_delete=models.PROTECT, related_name="attachments")
    comment = models.ForeignKey(
        "tasks.TaskComment",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="attachments",
    )
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="attachments")
    original_filename = models.CharField(max_length=255)
    file = models.FileField(upload_to="attachments/%Y/%m/%d/")
    content_type = models.CharField(max_length=100)
    size_bytes = models.PositiveIntegerField()
    checksum_sha256 = models.CharField(max_length=64)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    (models.Q(task__isnull=False) & models.Q(comment__isnull=True))
                    | (models.Q(task__isnull=True) & models.Q(comment__isnull=False))
                ),
                name="attachments_exactly_one_parent",
            )
        ]
```

- [ ] **Step 7: Add task and attachment services**

Create service functions with these exact signatures and behaviors:

```python
def create_task(*, actor: User, project: Project, data: dict) -> Task:
    """Create a task in an active project."""

def transition_task(*, actor: User, task: Task, target_status: str, note: str = "") -> Task:
    """Move a task to a new workflow status."""

def create_comment(*, actor: User, task: Task, body: str) -> TaskComment:
    """Create a task comment."""

def create_attachment(*, actor: User, parent: Task | TaskComment, uploaded_file) -> Attachment:
    """Create an attachment after validating type and quota."""
```

Attachment validation must check:

```python
ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "text/plain"}
TEXT_EXTENSIONS = {".txt", ".log", ".out", ".err"}
```

- [ ] **Step 8: Add nested API routes**

Create task and attachment route files so project-scoped URLs work:

```python
path("projects/<int:project_id>/tasks/", include("apps.tasks.api.urls")),
path("attachments/<int:attachment_id>/download/", AttachmentDownloadView.as_view()),
```

The final path set must match `docs/api/endpoints.md`.

- [ ] **Step 9: Run task verification**

Run:

```bash
docker compose run --rm api python manage.py makemigrations tasks attachments
docker compose run --rm api python manage.py migrate
docker compose run --rm api pytest tests/unit/tasks tests/integration/tasks tests/integration/attachments -v
```

Expected:

```text
passed
```

- [ ] **Step 10: Commit milestone**

Run:

```bash
git add apps/tasks apps/attachments config tests docs
git commit -m "PROJECT-006 Add task workflow comments and attachments"
```

---

## Task 6: PROJECT-007 Add Notifications, Email Delivery, And Celery Scheduled Jobs

**Files:**

- Create: `apps/notifications/models.py`
- Create: `apps/notifications/services.py`
- Create: `apps/notifications/selectors.py`
- Create: `apps/notifications/api/urls.py`
- Create: `apps/notifications/api/views.py`
- Create: `apps/notifications/api/serializers.py`
- Create: `apps/notifications/tasks.py`
- Modify: `apps/projects/services.py`
- Modify: `apps/tasks/services.py`
- Modify: `config/celery.py`
- Modify: `config/settings/base.py`
- Test: `tests/unit/notifications/test_notification_dedupe.py`
- Test: `tests/integration/notifications/test_notification_api.py`
- Test: `tests/integration/notifications/test_email_delivery.py`
- Test: `tests/integration/notifications/test_scheduled_jobs.py`
- Modify: `docs/decisions/celery-scheduling.md`

### Steps

- [ ] **Step 1: Write failing idempotency tests**

Create `tests/integration/notifications/test_scheduled_jobs.py`:

```python
import pytest
from django.utils import timezone


@pytest.mark.integration
@pytest.mark.django_db
def test_publish_due_projects_is_idempotent(project_factory):
    """Verify publishing due projects twice creates one notification set."""
    from apps.notifications.models import Notification
    from apps.notifications.tasks import publish_due_projects

    project = project_factory(visibility="private", publish_at=timezone.now())
    publish_due_projects()
    publish_due_projects()
    project.refresh_from_db()

    assert project.visibility == "public"
    assert project.published_at is not None
    assert Notification.objects.filter(project=project, type="project_published").count() == 1
```

- [ ] **Step 2: Run failing scheduled job tests**

Run:

```bash
docker compose run --rm api pytest tests/integration/notifications/test_scheduled_jobs.py -v
```

Expected:

```text
FAILED tests/integration/notifications/test_scheduled_jobs.py::test_publish_due_projects_is_idempotent - ModuleNotFoundError: No module named 'apps.notifications.models'
```

- [ ] **Step 3: Add notification and email delivery models**

Create `apps/notifications/models.py`:

```python
"""Notification and email delivery models."""

from django.conf import settings
from django.db import models

from apps.common.models import TimestampedAuditModel


class Notification(TimestampedAuditModel):
    """Represent an in-app notification."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="notifications")
    type = models.CharField(max_length=80)
    title = models.CharField(max_length=200)
    message = models.TextField()
    project = models.ForeignKey("projects.Project", null=True, blank=True, on_delete=models.PROTECT)
    task = models.ForeignKey("tasks.Task", null=True, blank=True, on_delete=models.PROTECT)
    dedupe_key = models.CharField(max_length=255)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "dedupe_key"], name="notifications_user_dedupe_unique")
        ]


class EmailDelivery(models.Model):
    """Represent an email delivery outbox row."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="email_deliveries")
    notification = models.ForeignKey(Notification, null=True, blank=True, on_delete=models.PROTECT)
    email = models.EmailField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider_message_id = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["notification", "user"],
                name="notifications_email_delivery_notification_user_unique",
            )
        ]
```

- [ ] **Step 4: Add notification services**

Create `apps/notifications/services.py`:

```python
"""Notification business services."""

from django.db import IntegrityError, transaction

from apps.notifications.models import EmailDelivery, Notification


def create_notification(*, user, type: str, title: str, message: str, dedupe_key: str, project=None, task=None):
    """Create a notification and matching pending email delivery."""
    with transaction.atomic():
        try:
            notification = Notification.objects.create(
                user=user,
                type=type,
                title=title,
                message=message,
                dedupe_key=dedupe_key,
                project=project,
                task=task,
            )
        except IntegrityError:
            return Notification.objects.get(user=user, dedupe_key=dedupe_key)
        EmailDelivery.objects.get_or_create(
            notification=notification,
            user=user,
            defaults={"email": user.email},
        )
        return notification
```

- [ ] **Step 5: Add Celery app and scheduled tasks**

Create `config/celery.py`:

```python
"""Celery application configuration."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("rkriz_django_demo")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

Create `apps/notifications/tasks.py` with Celery task functions named exactly:

```text
publish_due_projects() -> int
close_due_projects() -> int
send_deadline_reminders() -> int
send_pending_emails() -> int
```

Required behavior:

- `publish_due_projects` locks due unpublished projects, publishes them once, creates one notification per active member, and returns the number of changed projects.
- `close_due_projects` locks due active projects, closes them once, writes audit entries, and returns the number of changed projects.
- `send_deadline_reminders` creates at most one reminder per user and task deadline value, excluding completed, cancelled, closed, and soft-deleted records.
- `send_pending_emails` locks pending delivery rows, sends each email, records `sent_at` or `error_message`, and returns the number of attempted deliveries.

Configure Beat in `config/settings/base.py`:

```python
CELERY_BEAT_SCHEDULE = {
    "publish-due-projects": {
        "task": "apps.notifications.tasks.publish_due_projects",
        "schedule": 60.0,
    },
    "close-due-projects": {
        "task": "apps.notifications.tasks.close_due_projects",
        "schedule": 60.0,
    },
    "send-deadline-reminders": {
        "task": "apps.notifications.tasks.send_deadline_reminders",
        "schedule": 900.0,
    },
    "send-pending-emails": {
        "task": "apps.notifications.tasks.send_pending_emails",
        "schedule": 60.0,
    },
}
```

- [ ] **Step 6: Add notification API**

Routes:

```text
GET  /api/v1/notifications/
POST /api/v1/notifications/{notification_id}/read/
POST /api/v1/notifications/read-all/
```

Selectors must return only current user's notifications with `deleted_at IS NULL`.

- [ ] **Step 7: Run notification verification**

Run:

```bash
docker compose run --rm api python manage.py makemigrations notifications
docker compose run --rm api python manage.py migrate
docker compose run --rm api pytest tests/unit/notifications tests/integration/notifications -v
```

Expected:

```text
passed
```

- [ ] **Step 8: Commit milestone**

Run:

```bash
git add apps/notifications apps/projects apps/tasks config tests docs
git commit -m "PROJECT-007 Add notifications email delivery and scheduled jobs"
```

---

## Task 7: PROJECT-008 Add Unit, Integration, And E2E Coverage Hardening

**Files:**

- Modify: `tests/conftest.py`
- Create: `tests/factories.py`
- Create: `tests/e2e/test_docker_compose_flow.py`
- Add or modify tests under `tests/unit/`
- Add or modify tests under `tests/integration/`
- Modify: `docs/testing/strategy.md`

### Steps

- [ ] **Step 1: Add shared test factories**

Create `tests/factories.py`:

```python
"""Test data factories."""

from django.contrib.auth import get_user_model


def create_user(*, email: str = "user@example.com", password: str = "StrongPass123!", **kwargs):
    """Create a test user."""
    user_model = get_user_model()
    return user_model.objects.create_user(email=email, password=password, display_name=kwargs.pop("display_name", "User"), **kwargs)
```

Add these additional factory functions in the same file:

```python
def create_project(*, owner, name: str = "Project", **kwargs):
    """Create a project through the project service."""
    from apps.projects.services import create_project as service_create_project

    data = {"name": name, "description": kwargs.pop("description", ""), **kwargs}
    return service_create_project(actor=owner, data=data)


def create_task(*, actor, project, assignee, title: str = "Task", **kwargs):
    """Create a task through the task service."""
    from apps.tasks.services import create_task as service_create_task

    data = {"title": title, "assignee_id": assignee.id, **kwargs}
    return service_create_task(actor=actor, project=project, data=data)
```

- [ ] **Step 2: Add full permission matrices**

Add matrices using `pytest.mark.kwparametrize` for:

```text
project role x action
task role x action x project state
comment role x author relation
attachment parent x role x project state
visibility x authentication state
```

Each matrix must assert both HTTP status and error code when an error is expected.

- [ ] **Step 3: Add e2e test**

Create `tests/e2e/test_docker_compose_flow.py`:

```python
"""End-to-end smoke flow against a running local API."""

import os

import httpx
import pytest


@pytest.mark.e2e
def test_register_create_project_task_and_comment_flow():
    """Verify the deployed API supports the main user flow."""
    base_url = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8000")
    client = httpx.Client(base_url=base_url, timeout=10)

    register = client.post(
        "/api/v1/users/register/",
        json={
            "email": "e2e@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
            "display_name": "E2E User",
        },
    )
    assert register.status_code in {201, 400}

    token = client.post(
        "/api/v1/users/token/",
        json={"email": "e2e@example.com", "password": "StrongPass123!"},
    )
    assert token.status_code == 200
    access = token.json()["data"]["access"]
    headers = {"Authorization": f"Bearer {access}"}

    project = client.post(
        "/api/v1/projects/",
        headers=headers,
        json={"name": "E2E Project", "description": "Flow", "visibility": "private"},
    )
    assert project.status_code == 201
```

- [ ] **Step 4: Run all test categories**

Run:

```bash
docker compose run --rm api pytest -m unit -v
docker compose run --rm api pytest -m integration -v
docker compose up -d api celery-worker celery-beat mailpit
E2E_BASE_URL=http://127.0.0.1:8000 docker compose run --rm api pytest -m e2e -v
docker compose down
```

Expected:

```text
passed
```

- [ ] **Step 5: Commit milestone**

Run:

```bash
git add tests docs
git commit -m "PROJECT-008 Add unit integration and e2e coverage"
```

---

## Task 8: PROJECT-009 Add GHCR Image Publishing Workflow

**Files:**

- Create: `.github/workflows/ci.yml`
- Create: `docker-compose.release.yml`
- Modify: `README.md`
- Modify: `docs/deployment/docker.md`

### Steps

- [ ] **Step 1: Add CI workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  pull_request:
  push:
    branches:
      - master
      - main
    tags:
      - "v*"

permissions:
  contents: read
  packages: write

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: app
          POSTGRES_USER: app
          POSTGRES_PASSWORD: app
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install --upgrade pip
      - run: pip install ".[dev]"
      - run: ruff check .
      - run: pytest -m "unit or integration"
        env:
          DJANGO_SETTINGS_MODULE: config.settings.test
          DATABASE_URL: postgres://app:app@127.0.0.1:5432/app
          CELERY_BROKER_URL: redis://127.0.0.1:6379/0
          CELERY_RESULT_BACKEND: redis://127.0.0.1:6379/1
          DJANGO_SECRET_KEY: ci-secret

  docker:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        if: github.event_name == 'push'
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/metadata-action@v5
        id: meta
        with:
          images: ghcr.io/${{ github.repository }}/api
          tags: |
            type=sha
            type=ref,event=tag
            type=raw,value=latest,enable={{is_default_branch}}
      - uses: docker/build-push-action@v6
        with:
          context: .
          push: ${{ github.event_name == 'push' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
```

- [ ] **Step 2: Add release Compose**

Create `docker-compose.release.yml`:

```yaml
services:
  api:
    image: ghcr.io/${GITHUB_REPOSITORY:-owner/repo}/api:latest
    env_file:
      - .env
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis

  db:
    image: postgres:16
    env_file:
      - .env
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

volumes:
  postgres_data:
```

- [ ] **Step 3: Document public GHCR visibility**

Update README and Docker docs:

```text
After the first image publish, open the GitHub package settings and change package
visibility to public so reviewers can pull the image without authentication.
```

- [ ] **Step 4: Run CI file verification locally**

Run:

```bash
docker compose build api
docker compose run --rm api pytest -m "unit or integration" -v
```

Expected:

```text
passed
```

- [ ] **Step 5: Commit milestone**

Run:

```bash
git add .github docker-compose.release.yml README.md docs
git commit -m "PROJECT-009 Add GHCR image publishing workflow"
```

---

## Task 9: PROJECT-010 Add Kubernetes And Deployment Artifacts

**Files:**

- Create: `deploy/k8s/namespace.yaml`
- Create: `deploy/k8s/configmap.yaml`
- Create: `deploy/k8s/secret.example.yaml`
- Create: `deploy/k8s/api-deployment.yaml`
- Create: `deploy/k8s/celery-worker-deployment.yaml`
- Create: `deploy/k8s/celery-beat-deployment.yaml`
- Create: `deploy/k8s/migrate-job.yaml`
- Create: `deploy/k8s/service.yaml`
- Create: `deploy/k8s/ingress.yaml`
- Create: `deploy/k8s/media-pvc.yaml`
- Create: `deploy/k8s/cloudflared-deployment.example.yaml`
- Modify: `docs/deployment/kubernetes.md`
- Modify: `docs/deployment/cloudflare-tunnel.md`
- Modify: `README.md`

### Steps

- [ ] **Step 1: Add namespace and config**

Create `deploy/k8s/namespace.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: project-management
```

Create `deploy/k8s/configmap.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: project-management-config
  namespace: project-management
data:
  DJANGO_SETTINGS_MODULE: config.settings.production
  DJANGO_ALLOWED_HOSTS: api.example.com
  DJANGO_CORS_ALLOWED_ORIGINS: https://app.example.com
  ATTACHMENT_MAX_FILE_SIZE_BYTES: "1048576"
  ATTACHMENT_MAX_TOTAL_BYTES: "209715200"
  ATTACHMENT_MAX_PROJECT_BYTES: "20971520"
```

- [ ] **Step 2: Add API deployment with probes**

Create `deploy/k8s/api-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: project-management-api
  namespace: project-management
spec:
  replicas: 2
  selector:
    matchLabels:
      app: project-management-api
  template:
    metadata:
      labels:
        app: project-management-api
    spec:
      containers:
        - name: api
          image: ghcr.io/owner/repo/api:latest
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef:
                name: project-management-config
            - secretRef:
                name: project-management-secret
          volumeMounts:
            - name: media
              mountPath: /app/media
          livenessProbe:
            httpGet:
              path: /api/v1/health/live/
              port: 8000
            initialDelaySeconds: 20
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /api/v1/health/ready/
              port: 8000
            initialDelaySeconds: 20
            periodSeconds: 30
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
              ephemeral-storage: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
              ephemeral-storage: 512Mi
      volumes:
        - name: media
          persistentVolumeClaim:
            claimName: project-management-media
```

- [ ] **Step 3: Add migration job and worker deployments**

Create `deploy/k8s/migrate-job.yaml`:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: project-management-migrate
  namespace: project-management
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: migrate
          image: ghcr.io/owner/repo/api:latest
          command: ["python", "manage.py", "migrate", "--noinput"]
          envFrom:
            - configMapRef:
                name: project-management-config
            - secretRef:
                name: project-management-secret
```

Create `deploy/k8s/celery-worker-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: project-management-celery-worker
  namespace: project-management
spec:
  replicas: 1
  selector:
    matchLabels:
      app: project-management-celery-worker
  template:
    metadata:
      labels:
        app: project-management-celery-worker
    spec:
      containers:
        - name: celery-worker
          image: ghcr.io/owner/repo/api:latest
          command: ["celery", "-A", "config", "worker", "-l", "info"]
          envFrom:
            - configMapRef:
                name: project-management-config
            - secretRef:
                name: project-management-secret
```

Create `deploy/k8s/celery-beat-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: project-management-celery-beat
  namespace: project-management
spec:
  replicas: 1
  selector:
    matchLabels:
      app: project-management-celery-beat
  template:
    metadata:
      labels:
        app: project-management-celery-beat
    spec:
      containers:
        - name: celery-beat
          image: ghcr.io/owner/repo/api:latest
          command: ["celery", "-A", "config", "beat", "-l", "info"]
          envFrom:
            - configMapRef:
                name: project-management-config
            - secretRef:
                name: project-management-secret
```

- [ ] **Step 4: Add Cloudflare Tunnel example**

Create `deploy/k8s/cloudflared-deployment.example.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cloudflared
  namespace: project-management
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cloudflared
  template:
    metadata:
      labels:
        app: cloudflared
    spec:
      containers:
        - name: cloudflared
          image: cloudflare/cloudflared:latest
          args:
            - tunnel
            - --no-autoupdate
            - run
          env:
            - name: TUNNEL_TOKEN
              valueFrom:
                secretKeyRef:
                  name: cloudflared-secret
                  key: tunnel-token
```

- [ ] **Step 5: Validate Kubernetes YAML**

Run:

```bash
kubectl apply --dry-run=client -f deploy/k8s/
```

Expected:

```text
configured (dry run)
```

If `kubectl` is not installed, run:

```bash
docker run --rm -v "$PWD/deploy/k8s:/work" ghcr.io/yannh/kubeconform:latest -summary /work
```

Expected:

```text
0 invalid
```

- [ ] **Step 6: Commit milestone**

Run:

```bash
git add deploy docs README.md
git commit -m "PROJECT-010 Add Kubernetes and deployment artifacts"
```

---

## Final Verification Before Delivery

Run:

```bash
docker compose build
docker compose run --rm api python manage.py check
docker compose run --rm api python manage.py migrate
docker compose run --rm api pytest -m unit -v
docker compose run --rm api pytest -m integration -v
docker compose up -d api celery-worker celery-beat mailpit docs
curl -fsS http://127.0.0.1:8000/api/v1/health/live/
curl -fsS http://127.0.0.1:8000/api/v1/health/ready/
curl -fsS http://127.0.0.1:8000/api/v1/schema/
curl -fsS http://127.0.0.1:8001/
docker compose down
```

Expected:

```text
All tests pass.
Health endpoints return 200.
OpenAPI schema returns 200.
MkDocs site returns 200.
```

## Plan Self-Review

### Spec Coverage

| Requirement | Covered By |
| --- | --- |
| User accounts | `PROJECT-004` |
| Unique email login | `PROJECT-004` |
| Password reset email | `PROJECT-004` |
| Future SSO-ready model | `PROJECT-004` |
| Project ownership and members | `PROJECT-005` |
| Explicit owner membership | `PROJECT-005` |
| Ownership transfer | `PROJECT-005` |
| Project lifecycle and scheduling fields | `PROJECT-005`, `PROJECT-007` |
| Task workflow | `PROJECT-006` |
| Comments | `PROJECT-006` |
| Task and comment attachments | `PROJECT-006` |
| Attachment quotas | `PROJECT-006` |
| Notifications and email outbox | `PROJECT-007` |
| Celery scheduled jobs | `PROJECT-007` |
| Idempotent jobs | `PROJECT-007` |
| Audit log | `PROJECT-005`, `PROJECT-006`, `PROJECT-007` |
| API response contract | `PROJECT-003` |
| OpenAPI docs | `PROJECT-003` |
| Pagination | `PROJECT-003` and list endpoints |
| Unit tests | all milestones, hardened in `PROJECT-008` |
| Integration tests | all milestones, hardened in `PROJECT-008` |
| E2E tests | `PROJECT-008` |
| Docker Compose | `PROJECT-002` |
| GHCR image publishing | `PROJECT-009` |
| Kubernetes deploy | `PROJECT-010` |
| Cloudflare Tunnel docs | `PROJECT-010` |

### Open-Ended Instruction Scan

The plan keeps milestone tasks tied to explicit files, behavior, tests, verification
commands, and commit messages. Service internals are constrained by required
signatures, behavior lists, and failing tests written before implementation.

### Type Consistency

- Primary keys use integers.
- Project roles use `owner`, `manager`, `member`, `viewer`.
- Task statuses use `new`, `accepted`, `in_progress`, `on_hold`, `completed`, `cancelled`.
- Visibility uses `private`, `public`.
- Project state uses `active`, `closed`.
- Attachments use `task` or `comment` parent.

### Plan Rating

Rating: 8.5/10.

The plan is technically strong and maps the specification to reviewable milestone
commits. The main risk is implementation size: the backend has many interacting
domains, so each milestone must stay disciplined and complete its tests before
moving to the next milestone.
