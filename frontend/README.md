# RKRIZ Workspace Frontend

React/Vite UI for the Django ticketing backend.

## Scripts

```bash
npm run dev -- --host 127.0.0.1
npm run build
npm run lint
npm test
```

The app runs in demo mode by default so the UI can be reviewed without a live Django
server. To use the real API, create a local env file and set:

```bash
VITE_DEMO_MODE=live
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

## Coverage

The UI covers the current backend scenarios:

- authentication, registration, logout, password reset, password change, and profile timezone
- project list/filter/create/delete, membership management, ownership transfer, lifecycle scheduling, close/reopen, audit log
- task board, task create/update/delete, assignment, watch/unwatch, allowed workflow transitions
- task comments, comment deletion, task/comment attachments, attachment deletion/download, attachment limits
- my tasks, due-soon tasks, notifications, mark read, and mark all read
