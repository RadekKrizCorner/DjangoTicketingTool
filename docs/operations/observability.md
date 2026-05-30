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

## Future Prometheus Compatibility

Prometheus compatibility should be implemented through metrics, not logs.

Future option:

```text
/metrics
```

with `django-prometheus` or equivalent instrumentation.