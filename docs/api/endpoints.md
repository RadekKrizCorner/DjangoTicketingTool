# API Endpoints

## Users

```text
POST /api/v1/users/register/
POST /api/v1/users/token/
POST /api/v1/users/token/refresh/
POST /api/v1/users/token/verify/
POST /api/v1/users/logout/
GET  /api/v1/users/me/
GET  /api/v1/users/profile/
PATCH /api/v1/users/profile/
POST /api/v1/users/password/
POST /api/v1/users/password-reset/request/
POST /api/v1/users/password-reset/confirm/
GET  /api/v1/users/search/
```

Implemented in PROJECT-004. User search requires authentication and returns only:

```text
id
email
display_name
```

## Projects

```text
GET    /api/v1/projects/
POST   /api/v1/projects/
GET    /api/v1/projects/{project_id}/
PATCH  /api/v1/projects/{project_id}/
DELETE /api/v1/projects/{project_id}/
POST   /api/v1/projects/{project_id}/ownership-transfer/
POST   /api/v1/projects/{project_id}/close/
POST   /api/v1/projects/{project_id}/reopen/
PUT    /api/v1/projects/{project_id}/publish-schedule/
DELETE /api/v1/projects/{project_id}/publish-schedule/
PUT    /api/v1/projects/{project_id}/close-schedule/
DELETE /api/v1/projects/{project_id}/close-schedule/
GET    /api/v1/projects/{project_id}/audit-log/
```

## Members

```text
GET    /api/v1/projects/{project_id}/members/
POST   /api/v1/projects/{project_id}/members/
GET    /api/v1/projects/{project_id}/members/{membership_id}/
PATCH  /api/v1/projects/{project_id}/members/{membership_id}/
DELETE /api/v1/projects/{project_id}/members/{membership_id}/
```

## Tasks

```text
GET    /api/v1/projects/{project_id}/tasks/
POST   /api/v1/projects/{project_id}/tasks/
GET    /api/v1/projects/{project_id}/tasks/{task_id}/
PATCH  /api/v1/projects/{project_id}/tasks/{task_id}/
DELETE /api/v1/projects/{project_id}/tasks/{task_id}/
POST   /api/v1/projects/{project_id}/tasks/{task_id}/transition/
GET    /api/v1/tasks/my/
GET    /api/v1/tasks/due-soon/
```

Implemented in PROJECT-006. Task mutations require `owner`, `manager`, or
`member` role and are blocked after project closure.

## Comments

```text
GET    /api/v1/projects/{project_id}/tasks/{task_id}/comments/
POST   /api/v1/projects/{project_id}/tasks/{task_id}/comments/
GET    /api/v1/projects/{project_id}/tasks/{task_id}/comments/{comment_id}/
PATCH  /api/v1/projects/{project_id}/tasks/{task_id}/comments/{comment_id}/
DELETE /api/v1/projects/{project_id}/tasks/{task_id}/comments/{comment_id}/
```

Implemented in PROJECT-006. Members can comment on private projects. Public
projects can additionally allow all authenticated users through
`public_comment_policy=authenticated_users`.

## Attachments

```text
GET    /api/v1/projects/{project_id}/tasks/{task_id}/attachments/
POST   /api/v1/projects/{project_id}/tasks/{task_id}/attachments/
GET    /api/v1/projects/{project_id}/tasks/{task_id}/comments/{comment_id}/attachments/
POST   /api/v1/projects/{project_id}/tasks/{task_id}/comments/{comment_id}/attachments/
GET    /api/v1/attachments/{attachment_id}/download/
DELETE /api/v1/attachments/{attachment_id}/
```

Implemented in PROJECT-006. Downloads are authorized through the API and files
are not exposed directly from `MEDIA_URL`.

## Notifications

```text
GET  /api/v1/notifications/
POST /api/v1/notifications/{notification_id}/read/
POST /api/v1/notifications/read-all/
```

Implemented in PROJECT-007. Notification rows are user-scoped and scheduled jobs
create notifications idempotently through dedupe keys.

## Health

```text
GET /api/v1/health/live/
GET /api/v1/health/ready/
```
