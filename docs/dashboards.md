# Configurable Dashboards

The Dashboards workspace provides Jira-style configurable dashboards for project
and task reporting. Users can create their own dashboards, add predefined
widgets, save a bounded grid layout, apply temporary viewing filters, and share
dashboards with selected people or dynamic project-member groups.

## Access Model

Dashboards have three effective access levels:

| Access | Permissions |
| --- | --- |
| `owner` | Full control. Can edit dashboard details, widgets, layout, sharing, and delete the dashboard. |
| `editor` | Can edit dashboard details, widgets, widget filters, and layout. Cannot manage sharing or delete. |
| `viewer` | Can view dashboard data and apply temporary filters. Cannot persist changes. |

Only the owner can manage share rules. Share targets are:

- `user`: grants access to one active user.
- `project_members`: grants access dynamically to all active members of a project.

Project-member shares follow current membership. Removing a user from the project
removes access to dashboards shared through that project.

## Widgets

Version 1 supports predefined widgets rather than arbitrary SQL or a fully custom
query language:

| Widget | Purpose |
| --- | --- |
| `metric_tile` | Count tasks matching widget and temporary filters. |
| `status_breakdown` | Group visible tasks by status. |
| `priority_breakdown` | Group visible tasks by priority. |
| `technician_workload` | Show task counts grouped by assignee. |
| `due_soon_table` | Show the next matching tasks ordered by due date. |
| `recent_activity` | Show recent audit activity for visible projects. |

Widget configs support these filter keys:

```text
project_ids
statuses
priorities
assignee_ids
due_window
```

`due_window` accepts `overdue`, `next_24_hours`, and `next_7_days`.

## Layout

Dashboard layout is stored per widget using a bounded 12-column grid:

```text
x
y
w
h
order
```

The API rejects widgets outside the grid and rejects overlapping widgets. The
frontend renders this as a responsive dashboard grid and allows owners/editors to
drag and resize widgets while preserving the bounded grid contract.

## Permission Filtering

Dashboard rendering always applies normal project visibility before widget
filters. A shared dashboard never leaks tasks from projects the viewer cannot see.
Temporary dashboard-level filters override widget filters for the current render
request only and are not persisted.

## API Summary

```text
GET    /api/v1/dashboards/
POST   /api/v1/dashboards/
GET    /api/v1/dashboards/{dashboard_id}/
PATCH  /api/v1/dashboards/{dashboard_id}/
DELETE /api/v1/dashboards/{dashboard_id}/
GET    /api/v1/dashboards/{dashboard_id}/widgets/
POST   /api/v1/dashboards/{dashboard_id}/widgets/
PATCH  /api/v1/dashboards/{dashboard_id}/widgets/{widget_id}/
DELETE /api/v1/dashboards/{dashboard_id}/widgets/{widget_id}/
PUT    /api/v1/dashboards/{dashboard_id}/layout/
GET    /api/v1/dashboards/{dashboard_id}/shares/
PUT    /api/v1/dashboards/{dashboard_id}/shares/
POST   /api/v1/dashboards/{dashboard_id}/render/
```

## Demo Data

`python manage.py seed_demo_data` creates three dashboards for local review:

- `Operations Dashboard`
- `Support Triage`
- `My Team`

The seeded dashboards include metric, breakdown, workload, due-date, and recent
activity widgets. Demo sharing includes one user share and one dynamic
project-member share from the start.
