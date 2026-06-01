# Product Specification

## Summary

Build a backend for a project management application with user accounts, project
membership, role-based permissions, tasks, task comments, attachments, notifications,
scheduled project publishing, scheduled project closing, deadline reminders, audit
logging, and deployment-ready documentation.

The API must be usable by a frontend or mobile client. It must use correct HTTP
status codes, consistent response structures, predictable error shapes, and strong
test coverage focused on application logic.

## Goals

- Provide JWT-based user authentication and profile management.
- Let authenticated users create and manage projects.
- Support project members with explicit roles: `owner`, `manager`, `member`, `viewer`.
- Support ownership transfer.
- Support tasks with an explicit workflow.
- Support task comments and attachments.
- Support scheduled background operations through Celery.
- Keep all domain data audit-friendly through soft delete and audit logs.
- Provide public OpenAPI schema and docs without exposing application data to anonymous users.
- Support local startup with Docker Compose.
- Support production deployment paths for Docker and Kubernetes.

## Non-Goals

- No frontend application.
- No anonymous access to project, task, comment, user, or membership data.
- No email verification before first login.
- No full SSO implementation in version 1.
- No generic file hosting.
- No Redis HA setup in local Docker Compose.
- No support guarantee for databases other than PostgreSQL.

## User Management

The `accounts` application owns users, local authentication, password reset, profile
data, and future SSO identity mapping.

### Decisions

- Use a custom user model from the beginning.
- Use unique email as the login identifier.
- Do not use `username`.
- Accounts are active immediately after registration.
- Add `ExternalIdentity` so future SSO can be added without changing project
  membership or permission models.
- Password reset is handled through email.
- Local email delivery uses Mailpit during development.
- Production email delivery is configured through SMTP environment variables.

### Justification

Email-first login matches frontend and mobile client expectations. A custom user
model avoids the high migration cost of replacing Django's default user later.
`ExternalIdentity` makes the domain ready for OIDC or SAML without implementing SSO
before it is needed.

### Alternatives

- Django default `username`: faster to start, but weaker for email-first and SSO-ready APIs.
- `django-allauth` now: useful for social login, but too much scope for version 1.
- Email verification before activation: stronger for public production, but not required here.

## Project Visibility

Anonymous users never see concrete project data.

`visibility=public` means the project is readable by authenticated users, never by
anonymous users.

Visibility rules:

- Anonymous user: only public API endpoints such as health, schema, docs, register,
  login, token refresh, and password reset.
- Authenticated user without access to a private project: `404`.
- Authenticated user reading a public project: allowed.
- Authenticated user writing to a project: role-based permission required.

## Project Roles

Roles are stored in `ProjectMembership` and include the owner.

| Role | Permissions |
| --- | --- |
| `owner` | Full project control, member management, role changes, ownership transfer, delete, schedule publish/close, manual close/reopen, audit log access. |
| `manager` | Manage tasks, comments, and attachments within project rules. Cannot manage members or delete project. |
| `member` | Read project, comment, manage own task workflow within allowed transitions, upload allowed attachments when permitted. |
| `viewer` | Read-only member. Can read and comment where comments are allowed, but cannot upload task attachments or modify tasks. |

The project has exactly one owner. `Project.owner` must match the active membership
record with `role=owner`.

### Ownership Transfer

Endpoint:

```text
POST /api/v1/projects/{project_id}/ownership-transfer/
```

The old owner becomes `manager`. The new owner becomes `owner`. `Project.owner` and
membership roles change in one transaction.

## Project Lifecycle

Projects have independent visibility and lifecycle state.

```text
visibility: private | public
state: active | closed
publish_at, published_at
close_at, closed_at
```

Lifecycle operations:

```text
PUT    /api/v1/projects/{project_id}/publish-schedule/
DELETE /api/v1/projects/{project_id}/publish-schedule/
PUT    /api/v1/projects/{project_id}/close-schedule/
DELETE /api/v1/projects/{project_id}/close-schedule/
POST   /api/v1/projects/{project_id}/close/
POST   /api/v1/projects/{project_id}/reopen/
```

