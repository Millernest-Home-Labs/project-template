---
name: backend-implementation
description: 'Implement server-side features to a fixed API contract: storage (MySQL/EF/Alembic migrations), endpoints, seed data, and backend unit tests, then prove the API with real requests and persistence checks. USE WHEN: implement endpoint, add API, backend feature, database migration, seed data, server bug fix, backend unit tests, verify API behavior.'
---

# Backend Implementation

Build exactly what the plan asks, to the API contract it defines, plus the unit tests that prove it. Follow the repository hard rules (Clean Architecture, forward-only migrations, structured logging, `/health` and `/ready`).

## Workflow

1. Read the plan/work item and the relevant REQUIREMENTS.md section before coding.
2. Work in small increments and validate each one before moving on.
3. Treat the API contract as fixed. If it is wrong or incomplete, stop and revise the plan explicitly. Frontend work is built against the same contract, so never change it silently.
4. Migrations are forward-only and **idempotent** at runtime: guard `ADD COLUMN` / `CREATE INDEX` against existing objects. A non-idempotent migration crash-looped `amminox-server` on `Duplicate column name 'dislikes'`.
5. Add or update backend unit tests for every new service method, domain rule and endpoint.

## Definition of done (backend)

- The backend unit suite passes. Never weaken, skip or delete a test to make it pass; if a test looks wrong, say so.
- Every changed endpoint has been exercised with **real requests**. Record actual status codes and response bodies.
- Persistence is verified across a server restart where relevant.
- Report what changed, the test results, and any contract notes.

## Rules

- No fallback or defensive logic. Repair the expected path and the root cause.
- External paid or uncontrolled vendors go through the `virt` virtualizer in tests. Never call live paywalls.
- No emojis in code, comments or logs. No bare `print`/`console.log`; use structured logging.
- Never edit `e2e/`, DEFECTS.md closure fields, or ADVERSARIAL_REVIEW.md dispositions from an implementation context. See `defect-lifecycle`.