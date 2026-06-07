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

Create deterministic demo data after migrations:

```bash
docker compose run --rm api python manage.py seed_demo_data
```

The command creates the predefined superuser
`demo.admin@example.com` / `DemoAdmin123!` and demo users, projects,
memberships, tasks, comments, text attachments, and notifications. Override the
credentials with `DEMO_SUPERUSER_EMAIL`, `DEMO_SUPERUSER_PASSWORD`,
`DEMO_SUPERUSER_DISPLAY_NAME`, and `DEMO_USER_PASSWORD`.

The public homepage links to `/docs/`. In local development, Django redirects
that path to the MkDocs service at `http://localhost:8001/`. In release, Nginx
serves `/docs/` directly from the web image.

The default Dockerfile target is the production runtime image and uses
`config.settings.production`. Docker Compose builds the `development` target and
overrides `DJANGO_SETTINGS_MODULE=config.settings.local` for local development.

## Release Images

GitHub Actions publishes multi-arch runtime images to GHCR on pushes to
`master`, `main`, and `v*` tags. Pull requests and pushes to `release` build the
images but do not push them.

Expected tags:

```text
ghcr.io/<owner>/<repo>/api:sha-<sha>
ghcr.io/<owner>/<repo>/api:latest
ghcr.io/<owner>/<repo>/api:<git-tag>
ghcr.io/<owner>/<repo>/web:sha-<sha>
ghcr.io/<owner>/<repo>/web:latest
ghcr.io/<owner>/<repo>/web:<git-tag>
```

The API image runs Django/Gunicorn and collects static files during the image
build. The web image is built from `Dockerfile.web`; it builds MkDocs and the
React workspace UI, serves `/docs/` and `/ui/` directly through Nginx, and proxies
the remaining traffic to Django.

GHCR uses GitHub package visibility. After the first successful publish, open the
package settings in GitHub and change visibility to public. Once public, a teacher
can pull both images without authentication:

```bash
docker pull ghcr.io/radekkrizcorner/djangoticketingtool/api:latest
docker pull ghcr.io/radekkrizcorner/djangoticketingtool/web:latest
```

If the package stays private, pulling requires:

```bash
echo "$GITHUB_TOKEN" | docker login ghcr.io -u <github-user> --password-stdin
docker pull ghcr.io/radekkrizcorner/djangoticketingtool/api:latest
docker pull ghcr.io/radekkrizcorner/djangoticketingtool/web:latest
```

## Release Compose

`docker-compose.release.yml` uses the published GHCR images instead of building
locally. It includes Nginx web edge, API, Celery worker, Celery beat, PostgreSQL,
Redis, Mailpit, and a one-shot migration service. The `web` service is the only
service with a public port. API and Mailpit stay internal to the Compose network.

Minimal release run:

```bash
cp .env_template .env
# edit .env and replace secrets before starting the stack
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

Seed release demo data after migrations:

```bash
docker compose -f docker-compose.release.yml --profile tools run --rm seed-demo
```

On Linux hosts where the Docker storage driver supports writable-layer quotas,
run the same commands with the storage override:

```bash
docker compose -f docker-compose.release.yml -f docker-compose.release.storage.yml --profile tools run --rm migrate
docker compose -f docker-compose.release.yml -f docker-compose.release.storage.yml up -d web api celery-worker celery-beat
```

The storage override is separate because Docker Desktop, Rancher Desktop, and
some VPS storage drivers reject `storage_opt.size`. Application quotas remain
enabled in both modes and are the primary attachment protection.

Enable production monitoring with the monitoring overlay:

```bash
docker compose \
  -f docker-compose.release.yml \
  -f docker-compose.release.monitoring.yml \
  --profile monitoring \
  up -d web api celery-worker celery-beat prometheus grafana postgres-exporter redis-exporter celery-exporter node-exporter cadvisor
```

Grafana binds to `127.0.0.1:${GRAFANA_LOCAL_PORT:-3000}` for local admin access.
Prometheus and all exporters stay internal to the Compose network.
Before rolling out a Grafana major-version upgrade, back up the `grafana_data`
volume because Grafana may migrate dashboard and folder metadata on startup.

To publish Grafana through Cloudflare Access, configure
`grafana.radekkriz.space` in Cloudflare Zero Trust, set `CLOUDFLARED_TOKEN`, and
start the Cloudflare profile as well:

```bash
docker compose \
  -f docker-compose.release.yml \
  -f docker-compose.release.monitoring.yml \
  --profile monitoring \
  --profile cloudflare \
  up -d grafana prometheus cloudflared
