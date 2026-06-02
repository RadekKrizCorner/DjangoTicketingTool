"""Prometheus metrics helpers for the project."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.db import DatabaseError
from prometheus_client import REGISTRY, Counter, Gauge, Histogram, generate_latest

LOW_LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
QUERY_BUCKETS = (0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5)

HTTP_REQUESTS = Counter(
    "django_http_requests",
    "Total Django HTTP requests.",
    ("route", "method", "status"),
)
HTTP_DURATION = Histogram(
    "django_http_request_duration_seconds",
    "Django HTTP request duration in seconds.",
    ("route", "method", "status"),
    buckets=LOW_LATENCY_BUCKETS,
)
DB_QUERIES = Counter(
    "django_db_queries",
    "Total ORM database queries observed during HTTP requests.",
    ("route", "operation", "status"),
)
DB_QUERY_DURATION = Histogram(
    "django_db_query_duration_seconds",
    "ORM database query duration in seconds.",
    ("route", "operation", "status"),
    buckets=QUERY_BUCKETS,
)
DB_SLOW_QUERIES = Counter(
    "django_db_slow_queries",
    "Total ORM database queries slower than the configured threshold.",
    ("route", "operation"),
)
ATTACHMENT_STORAGE_BYTES = Gauge(
    "django_attachment_storage_bytes",
    "Current active attachment storage usage in bytes.",
    ("scope",),
)
ATTACHMENT_QUOTA_BYTES = Gauge(
    "django_attachment_quota_bytes",
    "Configured attachment storage quota in bytes.",
    ("scope",),
)
ATTACHMENT_UPLOAD_REJECTIONS = Counter(
    "django_attachment_upload_rejections",
    "Total rejected attachment uploads.",
    ("reason",),
)
OBSERVABILITY_REFRESH_ERRORS = Counter(
    "django_observability_refresh_errors",
    "Total observability collector refresh failures.",
    ("collector",),
)


@dataclass(frozen=True)
class QuerySample:
    """Represent one database query measurement."""

    operation: str
    duration_seconds: float


def metrics_are_enabled() -> bool:
    """Return whether Prometheus metrics are enabled."""
    return bool(getattr(settings, "OBSERVABILITY_METRICS_ENABLED", False))


def route_name(request: Any) -> str:
    """Return a low-cardinality route name for a request."""
    resolver_match = getattr(request, "resolver_match", None)
    if resolver_match is None:
        return "unknown"
    if resolver_match.view_name:
        return resolver_match.view_name
    if resolver_match.url_name:
        return resolver_match.url_name
    return "unknown"


def classify_sql_operation(sql: str) -> str:
    """Return a low-cardinality SQL operation label."""
    operation = sql.lstrip().split(maxsplit=1)[0].lower() if sql else ""
    if operation in {"select", "insert", "update", "delete"}:
        return operation
    return "other"


def record_http_request(*, route: str, method: str, status: str, duration_seconds: float) -> None:
    """Record an HTTP request measurement."""
    HTTP_REQUESTS.labels(route=route, method=method.upper(), status=status).inc()
    HTTP_DURATION.labels(route=route, method=method.upper(), status=status).observe(
        duration_seconds
    )


def record_db_query(*, route: str, status: str, query: QuerySample) -> None:
    """Record a database query measurement."""
    DB_QUERIES.labels(route=route, operation=query.operation, status=status).inc()
    DB_QUERY_DURATION.labels(route=route, operation=query.operation, status=status).observe(
        query.duration_seconds
    )
    if query.duration_seconds >= settings.OBSERVABILITY_SLOW_QUERY_SECONDS:
        DB_SLOW_QUERIES.labels(route=route, operation=query.operation).inc()


def record_attachment_upload_rejection(*, reason: str) -> None:
    """Record a rejected attachment upload."""
    if metrics_are_enabled():
        ATTACHMENT_UPLOAD_REJECTIONS.labels(reason=reason).inc()


def refresh_attachment_storage_metrics() -> None:
    """Refresh attachment storage gauges from the database."""
    if not metrics_are_enabled():
        return

    from apps.attachments.services import total_attachment_bytes

    try:
        active_bytes = total_attachment_bytes()
    except DatabaseError:
        OBSERVABILITY_REFRESH_ERRORS.labels(collector="attachment_storage").inc()
        active_bytes = 0

    ATTACHMENT_STORAGE_BYTES.labels(scope="global").set(active_bytes)
    ATTACHMENT_QUOTA_BYTES.labels(scope="global").set(settings.ATTACHMENT_MAX_TOTAL_BYTES)
    ATTACHMENT_QUOTA_BYTES.labels(scope="project").set(settings.ATTACHMENT_MAX_PROJECT_BYTES)


def ensure_default_metrics() -> None:
    """Initialize zero-valued metric series for dashboard discovery."""
    HTTP_REQUESTS.labels(route="unknown", method="GET", status="200")
    HTTP_DURATION.labels(route="unknown", method="GET", status="200")
    DB_QUERIES.labels(route="unknown", operation="select", status="200")
    DB_QUERY_DURATION.labels(route="unknown", operation="select", status="200")
    DB_SLOW_QUERIES.labels(route="unknown", operation="select")
    ATTACHMENT_UPLOAD_REJECTIONS.labels(reason="file_too_large")
    OBSERVABILITY_REFRESH_ERRORS.labels(collector="attachment_storage")


def prometheus_payload() -> bytes:
    """Return the Prometheus text payload."""
    ensure_default_metrics()
    refresh_attachment_storage_metrics()
    return generate_latest(REGISTRY)
