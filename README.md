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
API: http://localhost:8000/api/v1/
OpenAPI: http://localhost:8000/api/v1/docs/
Mailpit: http://localhost:8025
Docs: http://localhost:8001
```

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

## Release Image

GitHub Actions builds the runtime Docker image and publishes it to GHCR on pushes
to `master`, `main`, and `v*` tags:

```text
ghcr.io/<owner>/<repo>/api:latest
ghcr.io/<owner>/<repo>/api:sha-<commit>
ghcr.io/<owner>/<repo>/api:<tag>
```

After the first publish, set the GHCR package visibility to public in GitHub
Package settings. Public GHCR packages can be pulled without authentication:

```bash
docker pull ghcr.io/<owner>/<repo>/api:latest
```

If the package remains private, reviewers must run `docker login ghcr.io` first.

## Release Compose

Run the published image without building locally:

```bash
export APP_IMAGE=ghcr.io/<owner>/<repo>/api:latest
export DJANGO_SECRET_KEY="$(openssl rand -hex 32)"
docker compose -f docker-compose.release.yml --profile tools run --rm migrate
docker compose -f docker-compose.release.yml up -d api celery-worker celery-beat
```

`docker-compose.release.yml` keeps the same upload quotas as the application
specification: 1 MB per file, 200 MB globally, and 20 MB per project.

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
