# PROJECT-004 JWT User Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add email-based custom users, JWT authentication, password reset, profile management, and active-user search.

**Architecture:** Accounts use Django's swappable custom user model before later domain migrations reference users. API views stay thin: serializers validate transport payloads, services own mutations and token side effects, selectors own user lookups, and policies expose local-password eligibility.

**Tech Stack:** Python 3.12, Django 5.2, Django REST Framework, SimpleJWT with token blacklist, drf-spectacular, pytest, pytest-django, pytest-kwparametrize, PostgreSQL.

---

## Files

- Create `apps/accounts/models.py`, `managers.py`, `admin.py`, `services.py`, `selectors.py`, `policies.py`, `tokens.py`.
- Create `apps/accounts/api/serializers.py`, `views.py`, `urls.py`, and package `__init__.py`.
- Create `apps/accounts/migrations/0001_initial.py`.
- Modify `config/settings/base.py` and `config/api_urls.py`.
- Add tests under `tests/unit/accounts/` and `tests/integration/accounts/`.
- Update `docs/api/overview.md`, `docs/api/endpoints.md`, `docs/api/errors-pagination.md`, `docs/security.md`, and `mkdocs.yml`.

## TDD Steps

- [ ] Write model tests for email login, lowercase normalization, case-insensitive duplicate rejection, no username field, profile timezone default, and external identity uniqueness.
- [ ] Write auth API tests for register-token-me, refresh, verify, logout blacklist, public auth endpoints, and protected endpoint authentication.
- [ ] Write profile/password-change API tests.
- [ ] Write password reset tests for enumeration-safe request, usable-password mail behavior, unusable-password suppression, valid confirm, invalid token, mismatch, and token reuse.
- [ ] Write active-user search tests for authentication, filtering, inactive exclusion, and minimal response fields.
- [ ] Run new tests and record red failures.
- [ ] Implement custom user model, manager, migration, admin, and settings.
- [ ] Implement account services, selectors, policies, serializers, views, and URLs.
- [ ] Update docs and schema annotations.
- [ ] Run the required verification suite and fix regressions.
- [ ] Commit once with `PROJECT-004 Add JWT user management and password reset`.

## Plan Review

- Spec coverage: all required models, settings, service functions, selectors, API endpoints, docs, schema, and test matrices are represented.
- Risk points: custom-user migration ordering, SimpleJWT blacklist tables in test databases, and schema envelope accuracy.
- Scope control: later project, task, membership, notification, and attachment domain features are excluded.
- Rating: 9/10.