```

The tunnel should route `grafana.radekkriz.space` to:

```text
http://grafana:3000
```

The public homepage shows the Monitoring link when `PUBLIC_GRAFANA_URL` is set.
Use `https://grafana.radekkriz.space` for the public demo.

For direct HTTP on port `48137`, keep `DJANGO_SECURE_SSL_REDIRECT=false`. If
`radekkriz.space` or `www.radekkriz.space` is terminated through HTTPS before this Compose stack, set
`DJANGO_SECURE_SSL_REDIRECT=true` and keep
`DJANGO_CSRF_TRUSTED_ORIGINS=https://radekkriz.space,https://www.radekkriz.space`.

Use these variables to adapt the stack:

| Variable | Purpose |
| --- | --- |
| `APP_IMAGE` | Published API image tag. |
| `WEB_IMAGE` | Published Nginx/MkDocs web image tag. |
| `PUBLIC_PORT` | Single public host port for the web edge, default `48137`. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames accepted by Django. |
| `DJANGO_CORS_ALLOWED_ORIGINS` | Comma-separated frontend origins. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated trusted HTTPS origins. |
| `DJANGO_SECURE_SSL_REDIRECT` | Set `true` behind HTTPS reverse proxy. |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | PostgreSQL credentials. |
| `EMAIL_HOST`, `EMAIL_PORT`, `DEFAULT_FROM_EMAIL` | SMTP delivery settings. |
| `DEMO_SUPERUSER_EMAIL`, `DEMO_SUPERUSER_PASSWORD`, `DEMO_SUPERUSER_DISPLAY_NAME` | Demo superuser credentials used by `seed_demo_data`. |
| `DEMO_USER_PASSWORD` | Password assigned to generated non-staff demo users. |
| `PUBLIC_GRAFANA_URL` | Public Cloudflare Access protected Grafana URL shown on the homepage. |
| `OBSERVABILITY_METRICS_ENABLED` | Enables the internal Django Prometheus endpoint. |
| `OBSERVABILITY_SLOW_QUERY_SECONDS` | ORM query duration threshold for slow-query counters. |
| `PROMETHEUS_RETENTION_TIME` | Prometheus retention by time, default `7d`. |
| `PROMETHEUS_RETENTION_SIZE` | Prometheus retention by size, default `512MB`. |
| `GRAFANA_ADMIN_USER`, `GRAFANA_ADMIN_PASSWORD` | Grafana admin credentials. |
| `GRAFANA_LOCAL_PORT` | Loopback-only Grafana port for local admin access. |
| `GRAFANA_ANONYMOUS_ENABLED` | Enables read-only Grafana access after Cloudflare Access. |
| `CLOUDFLARED_TOKEN` | Cloudflare Tunnel token for the Grafana hostname. |
| `CLOUDFLARED_IMAGE` | Cloudflared image override. |
| `CELERY_EXPORTER_IMAGE` | Celery exporter image override. |
| `APP_CONTAINER_STORAGE_LIMIT` | Docker writable-layer limit for app containers when the storage override is used. |
| `WEB_CONTAINER_STORAGE_LIMIT` | Docker writable-layer limit for the web edge when the storage override is used. |
| `DB_CONTAINER_STORAGE_LIMIT` | Docker writable-layer limit for PostgreSQL when the storage override is used. |
| `REDIS_CONTAINER_STORAGE_LIMIT` | Docker writable-layer limit for Redis when the storage override is used. |
| `MAILPIT_CONTAINER_STORAGE_LIMIT` | Docker writable-layer limit for Mailpit when the storage override is used. |

## Raspberry, VPS, and Cloudflare Tunnel

The release stack is suitable for a small VPS or Raspberry Pi because only one
host port is exposed:

```text
http://<host>:48137/
http://<host>:48137/ui/
http://<host>:48137/api/v1/docs/
http://<host>:48137/docs/
http://<host>:48137/admin/
```

When the server has no public IP address, run Cloudflare Tunnel on the host and
route the public hostname to the local release port:

```bash
cloudflared tunnel route dns <tunnel-name> radekkriz.space
cloudflared tunnel route dns <tunnel-name> www.radekkriz.space
cloudflared tunnel run <tunnel-name>
```

The tunnel ingress target should be:

```yaml
service: http://127.0.0.1:48137
```

