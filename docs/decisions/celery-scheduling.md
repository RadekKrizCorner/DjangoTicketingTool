# Decision: Celery Scheduling

## Decision

Use Celery with database-backed scheduling state.

Do not rely on long-running ETA tasks for project publishing or project closing.

## Justification

Publishing and closing are business states, so their schedule must live in the
database:

```text
publish_at
published_at
close_at
closed_at
```

Celery Beat periodically checks for due work and calls idempotent services.

This makes the system easier to inspect, retry, test, and recover. If a worker is
down, due projects are still present in the database and will be processed on the
next run.

## Alternatives

### Long ETA Celery Tasks

Rejected for project publish/close.

They are simpler to enqueue, but harder to inspect and less reliable for long-term
business scheduling.

### Cron Only

Rejected as the only solution.

Cron can trigger management commands, but Celery gives a consistent background job
model for publish, close, deadline reminders, and email delivery.

### External Scheduler

Rejected for version 1.

External schedulers are useful in larger systems, but they add deployment complexity
that is unnecessary for this assignment.

## Idempotency

All scheduled jobs must be safe to run more than once.

Mechanisms:

- transaction boundaries
- row locks for due work
- state guards
- dedupe keys
- unique email delivery rows
- audit log idempotency keys

Email delivery is outbox-based. SMTP cannot guarantee perfect exactly-once behavior
if the process crashes after sending but before recording success, but duplicate risk
is minimized through persisted delivery state.
