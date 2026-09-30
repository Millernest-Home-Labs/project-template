---
name: frontend-implementation
description: 'Implement Expo React Native (web/iOS/Android) UI features against a fixed API contract, with frontend unit tests and self-verification by running the app and inspecting screenshots. USE WHEN: build screen, UI feature, frontend component, client bug fix, jest tests, verify UI, look-and-feel check, loading/empty/error states.'
---

# Frontend Implementation

Build exactly what the plan asks, against the API contract, plus the frontend unit tests that prove it. Clients are Expo React Native, one mobile-first codebase for web, iOS and Android, with TypeScript `strict` and no `any`.

## Workflow

1. Read the plan/work item and the relevant REQUIREMENTS.md section, including the look-and-feel rules.
2. Work in small increments and validate each one.
3. Call the API through the typed client layer generated from or typed against the OpenAPI spec. Never write untyped ad-hoc fetch wrappers.
4. Treat accessibility, loading, empty, error and persisted states as part of the feature, not polish.
5. Add or update jest / jest-expo unit tests.

## Self-verification before reporting done

1. Run the frontend unit tests.
2. Start the app and exercise the feature.
3. Capture screenshots into `screenshots/` and **look at them**. Compare against the spec and the look-and-feel rules, and fix what you see before anyone else has to.
4. For native (Android) behavior, see `qa-verification` and the emulator learnings in `.github/learnings/`. The corporate laptop cannot reach the lab emulator directly.

Report what changed, test results, and screenshot paths.

## Rules

- Never weaken, skip or delete a test to make it pass.
- No fallback logic. Fix the root cause.
- No emojis in code, comments or logs.
- Never edit `e2e/`; end-to-end tests are owned by the QA context (`qa-verification`).