# Attachments

## Scope

Attachments are available on both tasks and comments.

Primary use cases:

- Task screenshots.
- Comment screenshots.
- Plain text logs.

## Model

Use one `Attachment` model with exactly one parent:

```text
task_id OR comment_id
```

A database check constraint must enforce that one and only one parent is set.

Fields:

```text
parent task/comment
uploaded_by
original_filename
file
content_type
size_bytes
checksum_sha256
created_at
created_by
deleted_at
deleted_by
```

## Limits

```text
ATTACHMENT_MAX_FILE_SIZE_BYTES=1048576
ATTACHMENT_MAX_TOTAL_BYTES=209715200
ATTACHMENT_MAX_PROJECT_BYTES=20971520
```

## Allowed Types

```text
image/png
image/jpeg
text/plain
```

Allowed text extensions:

```text
.txt
.log
.out
.err
```

## Permissions

Task attachments:

- Read: anyone who can read the task.
- Upload: `owner`, `manager`, `member`.
- Delete own: uploader.
- Delete others: `owner`, `manager`.
- Blocked when project is closed.

Comment attachments:

- Read: anyone who can read the comment.
- Upload: anyone who can create the comment.
- Delete own: uploader.
- Delete others: `owner`, `manager`.
- Still allowed when project is closed.

Anonymous users cannot upload attachments.

## Download

Files must not be served through public `MEDIA_URL`.

Download endpoint:

```text
GET /api/v1/attachments/{attachment_id}/download/
```

The endpoint checks authorization before streaming the file.

## Host Protection

Application-level quotas prevent normal upload abuse. Production deployments should
also keep media on a dedicated filesystem, Docker volume, bind mount, or Kubernetes
PVC with a clear capacity limit.

This protects the host root filesystem from being filled by attachments.

## PROJECT-006 Implementation Notes

Attachment uploads validate all of the following before writing a row:

- Per-file size limit.
- Global active attachment quota.
- Per-project active attachment quota.
- Content type and text-file extension allow-list.
- Parent authorization for task or comment attachments.

Deleting an attachment is a soft delete so auditability is preserved.
