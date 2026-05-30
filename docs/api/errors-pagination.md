# Errors And Pagination

## Error Shape

All errors use the same response shape.

```json
{
  "errors": [
    {
      "code": "attachment_too_large",
      "detail": "Attachment size must not exceed 1 MB.",
      "field": "file"
    }
  ]
}
```

## Error Codes

Initial registry:

```text
authentication_required
permission_denied
not_found
validation_error
invalid_role
owner_required
project_closed
invalid_schedule
invalid_transition
quota_exceeded
attachment_too_large
unsupported_attachment_type
duplicate_membership
email_already_registered
password_reset_invalid
conflict
```

## Status Codes

| Status | Usage |
| --- | --- |
| `200` | Successful read or update. |
| `201` | Resource created. |
| `202` | Async request accepted, such as password reset request. |
| `204` | Soft delete completed, no response body. |
| `400` | Request validation failed. |
| `401` | Authentication is required. |
| `403` | Authenticated user lacks permission for visible resource. |
| `404` | Resource does not exist or private resource is hidden. |
| `409` | Request conflicts with current resource state. |
| `429` | Request throttled. |

## Pagination

Use page-number pagination.

Request:

```text
GET /api/v1/projects/?page=2&page_size=20
```

Response:

```json
{
  "data": [],
  "meta": {
    "pagination": {
      "count": 134,
      "page": 2,
      "page_size": 20,
      "total_pages": 7,
      "next": "http://localhost:8000/api/v1/projects/?page=3&page_size=20",
      "previous": "http://localhost:8000/api/v1/projects/?page=1&page_size=20"
    }
  }
}
```

Rules:

- Default `page_size=20`.
- Maximum `page_size=100`.
- Invalid `page` or `page_size` returns `400`.
- Default ordering must be stable, usually `-created_at, id`.

## Paginated Endpoints

```text
/api/v1/projects/
/api/v1/projects/{project_id}/members/
/api/v1/projects/{project_id}/tasks/
/api/v1/projects/{project_id}/tasks/{task_id}/comments/
/api/v1/projects/{project_id}/tasks/{task_id}/attachments/
/api/v1/projects/{project_id}/tasks/{task_id}/comments/{comment_id}/attachments/
/api/v1/projects/{project_id}/audit-log/
/api/v1/tasks/my/
/api/v1/tasks/due-soon/
/api/v1/notifications/
/api/v1/users/search/
```

## Non-Paginated Endpoints

```text
/api/v1/users/me/
/api/v1/users/profile/
/api/v1/health/live/
/api/v1/health/ready/
/api/v1/schema/
/api/v1/docs/
/api/v1/redoc/
/api/v1/projects/{project_id}/
```
