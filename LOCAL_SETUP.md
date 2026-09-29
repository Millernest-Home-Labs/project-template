# <Product> — Local Setup

## Prerequisites

- Node.js LTS (or the stack's runtime — see REQUIREMENTS.md)
- Docker / docker-compose for local services
- opencode.ai CLI with the providers configured in `opencode.json`

## Steps

1. Install dependencies for each component (client, server, e2e).
2. Copy any `.env.example` files to `.env` and fill in values.
3. Start local services: `docker compose up -d`.
4. Run the client and server dev servers.
5. Run E2E: `cd e2e && npx playwright test`.

## Agent workflow

- The orchestrator plans and gates phases (see AGENTS.md).
- qa runs E2E from `e2e/`, saves screenshots to `screenshots/`, and files defects in DEFECTS.md.
- The adversary runs against the running app and files findings in ADVERSARIAL_REVIEW.md.
