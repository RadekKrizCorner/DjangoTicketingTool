# Testing Strategy

## Test Types

Use three test categories. Unit and integration tests run in CI by default. E2E tests
are explicit because they require a running Docker Compose API endpoint.

| Type | Scope |
| --- | --- |
| Unit | Policies, task workflow, validators, quota calculations, selector filters. |
| Integration | Services + DB, API status codes, Celery eager tasks, email outbox, audit logs, quotas. |
| End-to-end | Docker Compose stack with real HTTP requests. |

## Markers

Planned pytest markers:

```text
unit
integration
e2e
```

Example commands:

```bash
docker compose run --rm api pytest -m unit -v
docker compose run --rm api pytest -m integration -v
docker compose up -d api celery-worker celery-beat mailpit
docker compose run --rm --no-deps \
  -e E2E_BASE_URL=http://host.docker.internal:8000 \
  -e E2E_HOST_HEADER=localhost \
  api pytest -m e2e -v
docker compose down
```

`E2E_BASE_URL` points from the test container to the running API. `E2E_HOST_HEADER`
keeps the request compatible with `DJANGO_ALLOWED_HOSTS` when Docker uses a bridge
hostname such as `host.docker.internal`. The E2E client also defaults this header
to `localhost` for `host.docker.internal` URLs.

## Parametrization

Use `pytest-kwparametrize` for finite behavior matrices.

Required matrices covered by the suite:

- project role vs action vs expected status
- task role vs action vs project state
- comment role vs author relation
- attachment parent vs role vs project state
- public/private visibility vs authentication state
- task status transition matrix
- attachment type and size validation
- quota validation
- password reset cases
- background job idempotency cases

All finite behavior matrices use `pytest.mark.kwparametrize` so each case names the
inputs and expected outcome directly.

## What Not To Test

Do not test Django or DRF internals.

Focus tests on:

- business rules
- permissions
- response contracts
- idempotency
- audit creation
- quota enforcement
- task workflow
- async side effects

## E2E Targets

End-to-end tests should cover:

- register, login, create project
- add member
- create task
- transition task
- comment with attachment
- schedule publish
- trigger due background job
- verify notification/email side effect

The current E2E suite covers registration, login, project creation, membership,
task creation, workflow transition, comment creation, comment attachment upload
and download, publish scheduling, anonymous/public endpoint boundaries, private
project access boundaries, public project comment policies, personal access token
scopes and revocation, advanced task filters, notification reads, project close
write-blocking, and reopen behavior. Deeper async side-effect checks stay in
integration tests because they can run deterministically with Celery eager mode.
