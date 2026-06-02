"""Django middleware for Prometheus request and database metrics."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from django.db import connection
from django.http import HttpRequest, HttpResponse

from apps.observability import metrics


class ObservabilityMiddleware:
    """Record low-cardinality HTTP and ORM metrics."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """Store the next middleware or view callable."""
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Record request duration and database query measurements."""
        if not metrics.metrics_are_enabled():
            return self.get_response(request)

        started_at = time.monotonic()
        query_samples: list[metrics.QuerySample] = []
        status = "500"

        def execute_wrapper(
            execute: Callable[..., Any],
            sql: str,
            params: Any,
            many: bool,
            context: dict[str, Any],
        ) -> Any:
            """Measure one ORM query execution."""
            query_started_at = time.monotonic()
            try:
                return execute(sql, params, many, context)
            finally:
                query_samples.append(
                    metrics.QuerySample(
                        operation=metrics.classify_sql_operation(sql),
                        duration_seconds=time.monotonic() - query_started_at,
                    )
                )

        try:
            with connection.execute_wrapper(execute_wrapper):
                response = self.get_response(request)
            status = str(response.status_code)
            return response
        finally:
            route = metrics.route_name(request)
            duration_seconds = time.monotonic() - started_at
            metrics.record_http_request(
                route=route,
                method=request.method,
                status=status,
                duration_seconds=duration_seconds,
            )
            for query in query_samples:
                metrics.record_db_query(route=route, status=status, query=query)
