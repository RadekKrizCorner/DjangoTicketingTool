# RKRIZ Project Management Workspace

Production-style Django/DRF project management API with a routed React workspace
UI. The project demonstrates authentication, authorization, async processing,
auditability, deployment, reviewer-facing documentation, monitoring, and release
operations.

[![CI](https://github.com/RadekKrizCorner/DjangoTicketingTool/actions/workflows/ci.yml/badge.svg?branch=release)](https://github.com/RadekKrizCorner/DjangoTicketingTool/actions/workflows/ci.yml)
[![Git Policy](https://github.com/RadekKrizCorner/DjangoTicketingTool/actions/workflows/git-policy.yml/badge.svg?branch=release)](https://github.com/RadekKrizCorner/DjangoTicketingTool/actions/workflows/git-policy.yml)

<p>
  <img alt="Python 3.12" src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&amp;logoColor=white">
  <img alt="Django 5.2" src="https://img.shields.io/badge/Django-5.2-092E20?logo=django&amp;logoColor=white">
  <img alt="DRF 3.15" src="https://img.shields.io/badge/DRF-3.15-b91c1c">
  <img alt="Simple JWT" src="https://img.shields.io/badge/Auth-SimpleJWT-111827">
  <img alt="React 19" src="https://img.shields.io/badge/React-19-61DAFB?logo=react&amp;logoColor=111827">
  <img alt="TypeScript 6" src="https://img.shields.io/badge/TypeScript-6-3178C6?logo=typescript&amp;logoColor=white">
  <img alt="Vite 8" src="https://img.shields.io/badge/Vite-8-646CFF?logo=vite&amp;logoColor=white">
  <img alt="Tailwind CSS 4" src="https://img.shields.io/badge/Tailwind_CSS-4-06B6D4?logo=tailwindcss&amp;logoColor=white">
  <img alt="PostgreSQL 16" src="https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&amp;logoColor=white">
  <img alt="Redis 7" src="https://img.shields.io/badge/Redis-7-DC382D?logo=redis&amp;logoColor=white">
  <img alt="Celery 5.4" src="https://img.shields.io/badge/Celery-5.4-37814A">
  <img alt="Prometheus 2.55" src="https://img.shields.io/badge/Prometheus-2.55-E6522C?logo=prometheus&amp;logoColor=white">
  <img alt="Grafana 11.3" src="https://img.shields.io/badge/Grafana-11.3-F46800?logo=grafana&amp;logoColor=white">
  <img alt="Docker Compose" src="https://img.shields.io/badge/Docker_Compose-release-2496ED?logo=docker&amp;logoColor=white">
  <img alt="Kubernetes" src="https://img.shields.io/badge/Kubernetes-manifests-326CE5?logo=kubernetes&amp;logoColor=white">
  <img alt="GHCR" src="https://img.shields.io/badge/GHCR-images-181717?logo=github&amp;logoColor=white">
  <img alt="pytest" src="https://img.shields.io/badge/pytest-tests-0A9EDC?logo=pytest&amp;logoColor=white">
  <img alt="Vitest" src="https://img.shields.io/badge/Vitest-tests-6E9F18?logo=vitest&amp;logoColor=white">
</p>

## Reviewer Path

| Goal | Start here |
| --- | --- |
| See the public entry point | `http://localhost:8000/` |
| Understand the system shape | [Architecture](docs/architecture.md) |
| Inspect the live API contract | `http://localhost:8000/api/v1/docs/` |
| Run the stack locally | [Local Development](#local-development) |
| Review quality strategy | [Testing Strategy](docs/testing/strategy.md) |
| Check release readiness | [Docker](docs/deployment/docker.md), [Kubernetes](docs/deployment/kubernetes.md) |
| Review security posture | [Security](docs/security.md) |
| Inspect production monitoring | `https://grafana.radekkriz.space` |

## Technology Stack

| Area | Technologies |
| --- | --- |
| Backend API | Python 3.12, Django 5.2, Django REST Framework 3.15, Simple JWT, drf-spectacular, django-filter |
| Frontend workspace | React 19, TypeScript 6, Vite 8, Tailwind CSS 4, TanStack Query 5, lucide-react, Sonner |
| Persistence and async | PostgreSQL 16, Redis 7, Celery 5.4, Celery beat |
| Runtime and release | Docker, Docker Compose release stack, Nginx web edge, Gunicorn, WhiteNoise, GHCR multi-arch images |
| Observability | Django Prometheus metrics, Prometheus 2.55, Grafana 11.3, postgres-exporter, redis-exporter, celery-exporter, node-exporter, cAdvisor |
| Deployment targets | Raspberry Pi or VPS release Compose, Kubernetes manifests, optional Cloudflare Tunnel and Cloudflare Access for Grafana |
| Quality | Ruff, pytest, pytest-django, Vitest, React Testing Library, GitHub Actions, local git hooks |

## What This Demonstrates

- JWT authentication and user management for an API-first backend.
- Project memberships and role-based access boundaries.
- Project, task, comment, attachment, audit log, and notification workflows.
- File upload quotas and attachment handling.
- Routed React workspace UI for dashboard, projects, tasks, notifications, and profile flows.
- Celery worker and beat scheduling backed by Redis.
- PostgreSQL persistence with Django migrations.
- OpenAPI documentation generated from the API surface.
- Reviewer-facing homepage that routes to API docs and MkDocs.
- Docker Compose local development and published image release flow.
- Single-port release gateway for homepage, API docs, MkDocs, and admin.
- Prometheus and Grafana monitoring with Cloudflare Access protected dashboards.
- Kubernetes deployment artifacts for API, worker, beat, migrations, ingress, and storage.
- Unit, integration, and end-to-end testing strategy.

This is still API-centered, but the release now includes a practical reviewer UI
for exercising project and task workflows without using the API docs directly.

## Architecture

<p align="center">
  <img src="docs/assets/readme/architecture.svg" alt="System architecture diagram showing reviewer traffic into the Django REST API, PostgreSQL, Redis, Celery, Mailpit, media storage, OpenAPI documentation, GHCR, Docker Compose release, and Kubernetes manifests" width="100%">
</p>

After the stack starts, the generated OpenAPI documentation is available at:

```text
http://localhost:8000/api/v1/docs/
```

## Local Development

Run the API, PostgreSQL, Redis, Celery, Mailpit, and documentation containers:

```bash
docker compose up --build
```

Then open:

```text
Home: http://localhost:8000/
UI: http://localhost:5174/
API: http://localhost:8000/api/v1/
OpenAPI: http://localhost:8000/api/v1/docs/
Mailpit: http://localhost:8025
Docs: http://localhost:8001
```

The homepage uses `/ui/` as its frontend link and `/docs/` as its documentation
link. In local development Django redirects those paths to the Vite and MkDocs
services; in release Nginx serves the built UI and MkDocs directly on the same
public port.

Run migrations and tests:

```bash
docker compose run --rm api python manage.py migrate
docker compose run --rm api pytest -m "unit or integration" -q
```

Create a deterministic demo dataset:

```bash
docker compose run --rm api python manage.py seed_demo_data
```

The seed command creates or updates this predefined superuser:

```text
email: demo.admin@example.com
password: DemoAdmin123!
display name: Demo Admin
```

It also creates demo users, projects, memberships, tasks, comments, text
attachments, and notifications. Override the credentials with
`DEMO_SUPERUSER_EMAIL`, `DEMO_SUPERUSER_PASSWORD`,
`DEMO_SUPERUSER_DISPLAY_NAME`, and `DEMO_USER_PASSWORD`.

## Documentation

Run only the MkDocs documentation site:

```bash
docker compose up docs
```

Then open:

```text
http://localhost:8001
```

Key documentation:

- [API Overview](docs/api/overview.md)
- [API Endpoints](docs/api/endpoints.md)
- [Architecture](docs/architecture.md)
- [Security](docs/security.md)
- [Testing Strategy](docs/testing/strategy.md)
- [Observability](docs/operations/observability.md)

## Release Images

GitHub Actions builds multi-arch runtime images and publishes them to GHCR on
pushes to `master`, `main`, and `v*` tags:

```text
ghcr.io/<owner>/<repo>/api:latest
ghcr.io/<owner>/<repo>/api:sha-<commit>
ghcr.io/<owner>/<repo>/api:<tag>
ghcr.io/<owner>/<repo>/web:latest
ghcr.io/<owner>/<repo>/web:sha-<commit>
ghcr.io/<owner>/<repo>/web:<tag>
```

The `web` image is the public entry point in release and exposes the homepage,
API docs, MkDocs, and admin through one host port.

Monitoring is optional and runs from `docker-compose.release.monitoring.yml`.
The monitoring profile starts Prometheus, Grafana, postgres-exporter,
redis-exporter, celery-exporter, node-exporter, and cAdvisor. Grafana binds only
to loopback by default and is intended to be published as
`https://grafana.radekkriz.space` behind Cloudflare Access while Prometheus and
`/internal/metrics/` stay private. The optional `cloudflare` profile starts the
bundled `cloudflared` service and requires `CLOUDFLARED_TOKEN` only when that
profile is enabled. When Cloudflare Tunnel already runs outside this Compose
stack, use only `--profile monitoring` and do not set `CLOUDFLARED_TOKEN` for
this file.

## Release And Deployment

The repository includes release-oriented Docker and Kubernetes artifacts:

- GHCR publishing for the API and web runtime images.
- Release Compose file for running published images.
- `.env_template` for release Compose configuration.
- `seed-demo` release Compose tool service for optional demo data.
- Optional storage quota override for Linux hosts that support writable-layer quotas.
- Kubernetes manifests for API, Celery worker, Celery beat, migrations, service,
  ingress, and media storage.
- Optional Cloudflare Tunnel deployment example for clusters without a public IP.
- Optional Prometheus, Grafana, and exporter overlay for production observability.

See:

- [Docker Deployment](docs/deployment/docker.md)
- [Kubernetes Deployment](docs/deployment/kubernetes.md)
- [Cloudflare Tunnel](docs/deployment/cloudflare-tunnel.md)
- [Release Strategy](docs/development/release-strategy.md)

## Git Policy

Normal merge requests target `release`. `master` contains released code and should
accept only merge requests from `release` or `hotfix/*`.

Enable local commit title validation:

```bash
git config core.hooksPath .githooks
```
