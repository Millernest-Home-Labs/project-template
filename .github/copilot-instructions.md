# GitHub Copilot Instructions

## Rules

- **Never commit directly to `master`.** All changes must be made on a `feature/*` branch and merged via a Pull Request.
- Only use Squash or Rebase when merging Pull Requests to ensure git history remains meaningful. (No "Merge commit" messages.)
- Delete feature branches after merging.
- Feature branches are always prefixed with `feature/`.
- Avoid fallback logic. Fallback logic is bad practice because it creates a repository of patches rather than fixing problems with the original path through the application. Focus on making the expected path work rather than making the app resilient.
- **Monitor CI after every push.** After each `git push`, run `gh run watch` (or `gh run list` + `gh run view --log-failed`) to confirm the build passes. If it fails, diagnose the root cause immediately, fix it, push the fix, and continue monitoring until the workflow shows a green pass. Never consider a task complete while the CI build is red.
- **Prove every new feature with Playwright.** For every new feature or behavior change, add or update Playwright E2E tests that validate the user-visible outcome, run them as part of implementation, and do not mark the work complete until Playwright validation is green (local/virt and dev workflow validation).

```powershell
# After every push — watch CI and fail-fast on red
gh run watch ; gh run list --limit 1 --json conclusion --jq '.[0].conclusion'
```

## Project Overview

<Product> is built by the Millernest Labs agent team defined in [AGENTS.md](../../AGENTS.md).
REQUIREMENTS.md is the contract: its phases, success criteria and final criteria decide when
work is done. When in doubt, REQUIREMENTS.md wins.

## Content Creation Standards

### Writing Style & Tone

- **Declarative, not interrogative** — State actions, don't ask permissions
- **Specific over generic** — Reference exact patterns from this codebase
- **Execution-focused** — Provide actionable guidance, not theoretical advice
- Use **bold** for key concepts and `code` for technical terms

### Documentation Structure

1. **Purpose statement** — Clear, single-sentence objective
2. **Core principles** — 3-7 foundational rules with bold headers
3. **Implementation patterns** — Specific examples with code snippets
4. **Quality standards** — Measurable success criteria

## AI Agent Behavioral Patterns

### Execution Philosophy

- **Zero-confirmation policy** — Execute planned actions immediately
- **Autonomous decision-making** — Resolve ambiguities independently
- **Continuous workflow** — Complete all phases without interruption
- **Documentation-driven** — Record every step and decision

### Quality Gates

- Validate against existing patterns before creating new ones
- Prioritize code reuse over duplication
- Ensure consistency with established architectural boundaries
- Test implementation against acceptance criteria

## Development Workflows

### TDD Methodology

- **Red phase** — Write failing tests from requirements
- **Green phase** — Minimal implementation to pass tests
- **Refactor phase** — Improve design while maintaining functionality

## Code Standards

Follow the `.editorconfig` settings:

- UTF-8 encoding, CRLF line endings
- 2-space indentation (4 spaces for C# and VB)
- Trim trailing whitespace, insert final newline
- Language-specific formatting (see `.github/instructions/*.instructions.md`)

## File Creation Guidelines

When creating new AI guidance files:

1. **Scan existing files first** — Reuse patterns and avoid duplication
2. **Follow the established taxonomy** — Instructions vs. Prompts vs. Chat modes
3. **Include complete frontmatter** — All relevant metadata fields
4. **Provide specific examples** — Reference actual code patterns when possible
5. **Test applicability** — Ensure guidance works across the intended scope

## Critical Constraints

- **Never ask for confirmation** — Execute based on established patterns
- **Maintain architectural consistency** — Follow existing directory structure
- **Preserve existing quality standards** — Don't lower established bars
- **Document all changes** — Update related files when making modifications

## graphify

For any question about this repo's architecture, structure, components, or how to add/modify/find
code, your first action should be `graphify query "<question>"` when `graphify-out/graph.json`
exists. Use `graphify path "<A>" "<B>"` for relationship questions and `graphify explain "<concept>"`
for focused-concept questions. These return a scoped subgraph, usually much smaller than the full
report or raw grep output.

Triggers: "how do I…", "where is…", "what does … do", "add/modify a <component>",
"explain the architecture", or anything that depends on how files or classes relate.

If `graphify-out/wiki/index.md` exists, use it for broad navigation. Read `graphify-out/GRAPH_REPORT.md`
only for broad architecture review or when query/path/explain do not surface enough context. Only read
source files when (a) modifying/debugging specific code, (b) the graph lacks the needed detail, or
(c) the graph is missing or stale.

Type `/graphify` in Copilot Chat to build or update the graph.