Rules:

- `publish_at` and `close_at` must be timezone-aware ISO 8601 timestamps.
- API and database use UTC.
- `close_at` must be after `publish_at` when both are set.
- Closing prevents task create/update/delete.
- Reopen is allowed for owner or Django staff.
- Reopen clears `closed_at` and `close_at`.
- Manual close clears `close_at`.
- Schedule cancellation changes future plans only; it does not undo already applied states.

## Task Workflow

Tasks use a workflow instead of free status changes.

Statuses:

```text
new | accepted | in_progress | on_hold | completed | cancelled
```

Allowed transitions:

| Current | Allowed targets |
| --- | --- |
| `new` | `accepted`, `cancelled` |
| `accepted` | `in_progress`, `on_hold`, `cancelled` |
| `in_progress` | `on_hold`, `completed`, `cancelled` |
| `on_hold` | `in_progress`, `cancelled` |
| `completed` | `accepted` |
| `cancelled` | `accepted` |

Transition endpoint:

```text
POST /api/v1/projects/{project_id}/tasks/{task_id}/transition/
```

Body:

```json
{
  "status": "in_progress",
  "note": "Starting work"
}
```

Rules:

- Assignee must be an active project member and cannot be `viewer`.
- `owner` and `manager` can create and manage tasks.
- `member` can transition own assigned tasks only through allowed transitions.
- `viewer` can read only.
- Closed projects block task changes.
- Reopening `completed` or `cancelled` tasks is allowed only for `owner` or `manager`.

## Comments

Task comments are supported.

Rules:

- Anyone with access to a project can read comments.
- Members can comment on private projects.
- Public projects can allow all authenticated users to comment through
  `public_comment_policy=authenticated_users`.
- Anonymous users cannot comment.
- Commenting remains allowed after project close.
- Authors can edit/delete their own comments.
- `owner` and `manager` can delete other users' comments.

## Attachments

Attachments are supported for both tasks and comments.

Supported use cases:

- Screenshots.
- Plain text logs.

Limits:

```text
ATTACHMENT_MAX_FILE_SIZE_BYTES=1048576
ATTACHMENT_MAX_TOTAL_BYTES=209715200
ATTACHMENT_MAX_PROJECT_BYTES=20971520
```

Allowed content types:

```text
image/png
image/jpeg
text/plain
```

Allowed text file extensions:

```text
.txt
.log
.out
.err
```

Rules:

- One file per upload request.
- No anonymous uploads.
- Files are downloaded through authorized API endpoints, not public media URLs.
- Task attachments are blocked after project close.
- Comment attachments remain allowed after project close.
- Attachment records are soft-deleted.
- Files are retained for audit.
- Uploads are quota checked before saving.

## Notifications And Emails

Use both in-app notifications and email delivery records.

Models:

```text
Notification
EmailDelivery
```

Uses:

- Project published notification and email to members.
- Task deadline reminder notification and email to assignee.
- Task watcher notifications and email delivery for task and comment changes.
- Password reset email.

`EmailDelivery` acts as an outbox for audit and deduplication.

## Async Operations

Celery is used for background jobs. Redis is used as the local broker.

Jobs:

- `publish_due_projects`
- `close_due_projects`
- `send_deadline_reminders`
- `send_pending_emails`

All background jobs must be idempotent.

Mechanisms:

- `transaction.atomic()`
- row locking for due work
- state guards such as `published_at IS NULL`
- `Notification.dedupe_key`
- unique email delivery records
- audit log idempotency keys for system jobs

Deadline reminder behavior:

- Celery Beat runs the check every 15 minutes.
- Remind when `due_at <= now + 24h`.
- Exclude tasks with status `completed` or `cancelled`.
- Exclude closed projects.
- Dedupe key includes task id and due date, so changing the deadline can generate
  a new reminder.

## Audit And Soft Delete

All important domain entities are audit-friendly.

Audit fields:

```text
created_at
created_by
updated_at
updated_by
deleted_at
deleted_by
```

