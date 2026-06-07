# Observability

## Logging

Logs should be structured and JSON-ready.

Required fields:

```text
request_id
user_id
method
path
status_code
latency_ms
ip
user_agent
```

Celery logs should include:

```text
task_id
task_name
job_type
entity_id
duration_ms
status
```

## Request ID

Every request should receive or preserve a request id.

Preferred header:

```text
X-Request-ID
```

## Future Logfire Compatibility

The logging format should stay vendor-neutral so Pydantic Logfire can be added later.

## Prometheus Metrics

Production metrics are exposed by Django at:

```text
/internal/metrics/
```

The endpoint is disabled unless `OBSERVABILITY_METRICS_ENABLED=true`. In release,
Nginx still returns `404` for public `/internal/metrics/` traffic, so Prometheus
scrapes the API container directly through the internal Docker network:

```text
api:8000/internal/metrics/
```

This keeps route names, status rates, query timings, and storage usage out of the
public web surface.

## Metric Rules

Metric labels must stay low-cardinality:

```text
route
method
status
operation
reason
scope
```

Never use user IDs, project IDs, task IDs, attachment IDs, raw paths, raw SQL,
email addresses, filenames, tokens, or request payload values as labels.

## Application Metrics

The Django metrics include:

```text
django_http_requests_total
django_http_request_duration_seconds
django_db_queries_total
django_db_query_duration_seconds
django_db_slow_queries_total
django_attachment_storage_bytes
django_attachment_quota_bytes
django_attachment_upload_rejections_total
```

Slow queries are counted when ORM query duration is greater than or equal to
`OBSERVABILITY_SLOW_QUERY_SECONDS`, default `0.5`.

## Monitoring Stack

The optional release monitoring overlay adds:

```text
prometheus
grafana
postgres-exporter
redis-exporter
celery-exporter
node-exporter
cadvisor
cloudflared
```

Prometheus retention is bounded by `PROMETHEUS_RETENTION_TIME` and
`PROMETHEUS_RETENTION_SIZE`, defaulting to `7d` and `512MB`. This protects small
hosts such as Raspberry Pi deployments from unbounded time-series storage growth.

## Grafana Dashboards

Grafana is provisioned from files in git:

```text
deploy/monitoring/grafana/provisioning/
deploy/monitoring/grafana/dashboards/
```

Initial dashboards:

```text
API Overview
Database Performance
Async Jobs
Infrastructure
```

The dashboards focus on request rate, latency, error rate, slow queries, database
health, Celery visibility, host health, container resource usage, and attachment
quota pressure.

## Cloudflare Access

Grafana is intended to be available at:

```text
https://grafana.radekkriz.space
```

Cloudflare Access should protect the whole hostname with an email allowlist for
reviewers. Grafana anonymous access is acceptable for this public demo because
the stack contains no production data, but Grafana must not be exposed directly
on a public host port. The release compose overlay binds Grafana only to
`127.0.0.1` for local admin access and supports a `cloudflared` container for
the public Access-protected route.

## Django Debug Toolbar

Django Debug Toolbar is intentionally not part of production observability. It is
useful for local debugging, but it exposes too much internal request and SQL
detail for a public demo deployment. Production performance inspection should go
through Prometheus metrics and Grafana dashboards.
