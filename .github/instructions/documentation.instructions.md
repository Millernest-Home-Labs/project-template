# GitHub Copilot Analysis & Documentation Instructions Template

## Purpose
This template provides standardized instructions for using GitHub Copilot to analyze complex systems, generate documentation, and create comprehensive analysis reports that can be easily shared across teams.

## Project Context Template

### Basic Information
- **System/Platform**: [Insert System Name - e.g., Provenir, Helix, BWCE, etc.]
- **Analysis Type**: [Workflow Analysis | System Migration | Business Process Documentation | API Analysis | etc.]

### Project-Specific Context
```
We are working on [describe your project context]. 
We want you to look into the [directory/system] containing [type of configurations/code/data].
These files define [what they define - e.g., credit system, business logic, API contracts, etc.].
We want to [describe your goal - e.g., convert them to modern architecture, document them, and analyze dependencies, etc ].
```

#### Terminology:
- [Define project specific acronym here - e.g., Helix AgentUX]

## Analysis Instructions

### 1. Identify the Starting Point
- **Primary Entry Point**: Locate the main file/entry point (e.g., `[MainFile.extension]`, ID: `[identifier]`)
- **Context**: Identify the primary workflow/system entry point in the specified directory/codebase
- **Documentation**: Note the purpose and role of this starting file

### 2. Follow System Dependencies
- Examine the system components and their relationships (e.g., dependencies, imports, references, API calls)
- For each component that references another (by ID, name, import, or call), retrieve and analyze that component as well
- Document the flow paths, decision points, and integration patterns

### 3. Dependency Analysis
- If a referenced component itself references other components, repeat the process recursively until all dependencies are resolved
- Build a complete dependency tree/graph
- Identify circular dependencies, shared components, and critical path analysis

### 4. Business Logic Extraction
- Extract all business rules, validation logic, and decision criteria
- Identify configuration patterns, constants, and business parameters
- Document exception handling and error scenarios
- Map business terminology to technical implementation

## Documentation Requirements

After analyzing all recursive relationships and dependencies, generate a markdown file that can be easily copied and pasted into Microsoft's Azure DevOps Wiki.

### 1. Analysis Prompt Documentation
Document the specific prompt used for this analysis, including:
- **Original Prompt**: The exact prompt used to generate the documentation
- **Refinement Notes**: Any modifications or clarifications that would improve future analysis
- **Context Variables**: Key information needed to understand the analysis scope
- **Assumptions Made**: Any assumptions made during the analysis process

### 2. Gherkin Features (For BDD Projects)
Create comprehensive Gherkin features that encapsulate all business rules and serve as:
- Behavioral specifications for development teams
- Test scenarios for automated testing (Reqnroll/SpecFlow)
- Acceptance criteria for User Stories
- Business-readable documentation for Product Owners

**Requirements**:
- Use business-friendly language that Product Owners can easily understand
- Cover all identified business scenarios and edge cases
- Follow standard Gherkin syntax (Given-When-Then)
- Include data tables where appropriate

### 3. Business Rules Documentation
Document all business rules in a clear, structured format:

#### Rule Categories:
- **Validation Rules**: Data validation and constraint rules
- **Business Logic Rules**: Decision-making logic and calculations
- **Processing Rules**: Workflow and sequence rules
- **Integration Rules**: External system interaction rules
- **Exception Rules**: Error handling and fallback procedures

#### Format:
```markdown
### [Rule Category]
| Rule ID | Description | Conditions | Actions | Exceptions |
|---------|-------------|------------|---------|------------|
| BR-001 | [Business rule description] | [When this applies] | [What happens] | [Edge cases] |
```

### 4. Test Scenarios Tables (Business-Focused)
Create comprehensive test scenario tables for business validation:

**Purpose**: Ensure all business scenarios are captured for Product Owner review
**Format**:
```markdown
| Scenario ID | Business Scenario | Input Parameters | Expected Business Outcome | Notes |
|-------------|------------------|------------------|---------------------------|-------|
| TS-001 | [Business scenario description] | [Business inputs] | [Expected business result] | [Additional context] |
```

### 5. Technical Test Tables (Developer-Focused)
Create detailed technical test tables for comprehensive coverage:

**Purpose**: Ensure developers can test all technical scenarios and edge cases
**Format**:
```markdown
| Test ID | Technical Scenario | Input Data | Expected Technical Result | Assertions | Prerequisites |
|---------|-------------------|------------|---------------------------|------------|---------------|
| TT-001 | [Technical test case] | [Technical inputs] | [Expected technical output] | [What to verify] | [Setup required] |
```

### 6. C4 Model System Architecture Diagrams

Create four levels of architecture diagrams using Mermaid format:

#### Level 1: System Context Diagram
Shows the system and its users/external systems
:::mermaid
graph TB
    Users[Users] --> System[Your System]
    System --> ExternalAPI[External API]
    System --> Database[(Database)]
