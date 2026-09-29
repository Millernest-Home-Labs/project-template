---
name: create-user-tests
description: "Create user-level end-to-end tests that stay as close to the real user as possible, in Gherkin Given/When/Then scenarios that flow user -> client -> backend -> DB. Executes either browserless via jest-cucumber + @testing-library/react-native (real client tree, real backend, no Chromium) or via the Playwright test runner (@playwright/bdd or test.step) when the browser itself is the behavior (media, fullscreen, touch, a11y, layout). ONE scenario lives at exactly ONE level: user-level if a user can trigger it, API-level (sociable) only when no user path exists. USE WHEN: create user test, write e2e test, add playwright test, gherkin feature, BDD scenario, jest-cucumber, user-level test, e2e scenario, user-visible test, close to the user, feature file, playwright-bdd, browserless e2e, client-level test."
---

# Create User Tests

**Category:** Testing & Quality

## Overview

Creates **user-level end-to-end tests**: scenarios that start from a real user
action, exercise the real client and the real backend together, and assert the
user-visible outcome. Scenarios are expressed in Gherkin Given/When/Then
language and bind to ONE of two runners:

- **Browserless** (`jest-cucumber` + `@testing-library/react-native`): the
  real client component tree in jsdom against the real backend — no Chromium,
  fast, parallel, PR-time default.
- **Browser** (`@playwright/bdd` `.feature` files or `test.step`): real
  Chromium when the browser itself is the behavior under test.

---

## Philosophy

> "A feature isn't done until it gets back to the user — so start at the user."

> "If a user's actions cannot trigger that code, then it's dead code anyway.
> Why unit test it? User test it instead." — Ethan, Amminox session

> "It used to take multiple teams to deliver a feature, and we would do it in
> stages... With my opencode AI team, I have a backend agent and a frontend
> agent working at the same time to deliver the same feature. It's all done at
> the same time. Backend doesn't wait on frontend or vice versa. It ships in
> the same commit. This makes 'code with no user path today' null and void."

- **User-level first.** If a user's actions can trigger the code path, the test
  starts from that user action and asserts what the user sees. Unit tests of
  code no user can reach are testing dead code.
- **"No user path today" is null and void in this repo model.** Frontend and
  backend ship together in the same commit — there is no "we'll write that
  test later when the UI exists." The rule is: the feature ships WITH its
  user-level test, because the feature and the UI land at the same time. Do
  not defer coverage under the assumption that a path "will" exist later.
- **One scenario, exactly one level.** Never write the same scenario twice.
  If a scenario runs at the user level, it has ALREADY exercised the backend —
  the request went through the real API, the real database, and the real
  service layer. Do not re-test the same path at the API level; that is
  duplication and waste (and it burns the very AI tokens we are conserving).
- **APIs are not the starting point; the user is.** The temptation with
  fast frameworks is to "start at the API level." That is the wrong default:
  it tests a contract, not an experience, and it silently drops everything the
  client does between user input and the API call. Start at the user. Drop to
  the API level ONLY for genuinely user-invisible machinery.
- **Drop down only for user-invisible machinery.** Admin ingest pipelines, TTS
  job processors, provider crawls, and scheduled jobs serve users *indirectly*
  (the transcript you read, the sermon that appears). Those have no UI trigger
  and are the legitimate home for API-level sociable tests — but only there.
- **The engine choice is about speed and fidelity, not about Gherkin.**
  "Can the Gherkin tests run at the client level without a browser?" — YES.
  `jest-cucumber` + `@testing-library/react-native` runs the REAL client
  component tree in jsdom against the REAL backend, no Chromium required.
  The browser is reserved for behaviors that ARE the browser: media playback,
  fullscreen, touch gestures, layout geometry, a11y scans. Same feature file
  can bind its steps to the fast browserless runner (PR/daily) or the browser
  runner (gate). This is the anti-waste configuration.

---

## One Scenario, Exactly One Level — Decision Table

| Can a user trigger it? | Level | Tooling |
|---|---|---|
| Yes (visible UI interaction) | **User-level** | Playwright E2E (`@playwright/bdd` `.feature` or `test.step`) |
| Yes, but browser adds no value (pure data render/API contract) | **User-level, browserless** | `jest-cucumber` + `@testing-library/react-native` — real client tree against real backend, **no Chromium** |
| Yes, but browser IS the behavior (media, fullscreen, touch, a11y, layout) | **User-level, browser-gated** | Playwright E2E (the unavoidable Chromium cases) |
| No — background/admin/scheduled (no UI path exists) | **API-level sociable** | In-process service tests, real internals, mock only external boundaries |
| No — pure calculation/mapping, no I/O | Solitary unit | xUnit/Jest unit tests |

The browserless tier is the **default for data/flow scenarios**; the browser
tier is reserved for behaviors that ARE the browser. Both bind the same
user-level Gherkin vocabulary, so a scenario can be "run fast in PR" and
"run gated in the browser" without rewriting the feature.

---

## The Cost Ladder (when the suite gets slow)

A slow Playwright suite is usually a **runtime plumbing problem**, not proof
that Playwright is the wrong tool. Fix the plumbing first, in this order:

1. **Fail fast on systemic breakage.** If the first API call returns 500, the
   suite must abort in seconds, not grind hours proving it 3x per test.
   Real case: run 36290168453 — dead `/api/home`, 744/744 requests 500,
   139 failures all the SAME assertion, 2h12m of retry amplification at
   `workers: 1`. And it is PERSISTENT, not flaky: the next run
   (36339340157) hit the same wall and was hard-killed at 4h52m. A health
   gate turns hours into ~5 min.
