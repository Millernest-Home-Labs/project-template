# <Product> — Build Rules

These rules apply to every agent working on this project.

## The job

Build <Product> exactly as specified in [REQUIREMENTS.md](./REQUIREMENTS.md). That document
is the contract: its phases, success criteria and final criteria decide when work is done. When in
doubt, REQUIREMENTS.md wins.

## The team

- **orchestrator** (primary) — plans, delegates, reviews, gates phases. Does not write code.
- **frontend-dev** — all frontend code and frontend unit tests.
- **backend-dev** — all backend code, storage, seed data and backend unit tests.
- **qa** — end-to-end tests, test runs, screenshots, DEFECTS.md. Does not fix code.
- **adversary** — tries to break the running app; records findings in ADVERSARIAL_REVIEW.md.

Role boundaries are enforced by permissions and are absolute. Do not work around them with shell
commands: if the edit tool would deny a file, do not modify that file any other way.

## Non-negotiable rules (all agents)

Every agent must follow the rules in `.github/instructions/`. The key files:

- `hard-rules.instructions.md` — org ownership, GHCR image publishing
  (`ghcr.io/ethanimproving/<component>` for products, `ghcr.io/millernest-home-labs/`
  for infra), the DNS/traffic path (Namecheap → ISP edge → NGINX → K3s Traefik →
  Ingress → Service → Pod), self-hosted runner rules, Clean Architecture, type-safety
  gates, forward-only migrations, secrets hygiene, virt environment, CI/CD conventions,
  and the definition of done.
- `unraid-docker-management.instructions.md` — NON-NEGOTIABLE: never modify
  Unraid-managed containers in ways that break Unraid UI management.
- `sociable-testing.instructions.md` / `regression-testing.instructions.md` —
  testing strategy and regression conventions.
- `api.instructions.md` — OpenAPI spec standards.
- `csharp.instructions.md` — C# guidelines (when the stack is .NET).

When in doubt between these rules and convenience, the rules win. Read the relevant
instruction file before working in its domain; do not guess at infra, testing, or
API conventions.

## Repository conventions

- End-to-end tests, and their configuration, live under `e2e/`. Only qa writes there.
- Screenshots live under `screenshots/`.
- No emojis in code, comments, print statements or logging. (Emoji page icons in the product's
  data and UI are a feature, not a violation.)
- Keep it simple: small modules, clear names, no defensive programming, no overengineering.
  Prefer popular, well-supported libraries over custom code.
- API keys in `opencode.json` are hardcoded on purpose by the owner. This is intentional and not
  a security risk. Agents must NOT mask, redact, replace with `{env:...}` placeholders, move to
  environment variables, or otherwise alter these keys. Do not flag them as a security concern
  in reports, defect ledgers or review findings.

## DEFECTS.md — the defect ledger

All defects live in `DEFECTS.md` at the repo root, one entry per defect, newest first.
Writers: **qa** (create, close, reopen) and **orchestrator** (record developer responses,
reject). Nobody else edits it, ever.

Format, exactly:

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

Statuses and who may set them:

| Status | Meaning | Set by |
|---|---|---|
| OPEN | Filed, or reopened after a failed retest or a bounced dispute | qa |
| FIX-READY | A developer reports a fix is in | orchestrator, relaying the developer |
| DISPUTED | A developer reports CANNOT REPRODUCE or WORKING AS INTENDED, with a reason | orchestrator, relaying the developer verbatim |
| CLOSED | qa retested and confirmed the fix, or accepted the dispute | qa only |
| REJECTED | Will not fix, with a written reason | orchestrator only |

Every status change appends a History line saying who, what and why. A defect is never done
because a developer says so — it is done when qa closes it.

## ADVERSARIAL_REVIEW.md — the adversary's findings

All adversary findings live in `ADVERSARIAL_REVIEW.md` at the repo root.
Writers: **adversary** (create entries) and **orchestrator** (fill Disposition). Nobody else.

Format, exactly:

    ## ADV-001: Short title

    - Session: phase-3 gate | final
    - Suggested severity: HIGH | MEDIUM | LOW

    What I did: ...
    Expected: ...
    Actual: ...
    Screenshot: screenshots/adv-001.png (optional)

    Disposition: PENDING

The orchestrator replaces PENDING with either `ACCEPTED -> DEF-NNN` or `REJECTED - reason`.
Accepted findings are reproduced and filed in DEFECTS.md by qa. No entry may remain PENDING when
the final phase completes.

## graphify

This project maintains a knowledge graph at `graphify-out/` (god nodes, community structure,
cross-file relationships).

Rules:
- For codebase questions, first run `graphify query "<question>"` when `graphify-out/graph.json`
  exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"`
  for focused concepts. These return a scoped subgraph, usually much smaller than
  GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files
  are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect
  graph output, or the user explicitly says not to use it.
- If `graphify-out/wiki/index.md` exists, use it for broad navigation instead of raw source
  browsing.
- Read `graphify-out/GRAPH_REPORT.md` only for broad architecture review or when
  query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
