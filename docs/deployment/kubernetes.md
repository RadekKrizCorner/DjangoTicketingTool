# Kubernetes Deployment

## Overview

Kubernetes manifests live under `deploy/k8s/` and use the same runtime image
published by the GHCR workflow:

```text
ghcr.io/<owner>/<repo>/api:latest
```

The manifests include:

```text
Namespace
ConfigMap
Secret example
PersistentVolumeClaim/media
Deployment/api
Deployment/celery-worker
Deployment/celery-beat
Job/migrate
Service/api
Ingress/api
Cloudflare Tunnel example
```

PostgreSQL, Redis, and SMTP are referenced through secret values. This keeps the
manifests usable with managed services, an in-cluster database, or a home-lab
network service.

## Apply Flow

Create a real secret from the example and replace all placeholder values:

```bash
cp deploy/k8s/secret.example.yaml /tmp/project-management-secret.yaml
```

Apply the base resources:

```bash
kubectl apply -f deploy/k8s/namespace.yaml
kubectl apply -f deploy/k8s/configmap.yaml
kubectl apply -f /tmp/project-management-secret.yaml
kubectl apply -f deploy/k8s/media-pvc.yaml
```

Run migrations explicitly:

```bash
kubectl -n project-management delete job project-management-migrate --ignore-not-found
kubectl apply -f deploy/k8s/migrate-job.yaml
```

Deploy runtime workloads and routing:

```bash
kubectl apply -f deploy/k8s/api-deployment.yaml
kubectl apply -f deploy/k8s/celery-worker-deployment.yaml
kubectl apply -f deploy/k8s/celery-beat-deployment.yaml
kubectl apply -f deploy/k8s/service.yaml
kubectl apply -f deploy/k8s/ingress.yaml
```

## Probes

The API deployment uses the same endpoints as Docker health checks:

```text
livenessProbe:  /api/v1/health/live/
readinessProbe: /api/v1/health/ready/
```

The readiness probe checks database and Redis connectivity, so Kubernetes should
only route traffic to pods that can serve requests against required dependencies.

## Migrations

Run migrations through a Kubernetes `Job`, not inside every API pod startup.

Justification: migration execution should be explicit and should not race between
API replicas during rolling deployments. Kubernetes Jobs are immutable after
creation, so delete and recreate the job or use release-specific job names.

## Media Storage

The included PVC requests `256Mi` and is mounted at `/app/media`. The application
still enforces these quotas:

```text
single file: 1 MB
global media: 200 MB
per project: 20 MB
```

For production, back the PVC with storage that has explicit capacity limits,
monitoring, and backups. Object storage would be the preferred next step for a
larger production deployment, but a PVC is the minimal path for the assignment.
The example uses `ReadWriteMany` because API and worker pods share uploaded files.
If the cluster only supports `ReadWriteOnce`, run a single node/single replica or
move attachments to object storage.

## Secrets

Use Kubernetes `Secret` for:

- Django secret key.
- database URL and credentials.
- Redis URLs and credentials when applicable.
- SMTP host, port, and credentials.
- Cloudflare Tunnel token when using the tunnel example.

Use `ConfigMap` for non-secret settings such as allowed hosts, CORS origins,
attachment limits, and Django settings module.

Do not commit real secrets. `secret.example.yaml` exists only as a readable
template.

## Validation

Validate manifests before applying:

```bash
kubectl apply --dry-run=client -f deploy/k8s/
```

If `kubectl` is unavailable locally:

```bash
docker run --rm -v "$PWD/deploy/k8s:/work" ghcr.io/yannh/kubeconform:latest -summary /work
```
