# <Product> — Product Requirements

> **TEMPLATE — REPLACE THIS FILE.** Agents initializing a project from this template must
> rewrite every section below for the actual product. The example content describes a generic
> cross-platform app and exists only to show the required structure: Summary, Core Concept,
> MVP Scope (feature areas with concrete, testable bullets), Phases with success criteria,
> and Final Criteria. Delete this banner when done.

## Summary

<Product> is a cross-platform (iOS, Android, Web) application that <one-sentence purpose>.
Users <primary actions>, and the product must <the core promise>.

The product should make the path from <entry point> to <core value> quick and trustworthy.
It must be honest about data sources and capabilities: the app must never claim a feature
works when it only renders a placeholder, and it must never claim content is available when
it only links to an external source.

## Core Concept

Describe the organizing idea of the product in 2-4 paragraphs. What is the mental model users
carry? What is deliberately in scope and out of scope? What principles constrain every feature?

## MVP Scope

### <Feature Area 1>

- Concrete, testable behavior bullets. Each bullet must be verifiable by qa via E2E.
- Reference design assets where they exist (screenshots, wireframes, inspiration files).

### <Feature Area 2>

- ...

### User Account and Progress

- Register and login with email and password; JWT token management; protected endpoints.
- Save progress on pause or exit; resume surface on home.
- History, saved items, and personal library screens.

## Phases

Work is delivered in gated phases. The orchestrator gates each phase; qa and the adversary
must sign off before the next phase starts.

### Phase 1: Foundation

- Project scaffolding, CI, deployment pipeline, health endpoints.
- Success criteria: app builds, deploys to dev, `/health` returns 200, E2E harness runs.

### Phase 2: Core <Domain>

- The primary domain feature end to end.
- Success criteria: a user can complete the core loop; E2E covers it; no HIGH defects open.

### Phase 3: Engagement and Polish

- Secondary features, settings, edge cases.
- Success criteria: all MVP scope bullets implemented and E2E-verified; adversary session run.

### Phase 4: Final Gate

- Full adversarial review, defect burn-down, documentation.
- Success criteria: zero OPEN HIGH defects, all ADV entries dispositioned, final qa pass.

## Final Criteria

The project is done when:

1. Every MVP scope bullet is implemented and verified by E2E.
2. CI is green: build, lint, type-check, unit tests, E2E.
3. Zero OPEN HIGH or MEDIUM defects in DEFECTS.md.
4. No PENDING entries in ADVERSARIAL_REVIEW.md.
5. REQUIREMENTS.md, docs, and ledgers are current.
