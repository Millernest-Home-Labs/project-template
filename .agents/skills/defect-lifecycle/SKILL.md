---
name: defect-lifecycle
description: 'Rules and exact formats for DEFECTS.md (DEF-NNN) and ADVERSARIAL_REVIEW.md (ADV-NNN): who may set which status, how to reproduce-fix-report a defect, and History entries. USE WHEN: file a defect, fix a defect, DEF-, ADV-, FIX-READY, CANNOT REPRODUCE, WORKING AS INTENDED, close defect, reopen defect, dispute, defect status, ledger.'
---

# Defect Lifecycle

Ledgers live at the repo root. A defect is never done because the implementer says so. It is done when an **independent QA pass** closes it.

## DEFECTS.md format (exact, newest first)

```
## DEF-001: Short title

- Status: OPEN
- Severity: HIGH | MEDIUM | LOW
- Found by: qa | adversary (ADV-003)
- Phase: 3

Steps to reproduce:
1. Numbered, specific, starting from app launch.

Expected: What should happen.
Actual: What happens instead.
Screenshot: screenshots/def-001.png (optional)

History:
- qa: opened
```

Severity: HIGH breaks a requirement, MEDIUM degrades one, LOW is cosmetic.

## Status machine

| Status | Meaning | Set by |
|---|---|---|
| OPEN | Filed, or reopened after a failed retest or bounced dispute | QA context |
| FIX-READY | Implementer reports a fix is in | Delivery context, relaying the implementer |
| DISPUTED | CANNOT REPRODUCE or WORKING AS INTENDED, with reason | Delivery context, reason verbatim |
| CLOSED | QA retested and confirmed, or accepted the dispute | **QA context only** |
| REJECTED | Will not fix, with written requirements-based reason | Delivery context only |

Every status change appends a History line: who, what, why.

## Fixing a defect (implementation context)

1. **Reproduce first** by following the steps exactly. Prove the problem before touching code.
2. Fix the **root cause**, re-run the same steps, and add or adjust a unit test that would have caught it.
3. Report exactly one outcome:
   - `FIX READY`: one line on what changed.
   - `CANNOT REPRODUCE`: what you tried, and what might explain the difference.
   - `WORKING AS INTENDED`: the REQUIREMENTS.md wording that supports current behavior.
4. Never set, claim or imply CLOSED.

## ADVERSARIAL_REVIEW.md format (exact)

```
## ADV-001: Short title

- Session: phase-3 gate | final
- Suggested severity: HIGH | MEDIUM | LOW

What I did: ...
Expected: ...
Actual: ...
Screenshot: screenshots/adv-001.png (optional)

Disposition: PENDING
```

The adversary creates entries and never fills Disposition. The delivery context replaces PENDING with `ACCEPTED -> DEF-NNN` (only after QA reproduces and files the DEF) or `REJECTED - reason`. No entry stays PENDING at the end of the final phase.

## Independence rule

With one super agent, independence comes from **separate contexts**, not separate personas. Filing, retesting and closing (QA) and hostile review (adversary) must run in a fresh subagent context that did not write the code under test.