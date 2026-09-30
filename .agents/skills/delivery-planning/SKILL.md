---
name: delivery-planning
description: 'Plan and gate a delivery phase against REQUIREMENTS.md: define the frontend/backend API contract, write task specs, sequence implementation -> QA -> adversary, and walk success criteria with evidence before declaring a phase done. USE WHEN: start a phase, plan a feature, define API contract, write task spec, phase gate, is this phase done, success criteria review, triage adversary findings, prioritize defects.'
---

# Delivery Planning and Phase Gating

REQUIREMENTS.md is the contract. A phase is done only when every applicable success criterion is demonstrated by evidence (a passing test run, observed runtime output, a screenshot, or a combination). "It should work" is not evidence.

## Per-phase workflow

1. **Read** the phase in REQUIREMENTS.md and inspect the existing implementation (prefer `graphify query` over reading whole trees).
2. **Plan** in a short note:
   - The API contract between frontend and backend: endpoints, methods, request/response shapes, status codes, error shapes.
   - Work items. Each says what to build, which unit tests prove it, and which success criteria it serves.
   - The evidence that will prove each criterion.
3. **Implement** backend and frontend against the same fixed contract (see `backend-implementation` and `frontend-implementation`). If the contract is wrong, revise the plan explicitly first. Never add compatibility shims or fallbacks.
4. **Independent QA pass**: hand off to a separate QA context (see `qa-verification`) for E2E coverage, full-suite runs and screenshots. Wait for it to finish.
5. **Adversarial pass**: hand off to a separate adversary context (see `adversarial-review`) scoped to what this phase added. Wait, then triage every finding (below).
6. **Gate**: walk each success criterion one by one and cite its evidence. Any criterion without evidence blocks the next phase.

## Triage adversary findings

For every `Disposition: PENDING` entry in ADVERSARIAL_REVIEW.md, judge it against REQUIREMENTS.md:

- **Accept**: QA must independently reproduce and file it in DEFECTS.md first. Then set `ACCEPTED -> DEF-NNN`.
- **Reject**: set `REJECTED - <requirements-based reason>`.

No entry may remain PENDING when the final phase completes.

## Defect prioritization

Work OPEN defects highest severity first (HIGH breaks a requirement, MEDIUM degrades one, LOW is cosmetic). See `defect-lifecycle` for the state machine.

## Judgment discipline

- Spend effort on judgment: read diffs, summaries, test output and screenshots, not whole source trees.
- Keep plans and specs short. Do not micro-manage a handed-off task; let it finish and report.
- Never edit REQUIREMENTS.md or AGENTS.md as part of delivery. Raise requirement gaps with the user.

## Final report

What changed, exact test and runtime evidence, infrastructure/platform actions (secrets redacted), unresolved risks, and which success criteria are proven.