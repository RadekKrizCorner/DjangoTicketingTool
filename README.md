# RKRIZ Project Management Backend

Django/DRF project management backend with JWT users, projects, memberships,
tasks, comments, attachments, audit logs, notifications, and Celery scheduling.

## Local Development

Run the API, PostgreSQL, Redis, Celery, Mailpit, and docs containers:

```bash
docker compose up --build
```

Then open:

```text
Home: http://localhost:8000/
API: http://localhost:8000/api/v1/
OpenAPI: http://localhost:8000/api/v1/docs/
Mailpit: http://localhost:8025
Docs: http://localhost:8001
```

The homepage uses `/docs/` as its documentation link. In local development Django
redirects that path to the MkDocs container on `http://localhost:8001`; in release
Nginx serves MkDocs directly on the same public port.

Run migrations and tests:

```bash
docker compose run --rm api python manage.py migrate
docker compose run --rm api pytest -m "unit or integration" -q
```

## View Documentation

Run only the MkDocs documentation site:

```bash
docker compose up docs
```

Then open:

```text
http://localhost:8001
```

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

After the first publish, set the GHCR package visibility to public in GitHub
Package settings. Public GHCR packages can be pulled without authentication:

```bash
docker pull ghcr.io/<owner>/<repo>/api:latest
docker pull ghcr.io/<owner>/<repo>/web:latest
```

If the package remains private, reviewers must run `docker login ghcr.io` first.

## Release Compose

Run the published images without building locally. The `web` service is the only
public entry point and exposes Django, API docs, MkDocs, and admin through one
host port.

```bash
export APP_IMAGE=ghcr.io/radekkrizcorner/djangoticketingtool/api:latest
export WEB_IMAGE=ghcr.io/radekkrizcorner/djangoticketingtool/web:latest
export PUBLIC_PORT=48137
export DJANGO_SECRET_KEY="$(openssl rand -hex 32)"
export DJANGO_ALLOWED_HOSTS=radekkriz.space,www.radekkriz.space,localhost,127.0.0.1
export DJANGO_CSRF_TRUSTED_ORIGINS=http://radekkriz.space:48137,http://www.radekkriz.space:48137,https://radekkriz.space,https://www.radekkriz.space
export DJANGO_SECURE_SSL_REDIRECT=false
docker compose -f docker-compose.release.yml --profile tools run --rm migrate
docker compose -f docker-compose.release.yml up -d web api celery-worker celery-beat
```

`docker-compose.release.yml` keeps the same upload quotas as the application
specification: 1 MB per file, 200 MB globally, and 20 MB per project.

For direct HTTP on port `48137`, keep `DJANGO_SECURE_SSL_REDIRECT=false`. If
`radekkriz.space` or `www.radekkriz.space` terminates HTTPS before this Compose stack, set
`DJANGO_SECURE_SSL_REDIRECT=true` and keep
`DJANGO_CSRF_TRUSTED_ORIGINS=https://radekkriz.space,https://www.radekkriz.space`.

On Linux hosts where the Docker storage driver supports writable-layer quotas,
add `-f docker-compose.release.storage.yml` to the migration and `up` commands.
This is intentionally an override because Docker Desktop and some VPS storage
drivers reject `storage_opt.size`.

## Kubernetes

Kubernetes manifests are available in `deploy/k8s/`:

```bash
kubectl apply -f deploy/k8s/namespace.yaml
kubectl apply -f deploy/k8s/configmap.yaml
kubectl apply -f /path/to/secret.yaml
kubectl apply -f deploy/k8s/media-pvc.yaml
kubectl apply -f deploy/k8s/migrate-job.yaml
kubectl apply -f deploy/k8s/api-deployment.yaml
kubectl apply -f deploy/k8s/celery-worker-deployment.yaml
kubectl apply -f deploy/k8s/celery-beat-deployment.yaml
kubectl apply -f deploy/k8s/service.yaml
kubectl apply -f deploy/k8s/ingress.yaml
```

Use `deploy/k8s/cloudflared-deployment.example.yaml` when the cluster has no
public IP address and the API should be exposed through Cloudflare Tunnel.

## Git Policy

Normal merge requests target `release`. `master` contains released code and should
accept only merge requests from `release` or `hotfix/*`.

Enable local commit title validation:

```bash
git config core.hooksPath .githooks
```