Soft delete applies to:

- Project
- ProjectMembership
- Task
- TaskComment
- Attachment
- Notification

Users are deactivated through `is_active=false` rather than deleted through public API.
Email delivery records are not normally deleted.

Audit log:

```text
AuditLog
  actor
  action
  entity_type
  entity_id
  project
  before
  after
  metadata
  ip_address
  user_agent
  idempotency_key
  created_at
```

Project audit logs are readable only by the project owner.

## API Contract

Base path:

```text
/api/v1/
```

Success response:

```json
{
  "data": {}
}
```

List response:

```json
{
  "data": [],
  "meta": {
    "pagination": {
      "count": 100,
      "page": 1,
      "page_size": 20,
      "total_pages": 5,
      "next": null,
      "previous": null
    }
  }
}
```

Error response:

```json
{
  "errors": [
    {
      "code": "project_closed",
      "detail": "Tasks cannot be modified after project is closed.",
      "field": null
    }
  ]
}
```

Status codes:

| Status | Meaning |
| --- | --- |
| `200` | Read or update succeeded. |
| `201` | Resource created. |
| `202` | Async or email request accepted. |
| `204` | Delete succeeded. |
| `400` | Validation error. |
| `401` | Anonymous user must authenticate. |
| `403` | Authenticated user lacks permission on visible resource. |
| `404` | Missing resource or private resource without access. |
| `409` | Valid request conflicts with current state. |

Pagination:

- Page-number pagination.
- Default `page_size=20`.
- Maximum `page_size=100`.
- Stable default ordering, usually `-created_at, id`.

## API Schema

The OpenAPI specification is public.

```text
/api/v1/schema/
/api/v1/docs/
/api/v1/redoc/
```

The schema exposes API contracts, not application data.

## Filtering And Ordering

Use explicit filter sets.

Examples:

```text
GET /api/v1/projects/?visibility=public&role=owner&search=crm&ordering=-created_at
GET /api/v1/projects/{project_id}/tasks/?status=accepted&assignee_id=1&ordering=due_at
GET /api/v1/tasks/my/?status=in_progress&due_before=2026-06-30T23:59:59Z
GET /api/v1/notifications/?is_read=false
```

Only whitelisted fields can be used for filtering and ordering.

## Database

PostgreSQL is the only officially supported database; code is ORM-only but
MySQL/MariaDB are not guaranteed without extra CI matrix.

Primary keys use integer `BigAutoField`, not UUID.

## Redis

Local development uses a single Redis instance.

Production documentation describes Redis Sentinel as the HA path. Redis Cluster is
not part of version 1.

## Testing

Test categories:

- Unit tests for policies, workflow transitions, validators, quota calculation, and selectors.
- Integration tests for service layer, database behavior, API status codes, Celery eager tasks, email outbox, audit logs, and quotas.
- End-to-end tests against the Docker Compose stack through real HTTP calls.

Use `pytest-kwparametrize` for finite matrices such as roles, actions, workflow states,
project states, and expected responses.

## Deployment

Supported deployment paths:

- Local Docker Compose.
- Public GHCR application image after implementation.
- Kubernetes manifests.
- Cloudflare Tunnel for deployments without a public IP address.

Docker and Kubernetes health checks use:

```text
/api/v1/health/live/
/api/v1/health/ready/
```

## Milestone Commits

Each milestone must be a single commit with a Jira-style message.

Planned structure:

```text
RKRIZ-001 Add product specification documentation
RKRIZ-002 Bootstrap dockerized Django project
RKRIZ-003 Add JWT user management and password reset
RKRIZ-004 Add project membership permissions
RKRIZ-005 Add task workflow, comments, and attachments
RKRIZ-006 Add Celery scheduled project jobs
RKRIZ-007 Add notifications, email delivery, and audit log
RKRIZ-008 Add unit, integration, and e2e test coverage
RKRIZ-009 Add GHCR image publishing workflow
RKRIZ-010 Add Kubernetes and deployment docs
```

The exact implementation plan will be generated after this product specification is
reviewed and approved.
