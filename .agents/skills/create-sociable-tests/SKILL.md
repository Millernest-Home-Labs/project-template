---
name: create-sociable-tests
description: "Create sociable unit tests for Helix event processors and API services. Tests wire real internal dependency graphs and mock only external boundaries (HTTP APIs, databases, messaging). USE WHEN: create sociable test, write sociable test, sociable unit test, test internal services, mock boundaries, integration-style unit test, test service graph, wire real dependencies."
---

# Create Sociable Tests

**Category:** Testing & Quality

## Overview

Creates sociable unit tests that exercise the **real internal service graph** while mocking only true external boundaries. This approach validates that our owned code works correctly together without depending on live infrastructure (Cosmos DB, Event Hub, external APIs).

---

## Philosophy

> "Test everything we own; mock everything we don't."

- **Real:** All services, mappers, validators, and business logic classes inside the repository
- **Mocked:** Database repositories, HTTP API clients, message senders, and any client that communicates with an external system

---

## Boundary Rules

| Layer | Treatment | Examples |
|---|---|---|
| **Internal Services** | Real instances | `EmploymentEligibilityService`, `LoanProtectionService`, `DecisionHistoryMappingService` |
| **External HTTP Clients** | Mock (Moq) | `IApplicationApiClient`, `IApplicationRulesApiClient`, `ICustomerVerificationsApiClient` |
| **Database Repositories** | Mock (Moq) | Any `IRepository<T>`, Cosmos DB clients |
| **Messaging** | Mock (Moq) | `IMessageSendingService` (Event Hub) |
| **Loggers** | Mock (Mock.Of) | `ILogger<T>` |
| **Pure Mappers** | Real instances | Classes with no external dependencies |
| **Cache Contexts** | Real instances | `EmploymentReportCacheContext` |

---

## Identifying the Entry Point

| Project Type | Entry Point |
|---|---|
| **-evt** (Event Processor) | The main processing service (e.g., `ApplicationDecisioningService.ProcessEventMessageAsync`) |
| **-api** (Web API) | The controller or service method under test |
| **-lib** (Library) | The public service interface |

---

## Agent Workflow

### Step 1 — Identify Dependencies

1. Open the entry-point service constructor
2. Classify each dependency as **REAL** (internal) or **MOCK** (external boundary)
3. For each REAL dependency, recursively check its constructor — its external deps also get mocked

### Step 2 — Wire the Object Graph

```csharp
// Mocked boundaries (external)
private readonly Mock<IApplicationApiClient> _applicationApiClientMock = new();
private readonly Mock<IApplicationRulesApiClient> _applicationRulesApiClientMock = new();
private readonly Mock<IMessageSendingService> _messageSendingServiceMock = new();

// Real internal services wired with mocked external dependencies
IDecisionHistoryMappingService decisionHistoryMappingService = new DecisionHistoryMappingService();

IScoreCutPolicyManualReviewRulesService scoreCutPolicyManualReviewRulesService =
    new ScoreCutPolicyManualReviewRulesService(_applicationRulesApiClientMock.Object, _applicationApiClientMock.Object);

// Entry-point service with full graph
_service = new ApplicationDecisioningService(
    [_messageSendingServiceMock.Object],
    _applicationRulesApiClientMock.Object,
    _applicationApiClientMock.Object,
    ...real services...,
    ...mocked boundaries...);
```

### Step 3 — Create Test Data

- Use existing JSON test data files from the `tests/UnitTests/Data/` folder via `TestingUtils.GetTestEntity<T>("filename.json")`
- Override IDs with valid values (e.g., numeric strings for `ApplicationId` when `long.Parse` is involved)
- Create event messages using helper methods that accept the test entity

### Step 4 — Setup Mocks for Each Scenario

- **Full decisioning path:** Mock all API calls that the service makes (config, dealer config, rules, identity, bureau, pricing)
- **Short-circuit path:** Mock only `WriteDecisionHistory` dependencies (get application + post decision history)
- Use `It.IsAny<T>()` for parameters you don't need to constrain
- Use specific values when testing that the correct data is passed

### Step 5 — Write Tests (One Assert Per Test)

```csharp
[Fact]
public async Task ProcessEventMessageAsync_SkipsDecisioning_WhenOnlyNonCriticalFieldsChanged()
{
    // Arrange
    var application = TestingUtils.GetTestEntity<OriginationsApplication>("transformed-application.json");
    application.Id = "12345";
    var eventMessage = CreateEventMessage(application, ProcessingState.AgentUxUpdate, ["AssignedCreditAnalyst"]);
    SetupWriteDecisionHistory(application);

    // Act
    _result = await _service.ProcessEventMessageAsync(eventMessage);

    // Assert
    _result.Data!.IsApplicationDecisioningSkipped.Should().BeTrue();
}
```

