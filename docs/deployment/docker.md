# Docker Deployment

## Local Development

Final Compose stack should include:

```text
api
db
redis
celery-worker
celery-beat
mailpit
docs
```

The local development stack now includes all of these services. The API image is
built from the local `Dockerfile`, mounts the repository into `/app`, and stores
uploaded media in the `media` Docker volume.

The default Dockerfile target is the production runtime image and uses
`config.settings.production`. Docker Compose builds the `development` target and
overrides `DJANGO_SETTINGS_MODULE=config.settings.local` for local development.

## Application Image

After implementation, GitHub Actions will publish the application image to GHCR.

Expected tags:

```text
ghcr.io/<owner>/<repo>/api:<sha>
ghcr.io/<owner>/<repo>/api:latest
ghcr.io/<owner>/<repo>/api:<git-tag>
```

The package must be configured as public so a teacher can pull the image without
authentication.

## Release Compose

`docker-compose.release.yml` should use the published GHCR image instead of building
locally.

## Health Checks

Docker health check should call:

```text
/api/v1/health/live/
```

Readiness checks for dependent services use:

```text
/api/v1/health/ready/
```

The readiness response includes database and Redis status under `data` so
orchestrators can distinguish process health from dependency availability.
Redis readiness uses `HEALTH_REDIS_URL` when set, then falls back to `REDIS_URL`,
then `CELERY_BROKER_URL`.

## Storage Protection

Attachments must not share an unbounded host root filesystem path.

Recommended production Docker setup:

- store media on a dedicated bind mount or Docker volume
- monitor free space
- keep application quotas enabled
- configure backup strategy for media files

Application quotas:

```text
single file: 1 MB
global media: 200 MB
per project: 20 MB
```
