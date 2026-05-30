# Decision: PostgreSQL

## Decision

PostgreSQL is the only officially supported database; code is ORM-only but
MySQL/MariaDB are not guaranteed without extra CI matrix.

Primary keys use `BigAutoField`.

## Justification

PostgreSQL is the best fit for this backend because it supports strong relational
modeling, transactions, constraints, JSON fields, indexes, predictable concurrency,
and mature Django support. The domain is naturally relational: users own projects,
projects have memberships, tasks belong to projects, comments belong to tasks, and
notifications reference users and domain objects.

PostgreSQL also supports good production deployment options on VPS, Kubernetes, and
managed cloud platforms.

## Comparison

| Database | Fit | Notes |
| --- | --- | --- |
| PostgreSQL | Recommended and supported | Best fit for constraints, transactions, relational data, JSON metadata, and Django support. |
| MySQL | Possible but not guaranteed | Django supports MySQL, but behavior differs for constraints, JSON handling, locking, collations, and migrations. Needs CI matrix before support claim. |
| MariaDB | Possible but not guaranteed | Similar concerns as MySQL. Needs explicit compatibility testing before support claim. |
| MongoDB | Not supported | The domain is relational and Django does not use MongoDB as a standard relational backend. Would require different modeling or third-party integration. |
| SQLite | Not supported for production | Useful for tiny demos, but does not match concurrency and production behavior required here. |

## ORM Portability

Business logic should use Django ORM and avoid raw SQL. This keeps the code more
portable, but it does not make other databases officially supported.

Support requires:

- CI matrix for the target database.
- Migration validation.
- Query behavior validation.
- Locking behavior validation.
- JSON and constraint behavior validation.
