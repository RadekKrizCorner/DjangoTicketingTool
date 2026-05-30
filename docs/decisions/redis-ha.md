# Decision: Redis HA

## Local Decision

Local development uses a single Redis container.

## Production HA Plan

For high availability, use Redis Sentinel:

- 1 Redis master.
- 2 Redis replicas.
- 3 Sentinel nodes.
- Celery broker URL using `sentinel://`.
- Celery transport option `master_name`.

Example shape:

```text
CELERY_BROKER_URL=sentinel://redis-sentinel-1:26379;sentinel://redis-sentinel-2:26379;sentinel://redis-sentinel-3:26379
CELERY_BROKER_TRANSPORT_OPTIONS={"master_name": "mymaster"}
```

## Justification

Sentinel provides failover for a single Redis primary pattern and matches Celery's
Redis Sentinel support.

## Alternatives

### RabbitMQ HA

Good alternative for a production-grade Celery broker. It may be more robust as a
broker than Redis, but it adds operational complexity.
