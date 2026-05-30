# Kubernetes Deployment

## Workloads

Kubernetes manifests should include:

```text
Deployment/api
Deployment/celery-worker
Deployment/celery-beat
StatefulSet or managed PostgreSQL reference
Redis service or managed Redis reference
Job/migrate
Service/api
Ingress/api
ConfigMap
Secret
PersistentVolumeClaim/media
```

## Probes

API deployment:

```text
livenessProbe:  /api/v1/health/live/
readinessProbe: /api/v1/health/ready/
```

## Migrations

Run migrations through a Kubernetes `Job`, not inside every API pod startup.

Justification: migration execution should be explicit and not race between replicas.

## Media Storage

Use a PVC for local-cluster deployments or object storage for production.

Set:

- PVC capacity limit for media.
- container ephemeral-storage requests and limits.
- application upload quotas.

## Secrets

Use Kubernetes `Secret` for:

- Django secret key.
- database credentials.
- SMTP credentials.
- Redis credentials when applicable.

Use `ConfigMap` for non-secret settings.
