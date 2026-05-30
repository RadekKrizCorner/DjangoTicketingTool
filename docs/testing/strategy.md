# Testing Strategy

## Test Types

Use three test categories.

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

Example commands after implementation:

```bash
pytest -m unit
pytest -m integration
pytest -m e2e
pytest
```

## Parametrization

Use `pytest-kwparametrize` for finite behavior matrices.

Required matrices:

- project role vs action vs expected status
- task status transition matrix
- assignee and actor role matrix
- project state vs task write behavior
- attachment type and size validation
- quota validation
- password reset cases
- public/private visibility cases
- background job idempotency cases

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
