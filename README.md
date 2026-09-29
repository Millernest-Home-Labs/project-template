# <Product> — Project Template

This repository is a **template** for new Millernest Labs products. It ships the fixed agent
team, the defect/adversarial ledgers, the opencode configuration, coding instructions, and the
agent skills that every project accumulates.

## Initializing a new project from this template

1. Copy this folder and rename it to the product name (lowercase, hyphenated).
2. Replace `REQUIREMENTS.md` with the real product requirements. **Agents must rewrite the
   example content** — phases, MVP scope, success criteria — for the actual product. The
   example is a placeholder, not a starting draft to keep.
3. Search-and-replace `<Product>` across `AGENTS.md`, `.github/copilot-instructions.md`, and
   the instruction files with the real product name.
4. Update `opencode.json` model/provider entries if the project needs different models.
5. Delete this README section and write the real project README.

## What lives here

| Path | Purpose |
|---|---|
| `REQUIREMENTS.md` | The contract. Phases, scope, success criteria. When in doubt, it wins. |
| `AGENTS.md` | Agent team roster, role boundaries, ledger formats, repo conventions. |
| `DEFECTS.md` | Defect ledger (DEF-XXX). qa and orchestrator only. |
| `ADVERSARIAL_REVIEW.md` | Adversary findings ledger (ADV-XXX). |
| `opencode.json` | opencode.ai config: providers, permissions, plugins. |
| `.github/copilot-instructions.md` | Rules for GitHub Copilot in this repo. |
| `.github/instructions/` | Per-technology instruction files (applyTo patterns). |
| `.agents/skills/` | Agent skills (SKILL.md files) available to all agents. |
| `e2e/` | End-to-end tests. qa-owned. |
| `screenshots/` | QA screenshots. |
| `specs/` | Gherkin features and specifications. |
| `docs/` | Documentation, backlogs, decisions. |

## The team (summary)

- **orchestrator** — plans, delegates, reviews, gates phases. Never codes.
- **frontend-dev** — frontend code + frontend unit tests.
- **backend-dev** — backend code, storage, seed data, backend unit tests.
- **qa** — E2E tests, screenshots, DEFECTS.md. Never fixes code.
- **adversary** — breaks the running app; records findings in ADVERSARIAL_REVIEW.md.

Role boundaries are absolute. See `AGENTS.md` for the full rules.
