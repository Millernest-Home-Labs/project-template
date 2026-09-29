---
description: "Helix regression-testing conventions for defects and behavior changes."
applyTo: "**/*Tests.cs"
---

# Regression Testing Agent Instructions

## Purpose

Ensure all production bugs are captured as automated tests before fixes are applied. This prevents regressions, documents expected behavior, and increases overall confidence in the system.

---

## Core Principles

- **Every bug must start with a failing test**
- **Tests must reproduce the bug before any fix is written**
- **All regression tests must be written as sociable tests**
- **Follow all guidance in: **`sociable-testing-strategy.instructions.md`

---

## Mandatory External Reference

All regression tests MUST comply with:

```plaintext

sociable-testing-strategy.instructions.md

```

This document defines:

- Acceptable use of mocks
- Required system boundaries
- Expectations for real component interaction

If there is any conflict, **the sociable testing strategy takes precedence**.

---

## Standard Workflow

### 1. Reproduce the Bug

- Confirm the bug exists in the current implementation
- Identify:
  - Exact inputs
  - Required state
  - Environmental conditions
- Use real or production-like data where possible

✅ Goal:

A reliably reproducible scenario outside of tests

---

### 2. Write a Failing Sociable Test (RED)

- Write a test that defines the **correct expected behavior**
- The test must:
  - Use **real collaborating components**
  - Reflect **real execution paths**
  - Avoid mocking internal system behavior

Example:

```plaintext

def test_order_total_applies_discount_correctly():

    service = OrderService(real_repository, real_pricing_engine)

    total = service.calculate_total(order_id=123)

    assert total == 90

```

✅ Requirements:

- The test must FAIL
- The failure must reflect the known bug

---

### 3. Validate the Failure

Confirm the test is failing for the **correct reason**:

- The bug is actually being triggered
- The setup matches real-world conditions
- No misconfiguration or missing setup

Validation techniques:

- Debug execution path
- Add temporary logging
- Temporarily fix code to ensure test passes

❗ Do NOT proceed until failure is trustworthy

---

### 4. Implement Minimal Fix (GREEN)

- Fix only what is necessary for the test to pass
- Do NOT:
  - Refactor unrelated code
  - Add unrelated features
  - Optimize prematurely

✅ Goal:

Make the failing test pass with minimal change

---

### 5. Refactor (REFACTOR)

- Improve code structure and clarity
- Keep all tests passing
- Ensure no behavioral changes beyond the bug fix

---

### ✅ Preserve Real Data Flow

- Use realistic data transformations and flows
- Avoid artificial or overly simplified setups

---

## Test Design Guidelines

### Accuracy

- Mirror real-world bug scenarios
- Reuse production inputs where possible

---

## Anti-Patterns (STRICTLY FORBIDDEN)

- ❌ Fixing a bug before writing a failing test
- ❌ Writing tests that do not actually reproduce the bug
- ❌ Over-mocking internal system behavior
- ❌ Writing overly broad or unfocused tests
- ❌ Ignoring flaky or nondeterministic failures

---

## Handling Legacy or Unknown Code

When system behavior is unclear:

### Step 1: Characterization

- Write sociable tests capturing current behavior
- Focus on documenting actual outputs

### Step 2: Correction

- Modify tests to reflect intended behavior
- Then implement fixes

---

## Definition of Done

A regression fix is complete only when:

- ✅ The bug is reproducible outside of tests
- ✅ A sociable test is written that fails
- ✅ The failure is validated and trustworthy
- ✅ The minimal fix makes the test pass
- ✅ All tests pass
- ✅ The code is refactored if needed
- ✅ The test clearly documents the correct behavior
- ✅ The test complies with `sociable-testing-strategy.instructions.md`

---

## Summary

All regression work must follow this strict cycle:

```plaintext

Reproduce → Write Sociable Failing Test → Validate Failure → Fix → Refactor

```

And must fully comply with:

```plaintext

sociable-testing-strategy.instructions.md

```

This ensures:

- Bugs are permanently captured
- Behavior is explicitly documented
- The system remains reliable under change