2. **Parallelize.** `workers: 4` on a 2-CPU runner pod, or shard across pods
   (each shard job gets its own MySQL service container; migrations/seeding are
   idempotent on boot). Target 5–10 min wall.
3. **Cut per-user wasted time.** Env-gate the app's boot screen under test
   (e.g. `EXPO_PUBLIC_E2E_FAST_BOOT=1` -> 300ms instead of 4.45s per load),
   cache the web build / Metro cache, replace fixed sleeps with waits on
   actionable state.
4. **Only then** ask: does this *specific* scenario family still cost more
   than its user value? If yes, move it to the **browserless tier** (see
   decision table) — it stays at the user level, it just stops paying for
   Chromium. If it is genuinely user-invisible machinery with no user path,
   drop it to the API level. You are REMOVING a scenario from the browser
   suite, never duplicating one.

---

## Writing User-Level Scenarios

### Gherkin-first (`@playwright/bdd`)

```gherkin
Feature: Player resume

  Scenario: The mini-bar and the pill resume playback where the user left off
    Given the user is signed in
    And the user has played "Ye Must Be Born Again" for 30 seconds
    When they navigate away and back to Home
    Then the mini-bar shows the paused sermon
    And tapping the mini-bar resumes the player at 30 seconds
```

The `.feature` file IS the test. Step definitions are Playwright code:

```ts
import { createBdd } from 'playwright-bdd';
const { Given, When, Then } = createBdd();

Given('the user is signed in', async ({ page }) => {
  await loginViaUI(page, 'demo@unbound.test', 'Demo123!');
});

When('they navigate away and back to Home', async ({ page }) => {
  await page.getByTestId('tab-Home').click();
});

Then('the mini-bar shows the paused sermon', async ({ page }) => {
  await expect(page.getByTestId('mini-player-bar')).toBeVisible();
  await expect(page.getByTestId('mini-player-bar')).toContainText('Ye Must Be Born Again');
});
```

### Inline BDD (`test.step`) — zero extra tooling

```ts
test('resume from the mini-bar', async ({ page }) => {
  await test.step('Given the user has played the sermon', async () => {
    await bootToPlayingPlayer(page, 'Ye Must Be Born Again');
  });
  await test.step('When they minimize and return Home', async () => {
    await minimizeToMiniBar(page);
    await page.getByTestId('tab-Home').click();
  });
  await test.step('Then the mini-bar shows the paused sermon', async () => {
    await expect(page.getByTestId('mini-player-bar')).toBeVisible();
  });
});
```

### Browserless user-level (`jest-cucumber` + `@testing-library/react-native`)

The same Gherkin vocabulary, but the step definitions mount the REAL client
component tree in jsdom and hit the REAL backend through the client's own data
layer — no Chromium, ~100x lighter. Use for data/flow scenarios where the
browser itself is not the behavior under test.

```ts
import { defineFeature, loadFeature } from 'jest-cucumber';
import { render, screen, fireEvent } from '@testing-library/react-native';
import { HomeScreen } from '../src/screens/HomeScreen'; // real component

const feature = loadFeature('./features/player-resume.feature');

defineFeature(feature, (test) => {
  test('The mini-bar and the pill resume playback where the user left off', ({
    given, when, then,
  }) => {
    given('the user is signed in', async () => {
      await apiLogin('demo@unbound.test', 'Demo123!');
    });
    given('the user has played the sermon for 30 seconds', async () => {
      await seedPlayback('ye-must-be-born-again', { seconds: 30 });
    });
    when('they navigate away and back to Home', async () => {
      render(<HomeScreen />);
    });
    then('the mini-bar shows the paused sermon', async () => {
      expect(await screen.findByTestId('mini-player-bar')).toBeTruthy();
      expect(screen.getByText('Ye Must Be Born Again')).toBeTruthy();
    });
  });
});
```

The client's own data layer (the real API client bound to the real backend at
a test URL) is exercised — so the scenario still flows user -> client ->
backend -> DB, just without the 500MB Chromium overhead. When a scenario
family grows to the point that browser-only execution is too slow, THIS is the
destination: still user-level, still the real client, just lighter.

---

## Rules

- **Start from a user action.** No scenario begins at an API call unless no
  user path exists.
- **Assert user-visible outcome.** The `Then` asserts what the user sees/feels
  (visible element, playing state, elapsed time, error copy) — not internal
  state you could observe only by peeking.
- **API fixtures for setup only.** Seed/warm state via API calls in a
  `beforeEach`/`Given` when the user needs pre-existing data; assert through
  the UI.
- **Real backend, real DB.** E2E exercises the actual client + backend. Mock
  ONLY external third-party boundaries (e.g. media hosts, payment gateways) via
  Playwright route interception or fixture files.
- **Isolation.** Each test creates and cleans up its own data (unique
  timestamps, per-test accounts, `finally` cleanup). No cross-test ordering
  assumptions, no shared mutable records.
- **Parallel-safe by default.** Run with `workers >= 4`; tests must not depend
  on execution order.
- **No duplicated scenarios.** If a scenario exists at the user level, it does
  not also exist at the API level. If it is dropped to the API level, it is
  removed from the user suite.
- **Same feature, two bindings.** A `.feature` file may bind its steps to the
  browserless runner (fast, PR-time) AND the browser runner (gate-time) —
  that is not duplication, that is one scenario reused at two speeds.

---

## When to Skip the Skill

- API-only contract changes with no user-visible surface: write sociable
  API-level tests instead (see `create-sociable-tests`).
- Pure logic/calculation: solitary unit tests.
- The user asked specifically for a unit/integration test, not an e2e test.
