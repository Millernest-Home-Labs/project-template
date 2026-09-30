---
name: adversarial-review
description: 'Hostile, unscripted exploratory testing of the running app to break it, recording every anomaly in ADVERSARIAL_REVIEW.md (ADV-NNN). Must run in an independent context; never fixes or triages. USE WHEN: adversarial review, break the app, exploratory testing, chaos testing, hostile user, edge cases, phase-gate adversary pass, final adversary pass.'
---

# Adversarial Review

Break the running product. Use it like a hostile, careless, curious user, not like a test script. Run in a **separate subagent context** that did not build the feature, and never fix or triage what you find.

## Sessions

- **Phase-gate pass**: short, focused on features the phase just added.
- **Final pass**: long, over the whole product, in both themes, covering everything in REQUIREMENTS.md.

## How to drive

Work from the browser's text snapshot (accessibility tree) where possible, and judge behavior and structure: wrong or missing content, broken state, dead controls, errors, state that no longer adds up after an action. Capture a screenshot for anything possibly visual.

## Attack catalog (invent more)

- **Extremes**: 500-char titles, empty states, zero rows, 50+ items, a wall of pasted text.
- **Odd sequences**: delete while viewing, refresh mid-drag or mid-submit, rename to blank, toggle theme on every screen, back/forward during async work, double-submit.
- **Input abuse**: quotes, unicode, emoji, HTML/script-like strings, junk in numeric/URL/zip fields, filters that match nothing.
- **Interaction abuse**: keyboard-only runs, rapid repeated taps, menus opened and abandoned mid-input, rotating or resizing mid-flow.
- **Integration edges** (for retailer/shopping flows): disconnected retailer, expired session, zero search results, out-of-stock swaps, invalid zip, retailer app not installed.

## Recording

Record every anomaly in ADVERSARIAL_REVIEW.md using the exact ADV format in `defect-lifecycle`: what you did, expected, actual, screenshot if visual, suggested severity, `Disposition: PENDING`, numbered ADV-NNN in sequence. Judge against REQUIREMENTS.md, but record anything surprising and say why. Over-reporting is fine; missing a real problem is the only failure.

## Rules

- Edit only ADVERSARIAL_REVIEW.md and `screenshots/`. Never product code, tests or other ledgers, whether by edit tool or shell.
- Never fill in Disposition.
- Report observations, not blame: steps, expected, actual.
- Never target live paid vendors or prod; use `virt`.