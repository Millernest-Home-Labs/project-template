# 10: End-to-End Verification and Cleanup

Status: TODO
Owner repo: `amminox` (branch `feature/shopping-e2e`)
Depends on: 09; android-testing tasks 04 (profiles) and 05 (native E2E) for native runs
Skills: `qa-verification`, `adversarial-review`

## Goal

Prove every challenge checkbox with evidence, then remove leftovers.

## Context

The challenge checklist is `.github/challenges/carte-shopping-integration.md` (11 items, each with an MFP reference screenshot). QA and adversary roles are defined in amminox `AGENTS.md`; they run in contexts that did not write the code.

## Constraints

- Playwright tests are isolated: each creates its own user and connections via API fixtures (UUID-prefixed) and tears them down; no shared seeded records; runs in parallel in CI.
- E2E runs only against `APP_ENV=virt`. Real-vendor runs are a separate manual-dispatch workflow and never gate CI.
- Native runs use the shared emulator lease from `plans/android-testing/` (no product-owned emulator).
- QA files defects in `DEFECTS.md` and never fixes code; the adversary writes only `ADVERSARIAL_REVIEW.md`.

## Steps

1. Playwright (web, virt, isolated per test with UUID-prefixed users and teardown): connect Walmart by ZIP; connect Kroger via virt consent; Groceries Shop picker; review preselection; swap search; confirm; assert `CartResult` and the opened URL (intercept `window.open`).
2. Maestro (native, shared emulator via CI lease): same flow on Android against virt, asserting the Intent target package and screenshots of each screen. A separate manual-dispatch job runs against real vendors with `walmart-authenticated` and `kroger-authenticated` profiles and captures the retailer app cart screenshots.
3. Map each challenge checkbox to a test and a screenshot in `qa-evidence/carte-shopping/` and tick the boxes in `.github/challenges/carte-shopping-integration.md` only with that evidence.
4. Adversary pass (independent context): expired Kroger token mid-flow, revoked consent at Kroger, ZIP with no stores, 429 from each vendor, out-of-stock after preselection, app not installed, malformed vendor payloads, very long lists (Kroger cart batch limits, Walmart URL length). File ADV entries.
5. Cleanup: remove unused registry rows or keep as coming soon, delete dead env names from K8s ConfigMaps/Secrets (list names only), update `LOCAL_SETUP.md` with virt instructions and `.env.example`.

## Acceptance criteria

- All challenge boxes ticked with linked evidence.
- CI green; adversary findings triaged (DEFECTS.md entries for accepted issues).

## Evidence to report

Playwright and Maestro reports (CI artifacts), `qa-evidence/carte-shopping/` index mapping each challenge item to test + screenshot, ADV/DEF ids opened and their status.

## Do not

- Do not tick a challenge box without a linked screenshot and passing test.
- Do not run E2E against production vendors or production data.
- Do not delete K8s secrets without listing them for the user first.

## Log
