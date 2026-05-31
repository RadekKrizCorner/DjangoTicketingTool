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

GitHub Actions publishes the runtime application image to GHCR on pushes to
`master`, `main`, and `v*` tags. Pull requests build the image but do not push it.

Expected tags:

```text
ghcr.io/<owner>/<repo>/api:sha-<sha>
ghcr.io/<owner>/<repo>/api:latest
ghcr.io/<owner>/<repo>/api:<git-tag>
```

GHCR uses GitHub package visibility. After the first successful publish, open the
package settings in GitHub and change visibility to public. Once public, a teacher
can pull the image without authentication:

```bash
docker pull ghcr.io/<owner>/<repo>/api:latest
```

If the package stays private, pulling requires:

```bash
echo "$GITHUB_TOKEN" | docker login ghcr.io -u <github-user> --password-stdin
docker pull ghcr.io/<owner>/<repo>/api:latest
```

## Release Compose

`docker-compose.release.yml` uses the published GHCR image instead of building
locally. It includes API, Celery worker, Celery beat, PostgreSQL, Redis, Mailpit,
and a one-shot migration service.

Minimal release run:

```bash
export APP_IMAGE=ghcr.io/<owner>/<repo>/api:latest
export DJANGO_SECRET_KEY="$(openssl rand -hex 32)"
docker compose -f docker-compose.release.yml --profile tools run --rm migrate
docker compose -f docker-compose.release.yml up -d api celery-worker celery-beat
```

Use these variables to adapt the stack:

| Variable | Purpose |
| --- | --- |
| `APP_IMAGE` | Published API image tag. |
| `API_PORT` | Host port for the API, default `8000`. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames accepted by Django. |
| `DJANGO_CORS_ALLOWED_ORIGINS` | Comma-separated frontend origins. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated trusted HTTPS origins. |
| `DJANGO_SECURE_SSL_REDIRECT` | Set `true` behind HTTPS reverse proxy. |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | PostgreSQL credentials. |
| `EMAIL_HOST`, `EMAIL_PORT`, `DEFAULT_FROM_EMAIL` | SMTP delivery settings. |
| `APP_CONTAINER_STORAGE_LIMIT` | Docker writable-layer limit for app containers. |

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
- place that mount on a bounded filesystem, LVM volume, ZFS dataset, or cloud disk
- monitor free space
- keep application quotas enabled
- configure backup strategy for media files
- keep `storage_opt.size` enabled where the Docker storage driver supports it

Application quotas:

```text
single file: 1 MB
global media: 200 MB
per project: 20 MB
```

`storage_opt.size` protects the container writable layer when supported by the
Docker storage driver. It does not limit named volumes on every platform, so the
application quotas are the primary protection against attachment growth. For a real
server, mount `/app/media` on storage with an explicit capacity limit.