:::

#### Level 2: Container Diagram
Shows applications and data stores
:::mermaid
graph TB
    Users[Users] --> WebApp[Web Application]
    WebApp --> API[API Application]
    API --> Database[(Database)]
    API --> MessageQueue[Message Queue]
:::

#### Level 3: Component Diagram
Shows components within containers
:::mermaid
graph TB
    Controller[Controllers] --> Service[Business Services]
    Service --> Repository[Data Repository]
    Service --> Integration[Integration Layer]
:::

#### Level 4: Code Diagram
Shows classes/functions (if applicable)
:::mermaid
classDiagram
    class BusinessService {
        +processRequest()
        +validateData()
    }
    class DataRepository {
        +save()
        +find()
    }
    BusinessService --> DataRepository
:::

**Diagram Requirements**:
- Focus on business logic and behavior, not implementation details
- Use clear, business-friendly naming
- Include appropriate styling for different node types
- Ensure diagrams render correctly in Azure DevOps Wiki

### 7. Sequence Diagrams

Create sequence diagrams for different flow types:

#### Primary Process Flow
:::mermaid
sequenceDiagram
    participant User
    participant System
    participant ExternalAPI
    participant Database
    
    User->>System: Submit Request
    System->>ExternalAPI: Validate Data
    ExternalAPI-->>System: Validation Result
    System->>Database: Store Data
    Database-->>System: Confirmation
    System-->>User: Success Response
:::

#### Alternative Flows
- Error conditions and exception handling
- Edge cases and boundary scenarios
- Parallel processing flows
- Retry and recovery scenarios

#### Integration Points
- External system interactions
- API call sequences
- Authentication flows
- Data synchronization processes

#### Data Transformation Flows
- Input data processing
- Business rule application
- Output formatting
- Data validation steps

## Formatting Requirements

### General Markdown Rules
1. **Single Code Block**: Generate the entire document in a single Markdown code block for easy copying into Azure DevOps Wiki.

### Mermaid Diagram Requirements
- **Syntax Highlighting**: Tag all mermaid diagrams with `mermaid` for proper rendering
- **Testing**: Verify diagrams render correctly in Azure DevOps Wiki preview

### Quality Assurance
- **Completeness**: Ensure comprehensive coverage of all identified components
- **Accuracy**: Verify all business rules and technical details are correctly captured
- **Clarity**: Use clear, unambiguous language throughout
- **Consistency**: Maintain consistent formatting and terminology

## Documentation Guidelines
------------------------------------------------------------------------------------------------
### Sample Guidelines - Specify one

#### API Documentation Projects
- Focus on endpoint analysis, request/response patterns
- Include authentication and authorization flows
- Document rate limiting and error codes
- Create OpenAPI/Swagger-style documentation tables

#### Database Migration Projects
- Analyze table relationships and foreign keys
- Document data transformation rules
- Include performance considerations
- Map old schema to new schema

#### Workflow Automation Projects
- Focus on trigger conditions and actions
- Document approval processes and routing logic
- Include escalation and notification rules
- Map user roles and permissions

#### Integration Projects
- Analyze message formats and protocols
- Document retry logic and error handling
- Include monitoring and alerting requirements
- Map data mapping and transformation rules

### For Different Audiences

#### Product Owner Focus
- Emphasize business value and user stories
- Use business terminology throughout
- Include acceptance criteria in Gherkin format
- Focus on user experience and business outcomes

#### Developer Focus
- Include technical implementation details
- Provide code examples and patterns
- Document performance and scalability considerations
- Include testing strategies and approaches

#### QA/Testing Focus
- Emphasize edge cases and boundary conditions
- Include negative test scenarios
- Document test data requirements
- Provide comprehensive test coverage matrices
------------------------------------------------------------------------------------------------

## Quality Checklist

Before finalizing any analysis, ensure:

- [ ] All entry points have been identified and analyzed
- [ ] Recursive dependencies have been fully explored
- [ ] Business rules are clearly documented and categorized
- [ ] Test scenarios cover all identified use cases
- [ ] Diagrams render correctly and are business-focused
- [ ] Documentation is suitable for the intended audience
- [ ] Formatting follows Azure DevOps Wiki standards
- [ ] Technical accuracy has been verified
- [ ] Business terminology is consistent throughout
- [ ] Cross-references and links are working properly

## Notes for Continuous Improvement

- **Feedback Loop**: Regularly collect feedback from teams using these instructions
- **Template Updates**: Update the template based on lessons learned and new requirements
- **Tool Evolution**: Adapt instructions as GitHub Copilot capabilities evolve
- **Best Practices**: Document successful patterns and approaches for reuse
- **Training Materials**: Create training resources for teams adopting these practices

---

**Document Version**: 1.0  
**Last Updated**: [Current Date]  
**Owner**: [Team/Department Name]  
**Review Cycle**: Quarterly
```