---

## Test Naming Convention

```
MethodUnderTest_ExpectedBehavior_WhenCondition
```

Examples:
- `ProcessEventMessageAsync_SkipsDecisioning_WhenOnlyNonCriticalFieldsChanged`
- `ProcessEventMessageAsync_PublishesDecisionedEvent_WhenNewApplication`
- `ProcessEventMessageAsync_CallsLoanProtection_WhenInsuranceEnabled`

---

## File Location

Place sociable tests alongside existing unit tests:

```
tests/UnitTests/Logic/{ServiceName}SociableTests.cs
tests/UnitTests/Services/{ServiceName}SociableTests.cs
```

---

## Mock Setup Patterns

### External API returning JSON-shaped data

When an external API mock needs realistic response data, create a JSON file in `tests/UnitTests/Data/` that matches the actual HTTP response shape:

```csharp
var rulesResponse = TestingUtils.GetTestEntity<ApplicationRulesResponse>("rules-response.json");
_applicationRulesApiClientMock
    .Setup(x => x.ApplicationsRulesScorecutpolicymanualreviewsAsync(...))
    .ReturnsAsync(rulesResponse);
```

### Event Hub message sender

```csharp
_messageSendingServiceMock.SetupGet(m => m.Name).Returns(EventNameCode.ApplicationDecisioned.ToString());
_messageSendingServiceMock.SetupGet(m => m.SourceUri).Returns(new Uri("https://test.gmf.com/service-name"));
```

### CancellationToken parameters

Always use `It.IsAny<CancellationToken>()` — tests don't need to constrain cancellation tokens.

---

## Common Pitfalls

| Issue | Fix |
|---|---|
| `ApplicationId` must be numeric | Set `application.Id = "12345"` after loading from JSON |
| Expression tree optional args error | Use `default` for optional `CancellationToken` params, never `It.IsAny<CancellationToken>()` |
| `It.IsAny<string>()` for known values | Use the actual value (correlation ID, application ID, customer ID) — only use `It.IsAny` for data we don't control |
| Mock not matching | Ensure all optional params are covered with `default` not `It.IsAny<T>()` |
| `ApplicationNotFoundException` | Mock the `ApplicationsGetAsync` call in `WriteDecisionHistory` |
| Constructor changed | Re-check the service constructor — new deps need wiring |
| Null reference in mapper | Ensure test data JSON has the fields the mapper accesses |

---

## Mock Specificity Rules

**Use the actual value** for any data the test owns or generates:
- Correlation IDs (we generate them)
- Application IDs (we set them)
- Customer IDs (we set them)

**Use `It.IsAny<T>()`** only for:
- Data structures we don't constrain (e.g., `It.IsAny<List<string>>()` for config name lists)
- Complex objects passed through (e.g., `It.IsAny<DecisionHistory>()`, `It.IsAny<CustomerPerson>()`)
- Boolean flags that don't affect the test scenario

**Use `default`** for:
- Optional `CancellationToken` parameters (never `It.IsAny<CancellationToken>()`)

```csharp
// ✅ GOOD — specific values for known data
_applicationApiClientMock
    .Setup(x => x.ApplicationsGetAsync(correlationId, ApplicationId, ...))
    .ReturnsAsync(application);

// ❌ BAD — lazy matching for data we control
_applicationApiClientMock
    .Setup(x => x.ApplicationsGetAsync(It.IsAny<string>(), It.IsAny<string>(), ...))
    .ReturnsAsync(application);
```

---

## Reference Implementation

- **Event Processor:** `Underwriting/orig-undw-decisioning-evt/tests/UnitTests/Logic/ApplicationDecisioningServiceSociableTests.cs`
- **API Service:** `Customer/orig-undw-customer-bureaus-api/tests/UnitTests/Services/CreditBureausServiceSociableTests.cs`
- **Team Guidance:** `../../../instructions/sociable-testing.instructions.md`

---

## Quality Checklist

- [ ] All internal services are real instances (not mocked)
- [ ] Only external boundaries are mocked
- [ ] Each test has exactly one assertion
- [ ] Test names follow `Method_Behavior_Condition` pattern
- [ ] Test data uses valid IDs (numeric where required)
- [ ] Mock setups match actual method signatures (check `CancellationToken` params)
- [ ] Tests pass in isolation and in parallel
- [ ] No shared mutable state between tests (create fresh mocks per test or use constructor)