For Kubernetes, use the manifests in `deploy/k8s/` when a cluster is available.
The same GHCR API image is used by the Django and Celery workloads. Cloudflare
Tunnel can also be deployed in-cluster with
`deploy/k8s/cloudflared-deployment.example.yaml`.

## Raspberry Pi Production Deploy

Use the release Compose stack on the Raspberry Pi. The Pi needs Docker Compose,
outbound internet access, and persistent Docker volumes.

1. Create a deployment directory:

```bash
mkdir -p ~/django-ticketing-tool
cd ~/django-ticketing-tool
```

2. Download the release Compose files from the repository:

```bash
curl -fsSLO https://raw.githubusercontent.com/RadekKrizCorner/DjangoTicketingTool/master/docker-compose.release.yml
curl -fsSLO https://raw.githubusercontent.com/RadekKrizCorner/DjangoTicketingTool/master/docker-compose.release.storage.yml
curl -fsSLO https://raw.githubusercontent.com/RadekKrizCorner/DjangoTicketingTool/master/.env_template
```

3. Create `.env`:

```bash
cp .env_template .env
nano .env
```

Generate secrets on the Pi:

```bash
openssl rand -hex 32
openssl rand -base64 32
```

4. Pull images and migrate:

```bash
docker compose -f docker-compose.release.yml pull
docker compose -f docker-compose.release.yml --profile tools run --rm migrate
docker compose -f docker-compose.release.yml --profile tools run --rm seed-demo
```

5. Start the production stack:

```bash
docker compose -f docker-compose.release.yml up -d web api celery-worker celery-beat
docker compose -f docker-compose.release.yml ps
```

6. Verify locally on the Pi:

```bash
curl -fsS http://127.0.0.1:48137/api/v1/health/live/
curl -fsS http://127.0.0.1:48137/
curl -fsS http://127.0.0.1:48137/docs/
```

7. Expose it to the internet.

If the Pi has a public IP or router port forwarding, forward external TCP port
`48137` to the Pi port `48137` and point `radekkriz.space` and
`www.radekkriz.space` DNS to the public IP.

If the Pi has no public IP, use Cloudflare Tunnel:

```bash
cloudflared tunnel login
cloudflared tunnel create django-ticketing-tool
cloudflared tunnel route dns django-ticketing-tool radekkriz.space
cloudflared tunnel route dns django-ticketing-tool www.radekkriz.space
```

Create `~/.cloudflared/config.yml`:

```yaml
tunnel: django-ticketing-tool
credentials-file: /home/pi/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: radekkriz.space
    service: http://127.0.0.1:48137
  - hostname: www.radekkriz.space
    service: http://127.0.0.1:48137
  - service: http_status:404
```

Run it as a service:

```bash
sudo cloudflared service install
sudo systemctl enable --now cloudflared
```

When HTTPS is terminated by Cloudflare Tunnel, set these values in `.env` and
restart:

```env
DJANGO_SECURE_SSL_REDIRECT=true
DJANGO_CSRF_TRUSTED_ORIGINS=https://radekkriz.space,https://www.radekkriz.space
```

```bash
docker compose -f docker-compose.release.yml up -d
```

## Updating Raspberry Pi Production

After pushing changes to GitHub, wait for the GitHub Actions image publishing job
to finish. Then update the Pi:

```bash
cd ~/django-ticketing-tool
docker compose -f docker-compose.release.yml pull
docker compose -f docker-compose.release.yml --profile tools run --rm migrate
docker compose -f docker-compose.release.yml up -d web api celery-worker celery-beat
docker image prune -f
```

With monitoring enabled, include the monitoring overlay during updates:

```bash
docker compose -f docker-compose.release.yml -f docker-compose.release.monitoring.yml pull
docker compose -f docker-compose.release.yml -f docker-compose.release.monitoring.yml --profile tools run --rm migrate
docker compose -f docker-compose.release.yml -f docker-compose.release.monitoring.yml --profile monitoring up -d web api celery-worker celery-beat prometheus grafana postgres-exporter redis-exporter celery-exporter node-exporter cadvisor
```

For safer releases, use immutable tags instead of `latest`:

```env
APP_IMAGE=ghcr.io/radekkrizcorner/djangoticketingtool/api:sha-<commit>
WEB_IMAGE=ghcr.io/radekkrizcorner/djangoticketingtool/web:sha-<commit>
```

Rollback is the same operation with the previous known-good image tags in `.env`.

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

Prometheus scrapes the same running API container through `/internal/metrics/`.
The release Nginx gateway blocks that path publicly, so health checks and metrics
have separate exposure rules.

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
