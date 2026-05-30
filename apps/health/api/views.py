"""Health API views."""

from collections.abc import Callable

from django.conf import settings
from django.db import connection
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from redis import Redis
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from apps.api.responses import success_response


@extend_schema(responses={200: OpenApiTypes.OBJECT})
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def live_health(request: Request) -> Response:
    """Return the live health status."""
    return success_response({"status": "ok"})


@extend_schema(responses={200: OpenApiTypes.OBJECT, 503: OpenApiTypes.OBJECT})
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def ready_health(request: Request) -> Response:
    """Return readiness status for dependent services."""
    database_status = _dependency_status(_check_database)
    redis_status = _dependency_status(_check_redis)
    ready = database_status == "ok" and redis_status == "ok"
    response_status = status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return success_response(
        {
            "status": "ok" if ready else "error",
            "database": database_status,
            "redis": redis_status,
        },
        status_code=response_status,
    )


def _dependency_status(check: Callable[[], None]) -> str:
    """Return ok or error for one dependency check."""
    try:
        check()
    except Exception:
        return "error"
    return "ok"


def _check_database() -> None:
    """Verify the database accepts a simple query."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()


def _check_redis() -> None:
    """Verify Redis accepts a ping."""
    client = Redis.from_url(redis_readiness_url(), socket_connect_timeout=1, socket_timeout=1)
    try:
        client.ping()
    finally:
        client.close()


def redis_readiness_url() -> str:
    """Return the configured Redis readiness URL."""
    for setting_name in ("HEALTH_REDIS_URL", "REDIS_URL", "CELERY_BROKER_URL"):
        redis_url = str(getattr(settings, setting_name, ""))
        if redis_url:
            return redis_url
    return ""
