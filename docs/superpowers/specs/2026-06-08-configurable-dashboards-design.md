# Configurable Dashboards Design

## Status

Approved for implementation planning on 2026-06-08.

## Goal

Add a top-level Dashboards workspace where users can build Jira-style operational
dashboards from predefined widgets. The first version should be configurable and
shareable, while leaving a clear path to a fuller Jira-like builder with saved
filters, richer query definitions, dashboard permissions, and layout editing.

## Product Scope

Users can create dashboards, add predefined widgets, configure widget filters,
drag and resize widgets on a bounded responsive grid, and share dashboards with
specific users or dynamic project-member groups.

Dashboards are private by default. The owner can grant view or edit access.
Sharing management is owner-only. Editors can update dashboard name, widgets,
widget filters, and layout, but cannot manage sharing, delete the dashboard, or
transfer ownership. Viewers can open shared dashboards and apply temporary
dashboard-level filters while viewing.

Temporary dashboard-level filters are not persisted. Persisted filter changes
come from editing individual widget configuration.

## Navigation And UI

Dashboards will be a top-level navigation item, separate from the existing
Dashboard page. The workspace includes:

- A list of dashboards visible to the current user.
- A dashboard canvas with widget cards.
- A widget catalog for adding supported widgets.
- An edit mode for drag-and-resize layout changes.
- Share controls available only to the dashboard owner.
- Temporary dashboard-level filters while viewing.

The layout model is a bounded responsive grid:

- Desktop uses a 12-column grid.
- Widget instances store `x`, `y`, `w`, `h`, and `order`.
- Drag and resize snap to grid cells.
- Mobile stacks widgets by `order`.
- The backend validates grid bounds and collision rules.

## V1 Widget Catalog

The first widget catalog includes:

- Metric tile.
- Status breakdown.
- Priority breakdown.
- Technician workload table.
- Due soon and overdue table.
- Recent activity feed.

Each widget type has a typed configuration schema. Configuration is stored as
JSON, but validation is owned by backend serializers or service helpers rather
than left as arbitrary client JSON.

## Drill-Down

Every widget supports drill-down:

- Metric tile opens a matching task list.
- Status or priority chart segment opens a matching task list for that segment.
- Technician workload row opens a matching task list for that assignee.
- Due soon or overdue table row opens the task detail.
- Recent activity item opens the related task or project.

Drill-down navigates to existing routed pages with filters applied. It does not
open a dashboard-side drawer in v1.

Widget render responses should include structured drill-down payloads, such as
`type` and `filters`, so the frontend does not hardcode query construction per
widget.

## Backend Architecture

Add a new `apps.dashboards` Django app. The app owns dashboard persistence,
sharing, widget config validation, widget rendering, permissions, and API
serializers.

Core models:

- `Dashboard`
  - `name`
  - `owner`
  - audit and soft-delete fields from the existing common model pattern
- `DashboardWidget`
  - `dashboard`
  - `type`
  - `title`
  - `config`
  - `x`
  - `y`
  - `w`
  - `h`
  - `order`
- `DashboardShare`
  - `dashboard`
  - `target_type`: `user` or `project_members`
  - `user`
  - `project`
  - `access`: `viewer` or `editor`

Project-member shares are dynamic. A dashboard shared with all members of a
project is visible to users who have active membership in that project at read
time. If a user is removed from the project, access ends automatically.

All widget data remains permission-aware. Dashboard access allows a user to
open the dashboard shell, but each widget still renders only data the current
viewer can access through existing project and task permissions.

All new Python methods must include simple docstrings.

## API Design

Initial endpoint shape:

- `GET /api/v1/dashboards/`
- `POST /api/v1/dashboards/`
- `GET /api/v1/dashboards/{id}/`
- `PATCH /api/v1/dashboards/{id}/`
- `DELETE /api/v1/dashboards/{id}/`
- `POST /api/v1/dashboards/{id}/widgets/`
- `PATCH /api/v1/dashboards/{id}/widgets/{widget_id}/`
- `DELETE /api/v1/dashboards/{id}/widgets/{widget_id}/`
- `PUT /api/v1/dashboards/{id}/layout/`
- `GET /api/v1/dashboards/{id}/shares/`
- `PUT /api/v1/dashboards/{id}/shares/`
- `POST /api/v1/dashboards/{id}/render/`

The render endpoint accepts temporary dashboard filters and returns widget data
plus drill-down payloads. It does not persist temporary filters.

## Frontend Architecture

Add dashboard types, API methods, routing, and a new feature module under the
frontend source tree.

The frontend should use an established grid-layout package for drag and resize
rather than hand-rolling pointer math. The implementation should keep layout
state local while editing, validate before saving, and persist through the
layout endpoint.

Demo mode must include dashboard data and dashboard API methods so reviewers
can exercise dashboards without a live backend.

## Seed Data

Update the deterministic demo seed command to create dashboards in addition to
users, projects, tasks, comments, attachments, and notifications.

Seeded dashboards must include at least:

- `Operations Dashboard`
- `Support Triage`
- `My Team`

Seed data should include multiple widget types, realistic grid layouts, one
specific-user share, and one dynamic project-member share.

The seed command should remain idempotent.

## MkDocs Documentation

Implementation must update MkDocs-facing documentation. At minimum:

- Add or update product documentation explaining configurable dashboards.
- Document the dashboard API endpoints.
- Document dashboard sharing and permission behavior.
- Document seeded demo dashboards in local development or reviewer docs.
- Update `mkdocs.yml` navigation if a new dashboards documentation page is
  added.

## Testing Requirements

Backend tests should cover:

- Dashboard CRUD permissions.
- Dynamic project-member share access.
- Owner-only sharing management.
- Editor permissions for widgets and layout.
- Viewer read-only behavior.
- Widget config validation.
- Layout bounds and collision validation.
- Permission-filtered widget rendering.
- Drill-down payload generation.
- Seed command dashboard creation and idempotency.

Frontend tests should cover:

- Dashboards top-level navigation.
- Dashboard list rendering.
- Widget catalog and add-widget flow.
- Edit mode layout save.
- Share dialog visibility and owner-only controls.
- Temporary filter behavior.
- Drill-down navigation.
- Demo mode dashboard rendering.

## Implementation Notes

The first implementation should avoid a full custom query language. Widgets use
typed structured filters now, while the data model leaves room to add saved
filters and richer query definitions later.

The implementation should preserve existing project/task permission boundaries
and reuse existing selector/service patterns where possible.

MkDocs and seed data are required parts of the final implementation, not follow
up tasks.
