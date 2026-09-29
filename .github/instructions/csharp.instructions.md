---
description: 'Guidelines for building C# applications'
applyTo: '**/*.cs'
---

# C# Development Guidelines

## Core Principles
- **Target Framework:** Use latest LTS version (https://dotnet.microsoft.com/platform/support/policy/dotnet-core)
- **Readability:** Clear, self-explanatory code with meaningful names
- **Consistency:** Follow naming conventions and formatting throughout solution
- **Error Handling:** Structured exception handling; avoid swallowing exceptions
- **SOLID Principles:** Maintainable and extensible code design
- **Dependency Injection:** Constructor injection preferred
- **Async/Await:** Use for I/O-bound operations
- **File Organization:** One class, interface or type definition per file. Organize files into appropriate folders by feature or layer.

## Naming & Formatting
- **PascalCase:** Classes, methods, properties, public members
- **camelCase:** Private fields, local variables
- **Interfaces:** Prefix with "I" (e.g., IUserService)
- **File-scoped namespaces** and single-line using directives
- **Newline before opening braces** for code blocks
- **Pattern matching** and switch expressions where possible
- **nameof** instead of string literals for member names
- **XML doc comments** for public APIs with `<example>` tags

## Nullable Reference Types
- Declare variables non-nullable; check for null at entry points
- Use `is null` or `is not null` instead of `== null`
- Trust null annotations; avoid redundant null checks

## Architecture & Structure
- **Clean Architecture:** /src for source, /tests for tests
- **Feature folders** or domain-driven design organization
- **Separation of concerns:** Models, services, data access layers
- **Repository pattern** when beneficial for data access

## Data Access
- **Database migrations** and data seeding
- **Efficient queries** to avoid N+1 problems

## Authentication & Authorization
- **JWT Bearer tokens** for API authentication
- **Role-based and policy-based** authorization
- **Microsoft Entra ID** integration when applicable
- Secure both controller-based and Minimal APIs

## Validation & Error Handling
- **Data annotations** for model validation
- **Global exception handling** middleware
- **Problem details (RFC 7807)** for standardized error responses
- Consistent error responses across APIs

## API Design
- **Versioning strategies** for API evolution
- **Swagger/OpenAPI** documentation with proper annotations
- **Meaningful documentation** for consumers
- Version both controller-based and Minimal APIs

## Logging & Monitoring
- **Structured logging** with Serilog and unified logging framework (Gmf.Ers.UnifiedLogging nuget Package)
- **Application Insights** for telemetry collection
- **Correlation IDs** for request tracking
- Monitor performance, errors, and usage patterns

## Package Management
- Use: `https://artifactory.gmfinancial.com/artifactory/api/nuget/nuget/`
- Prefer stable releases; avoid pre-release packages unless necessary
- Regularly update dependencies to latest compatible versions

## Testing
- **Critical path coverage** for all applications
- **Integration testing** for API endpoints
- **Mock dependencies** for unit tests
- **Test authentication/authorization** logic
- Follow existing test naming and capitalization style

## Performance
- **Caching strategies:** In-memory, distributed, response caching
- **Asynchronous patterns** for better performance
- **Pagination, filtering, sorting** for large datasets
- **Compression** and other optimizations
- **Measure and benchmark** API performance

## Code Quality
- Make high-confidence suggestions only
- Include comments explaining design decisions
- Handle edge cases appropriately
- Document external dependencies and their purpose
- Avoid magic numbers; use constants or enums

