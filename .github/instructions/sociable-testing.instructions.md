---
description: "Guidance for sociable unit tests in Helix repositories: keep internal services real and mock only external boundaries."
applyTo: "**/*Tests.cs"
---

![[sociable-tests.excalidraw|800x400]]
# Sociable Testing Strategy

## Industry Foundations

This strategy is grounded in three established software engineering principles:

1. **Test Pyramid** (Mike Cohn, *Succeeding with Agile*) — The bulk of automated tests should be fast, isolated unit tests. Integration and end-to-end tests sit at the top of the pyramid and should be few in number. When scenario coverage migrates upward into slow functional tests, the pyramid inverts and feedback loops collapse.
2. **FIRST Principles** (Robert C. Martin, *Clean Code*) — Tests must be **F**ast, **I**solated, **R**epeatable, **S**elf-validating, and **T**imely. Tests that depend on live infrastructure violate Fast (network I/O), Isolated (shared mutable state), and Repeatable (external data changes between runs).
3. **Sociable Unit Tests** (Gerard Meszaros, *xUnit Test Patterns*; Martin Fowler, *UnitTest*) — A sociable test exercises a cluster of collaborating objects together, substituting only the outermost dependencies with test doubles. This validates that internal collaborations produce correct behavior without coupling tests to implementation details of each individual class.

---

## Problem Statement

Functional tests that depend on live infrastructure create three compounding problems:

1. **Test Isolation Violations** — Tests that mutate shared Cosmos DB configuration documents break neighboring tests when cleanup fails. Silent exception swallowing in AfterScenario hooks leaves the environment in unknown state.
2. **Unstable External Data** — Credit scores, pricing data, and bureau information change week to week. Tests fail not because our logic broke, but because a third-party data source returned different values. We spend developer time fixing tests instead of delivering features.
3. **Execution Time** — Network-bound tests running sequentially (20+ minutes for 57 tests) destroy feedback loops. Developers context-switch while waiting, losing flow state.

---

## Principle: Sociable Unit Tests for Scenario Coverage

**Test everything we own. Mock everything we don't.**

Sociable unit tests wire the real internal service graph and mock only true external boundaries. They validate that our business logic works correctly as an integrated unit — without live infrastructure.

---

## Testing Pyramid for Helix Repos

```plaintext
        ┌─────────────────────┐
        │  Functional Tests   │  ← Minimal: wiring, connectivity, smoke
        │     (5-10 tests)    │
        ├─────────────────────┤
        │  Sociable Unit Tests│  ← Bulk: scenario coverage, business rules
        │    (50-200 tests)   │
        ├─────────────────────┤
        │  Solitary Unit Tests│  ← Targeted: pure logic, mappers, calculations
        │    (as needed)      │
        └─────────────────────┘

```

---

## What Goes Where

### Functional Tests (keep minimal)

Use functional tests **only** for:

- Verifying DI container wires correctly (services resolve without exception)
- Confirming Event Hub messages are actually sent and received
- Validating serialization/deserialization with real payloads
- Smoke-testing the deployed function app responds to events
- Confirming Cosmos DB read/write operations work (schema, partition keys)

Do **not** use functional tests for:

- Business rule scenario coverage
- Configuration-dependent branching logic
- Testing what happens when field X has value Y
- Anything that requires mutating shared live data

### Sociable Unit Tests (primary coverage)

Use sociable tests for:

- All business logic scenarios (the "Given/When/Then" behavior)
- Configuration-driven branching (dealer mainline, loan insurance, employment verification)
- Decision status transitions
- Policy evaluation paths
- Field change routing logic
- Error handling and edge cases

### Solitary Unit Tests (targeted)

Use solitary (isolated) unit tests for:

- Pure calculation services (no dependencies)
- Mappers and transformers
- Utility/extension methods
- Validation logic

---

## Sociable Test Architecture

### Boundary Rules

<table class="markdown-table">
  <tr><th>Dependency Type</th><th>Treatment</th><th>Rationale</th></tr>
  <tr><td>Internal services (same repo)</td><td>Real instance</td><td>This is code we own and want to validate</td></tr>
  <tr><td>Pure mappers / calculators</td><td>Real instance</td><td>No external deps, fast, deterministic</td></tr>
  <tr><td>Cache contexts</td><td>Real instance</td><td>In-memory state, no I/O</td></tr>
  <tr><td>HTTP API clients</td><td>Mock</td><td>External system, network I/O</td></tr>
  <tr><td>Database repositories</td><td>Mock or Fake</td><td>External persistence, I/O</td></tr>
  <tr><td>Message senders (Event Hub)</td><td>Mock</td><td>External messaging, I/O</td></tr>
  <tr><td>Loggers</td><td>Mock.Of&lt;&gt;</td><td>Side-effect only, no behavior to test</td></tr>
</table>

### Mock Specificity Rules

**Use the actual value** for any data the test owns or generates:

```csharp
// ✅ We generate the correlation ID — use the actual value
.Setup(x => x.ApplicationsGetAsync(correlationId, applicationId, ...))

// ❌ Lazy matching hides bugs where wrong values are passed
.Setup(x => x.ApplicationsGetAsync(It.IsAny<string>(), It.IsAny<string>(), ...))

```

**Use **`It.IsAny<T>()` only for:

- Complex objects we don't constrain (e.g., `It.IsAny<DecisionHistory>()`)
- Boolean flags irrelevant to the test scenario
- Lists whose exact contents don't matter

