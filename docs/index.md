# Project Management Backend

This documentation defines the product specification for a senior-level Django,
Django REST Framework, and Celery backend.

The application manages projects, project members, tasks, comments, attachments,
notifications, scheduled publishing, scheduled closing, and audit logs.


## Main Decisions

- Django + Django REST Framework for the API.
- PostgreSQL as the only officially supported database.
- Celery + Redis for asynchronous work.
- Docker Compose for local development.
- GHCR for public application images after implementation.
- Kubernetes manifests for deployability.
- MkDocs Material for project documentation.
- Strict separation between API schema, HTTP layer, business services, selectors,
  policies, and persistence.

## How To Read This Spec

Start with the [Product Specification](product-specification.md), then review
[Architecture](architecture.md), [API Overview](api/overview.md), and the decision
documents.