**Use **`default` for optional `CancellationToken` parameters (never `It.IsAny<CancellationToken>()` — causes expression tree errors).

### JSON Fixture Files for API Responses

When a mock needs to return realistic response shapes, store them as JSON files:

```plaintext
tests/UnitTests/Data/
  transformed-application.json
  rules-response-approved.json
  dealer-configuration-mainline.json

```

Load with: `TestingUtils.GetTestEntity<T>("filename.json")`

This ensures mock responses match actual API contracts and are easy to update when contracts change.

---

## Test Structure

### API Level

The entry point of a sociable test is at the API level where the consumer would use our endpoint. That ensures we are testing the entire behavior of our component. If a unit of code cannot be reached from the controller, it is dead code.

### One Assert Per Test

Each test validates exactly one behavior. This makes failures immediately diagnosable:

```csharp
[Fact]
public async Task ProcessEventMessageAsync_SetsLoanInsuranceFlag_WhenAnalystTogglesInsuranceOn()
{
    // Arrange
    var application = CreateLoanInsuranceEligibleApplication();
    var eventMessage = CreateEventMessage(application, ProcessingState.AgentUxUpdate, ["PricingCriticalFields"]);
    SetupApplicationApiForLoanInsurance(application, eventMessage.CorrelationId, useLoanInsurance: true);

    // Act
    var result = await _service.ProcessEventMessageAsync(eventMessage);

    // Assert
    result.Data!.IsLoanInsuranceUsed.Should().BeTrue();
}

```

### Naming Convention

```plaintext
MethodUnderTest_ExpectedBehavior_WhenCondition

```

### No Debugging Artifacts

Tests contain only Arrange, Act, Assert. No:

- `Stopwatch` / timing code
- `Console.WriteLine` / debug logging
- `Thread.Sleep` / polling
- Comments explaining the test framework

The only exception: functional tests may log a correlation ID to trace failures in Application Insights.

---

## Migration Path

When converting a functional test to a sociable test:

1. **Identify the assertion** — What does the functional test actually verify? (e.g., "loan insurance flag is true")
2. **Identify the setup** — What configuration/data makes that scenario execute? (e.g., "IsLoanInsuranceEnabled = true, analyst toggled checkbox")
3. **Express as mock setup** — Configure the API client mocks to return the data that drives that path
4. **Assert on the output** — Check the `EventMessage` result or verify the correct API was called with correct values
5. **Remove the functional test** — Only after the sociable test covers the same business assertion

---

## When Functional Tests Are Still Required

Keep functional tests for behaviors that **cannot** be validated without live infrastructure:

- Event Hub message serialization round-trips
- Cosmos DB partition key routing
- Azure Function trigger binding
- Authentication/authorization middleware
- Network timeout/retry behavior

These are infrastructure concerns, not business logic.

---

## Anti-Patterns to Avoid

<table class="markdown-table">
  <tr><th>Anti-Pattern</th><th>Why It&#39;s Bad</th><th>Alternative</th></tr>
  <tr><td>Mutating shared Cosmos config in test setup</td><td>Breaks isolation, causes cascading failures</td><td>Mock the config response in sociable tests</td></tr>
  <tr><td>Asserting on live credit scores</td><td>Data changes weekly, tests become maintenance burden</td><td>Use JSON fixtures with known values</td></tr>
  <tr><td>20+ minute test suites</td><td>Destroys feedback loops, developers skip tests</td><td>Sociable tests run in seconds</td></tr>
  <tr><td>It.IsAny&lt;string&gt;() for correlation IDs</td><td>Hides bugs where wrong correlationId is passed</td><td>Use the actual generated value</td></tr>
  <tr><td>Multiple assertions per test</td><td>Unclear which behavior failed</td><td>One assertion per test method</td></tr>
  <tr><td>Testing framework wiring in scenario tests</td><td>Conflates infrastructure with business logic</td><td>Separate functional (wiring) from sociable (logic)</td></tr>
</table>

---

## Black Box vs White Box Testing

Testing approaches differ based on how much knowledge the test has about the system’s internals:

- **Black Box Testing** validates behavior purely from the outside. Tests provide inputs and assert outputs without any awareness of internal structure. Functional tests fall into this category—they verify that the system responds correctly, but not *how* it produces that result.
- **White Box Testing** validates behavior with full knowledge of the internal implementation. Tests are aware of classes, dependencies, and execution paths, and may verify specific interactions or branches. Solitary unit tests are typically white box, focusing on isolated logic.
- **Sociable Tests (Our Approach)** operate as a **hybrid**:
  - **Black box from a behavior perspective** — assertions focus on outcomes (business behavior), not internal method calls
  - **White box from a construction perspective** — we manually build the object graph and control dependencies

This hybrid model allows us to validate **real system behavior in a deterministic environment**, combining the realism of black box testing with the control of white box testing.

> **Summary:**  
> 
> Black box tests answer *“Does it work?”*  
> 
> White box tests answer *“How does it work?”*  
> 
> Sociable tests answer *“Does our system behave correctly under controlled conditions?”*

---

## Reference Implementations

- **Event Processor (evt):** `Underwriting/orig-undw-decisioning-evt/tests/UnitTests/Logic/ApplicationDecisioningServiceSociableTests.cs`
- **API Service:** `Customer/orig-undw-customer-bureaus-api/tests/UnitTests/Services/CreditBureausServiceSociableTests.cs`
- **Skill Documentation:** `.github/skills/create-sociable-tests/SKILL.md`
