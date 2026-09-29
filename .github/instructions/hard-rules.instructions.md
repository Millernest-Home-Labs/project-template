---
description: 'Hard rules and conventions that every Millernest Labs repository must follow'
applyTo: '**'
---

# Millernest Labs — Hard Rules

These rules are **enforced**, not suggested. They are distilled from the established patterns across `reflexia`, `wish-hunter`, `unbound-preaching`, `speak-bible`, and `opencode-observability`. New repos must conform from day one; existing repos migrate toward them.

---

## 1. Organization & Ownership

- Every repo belongs to **Millernest Labs** (GitHub org: `ethanimproving`).
- Container images are published to `ghcr.io/ethanimproving/<component>` (owner lowercased). Never use a self-hosted registry — Traefik's 60s read timeout breaks large image pulls.
- All public domains are `*.millernest.com` (e.g. `reflexia.millernest.com`, `api.auctions.millernest.com`).

### DNS & Traffic Path

- **DNS:** `*.millernest.com` A records are managed in **Namecheap**, pointing at the ISP/public IP.
- **Traffic path:** Namecheap A record → ports **80/443** on the ISP edge → **NGINX Reverse Proxy** (SSL termination via **Let's Encrypt** certificates) → **Traefik ingress** on the K3s cluster → Service/Ingress for the app.
- New public hostnames require: (1) a Namecheap A record, (2) an NGINX proxy host forwarding to the K3s Traefik entrypoint, (3) a Traefik `ingress.yml` in the component's `kube-deploy/`. All three layers must exist before a domain is considered live.

## 2. Repository Layout (Monorepo)

One monorepo per product. Agents must be able to trace everything in a single clone.

```
<product>/
  <product>-client/        # Expo React Native app (web + iOS + Android, single codebase)
  <product>-server/        # Backend API (Clean Architecture — see §3)
  <product>-virtualizer/   # (optional) virt stand-ins for external paid services
  workers/                 # (optional) background/GPU workers
  e2e/                     # Playwright E2E tests (qa-owned)
  specs/                   # Specifications, Gherkin features
  docs/                    # Documentation
  screenshots/             # QA screenshots
  qa-evidence/             # QA evidence artifacts
  deploy/ or kube-deploy/  # K8s manifests per component
  docker-compose.yml       # Local dev environment
  REQUIREMENTS.md          # The contract — "when in doubt, REQUIREMENTS.md wins"
  AGENTS.md                # Agent team roster + conventions + defect ledgers
  DEFECTS.md               # DEF-XXX ledger
  ADVERSARIAL_REVIEW.md    # ADV-XXX ledger
  LOCAL_SETUP.md           # Local dev instructions
  .github/workflows/       # CI/CD
```

- **REQUIREMENTS.md is the contract.** Implementation questions resolve to it.
- **AGENTS.md** defines the fixed agent roster: `orchestrator` (plans, never codes), `frontend-dev`, `backend-dev`, `qa` (E2E, screenshots, DEFECTS.md — never fixes code), `adversary` (breaks the app, writes ADVERSARIAL_REVIEW.md). Role boundaries are absolute.
- Defect ledger format is fixed: `## DEF-001: Short title` with Status / Severity / Found by / Phase, steps, Expected/Actual, History. Status machine: OPEN → FIX-READY/DISPUTED → CLOSED (qa-only) / REJECTED.
- No emojis in code. No defensive programming / fallback logic. Prefer popular libraries over custom solutions.

## 3. Code Organization — Clean Architecture

- **.NET servers** use strict Clean Architecture with projects:
  - `<Product>.Domain` — entities, value objects, domain interfaces. Zero dependencies.
  - `<Product>.Application` — use cases, DTOs, application interfaces. Depends only on Domain.
  - `<Product>.Infrastructure` — EF Core, external services, persistence. Depends on Application.
  - `<Product>.Api` (or `.WebApi`) — controllers, DI composition root.
  - `<Product>.Contracts` — cross-boundary contracts where needed.
  - Solution naming: `Com.Millernest.<Product>.sln`; namespaces `Com.Millernest.<Product>.<Layer>`.
- **Python servers** use FastAPI with a layered structure (`app/controllers`, `app/services`, `app/models`, `app/schemas`) — dependencies still point inward; controllers never touch persistence directly.
- **Dependency rule:** source dependencies point inward only. Domain knows nothing about HTTP, databases, or vendors.
- **Clients** are Expo React Native — one codebase for web/iOS/Android, mobile-first. Each client ships its own `Dockerfile` + `nginx.conf` and `kube-deploy/` manifests.

### Type Safety & Static Analysis (correctness gates)

- **TypeScript:** `"strict": true` always. No `any` in new code (use `unknown` + narrowing). ESLint must pass with zero errors.
- **Python:** `mypy --strict` (or equivalent) and `ruff check` must pass. Type hints required on all public functions.
- **.NET:** `TreatWarningsAsErrors` enabled; `dotnet format` verified in CI. No `#pragma warning disable` without a written justification comment.
- **Zero-warning policy:** lint/type-check jobs gate CI the same as tests. Warnings are defects, not noise.

### API Contract Discipline

- Server APIs expose an OpenAPI spec (FastAPI generates it; .NET uses Swashbuckle). Client API layers are generated or typed against the spec — no hand-written untyped fetch wrappers.
- Breaking API changes require a version bump (`/api/v2/...`) or a coordinated same-PR client+server update. Never deploy a server that breaks the deployed client.

### Database Migrations

- Migrations are **forward-only** (Alembic for Python, EF migrations for .NET). Never edit an applied migration — add a new one.
- CI runs migrations against a scratch database before deploy; a failing migration fails the build.
- Destructive migrations (drop/rename) require a two-step deploy (deprecate → remove) so old and new code can coexist during rollout.

### Secrets Hygiene

- Never commit secrets, keys, or tokens. Every repo ships a `.env.example` documenting every variable (name + purpose, no values).
- CI includes a secret scanner (e.g. `gitleaks`) as a gating job.
- Runtime secrets come from K8s Secrets (see §4) or GitHub environment secrets — never baked into images or ConfigMaps.

## 4. Deployment — Self-Hosted K3s

- **Target:** self-hosted K3s at `192.168.1.206`, Traefik ingress, namespaces `dev` and `prod` (plus `ci` for the shared runner itself).
- **GitHub Actions is the primary deploy path.** Manual `kubectl apply` is permitted when needed (e.g. QA verifying a fix quickly), but product code changes must always ship through CI/CD — never as a manual-only deployment.
- **Runners:** ONE consolidated self-hosted runner stack in the `ci` namespace (StatefulSet `github-runner`), versioned in `ethanimproving/labs-infra`. Label: `[self-hosted, linux, x64]`. It serves all product repos — never create per-repo runner deployments. Scale by adding the repo to the `runner-repos` ConfigMap and bumping StatefulSet replicas (one pod per registered repo). GitHub-hosted runners are billing-blocked on this account; `ubuntu-latest` jobs will queue forever. If a hosted runner is ever required for kubectl-only access, use WireGuard with **split-tunnel** `AllowedIPs` (`192.168.1.0/24,10.253.0.0/24`) — never `0.0.0.0/0`.
- **Manifests:** per-component `kube-deploy/` folders: `deployment.yml`, `service.yml` (ClusterIP 80 → app port), `ingress.yml` (`kubernetes.io/ingress.class: traefik`), `config-map-dev.yml`, `pvc.yml` as needed. Tag substitution via `cschleiden/replace-tokens@v1.1`.
- **Health checks:** every Deployment declares `readinessProbe` and `livenessProbe` (HTTP health endpoint, e.g. `/health`). A container without probes does not deploy.
- **Resource limits:** every container declares `requests` and `limits` (CPU/memory). Prevents one product from starving the shared cluster.
- **Rollback:** if `kubectl rollout status` fails or times out, CI runs `kubectl rollout undo` automatically and fails the deploy job loudly. Never leave a broken rollout live.
- **Image tags:** `$(date +%Y%m%d%H%M).${GITHUB_RUN_NUMBER}` — identical meta step in every workflow.
- **Secrets:** created idempotently via `kubectl create secret ... --dry-run=client -o yaml | kubectl apply`. Cluster access via `KUBECONFIG_DATA` secret (k3s service-account token).
- **Deploy order:** ConfigMap → Service → Deployment → `kubectl set image` → `kubectl rollout status --timeout=600s` → Ingress.

### Mobile Testing Deployment (Expo Metro Container)

- In addition to the server and client (web) deployments, each product deploys an **Expo Metro container** to K3s for iOS/Android testing (e.g. `amminox-metro`).
- The Metro container serves the Expo dev server/bundler over the cluster, so physical devices and emulators can load the app via Expo Go / dev client pointed at the K3s-hosted Metro URL — no local `npx expo start` required.
- It gets its own component in `kube-deploy/` (deployment + service + ingress, e.g. `metro.<app>.millernest.com`) and is built/pushed by CI like any other component.
- **Environments:** GitHub `environment: dev` / `prod`. Dev deploys on push to `main`/`master` and `feature/*`. Prod only from `master`. Never commit directly to `master` — feature branches (`feature/*`) merged via squash/rebase PRs only; delete branches after merge.
- **Monitor CI after every push** (`gh run watch`); a task is not complete while CI is red.

## 5. Virtualization (`virt`) — External Services

Apply the virt environment to **any** external service where (1) we don't control the data, or (2) we must pay for interaction.

- `APP_ENV=virt` routes all external vendor calls to virtualizer services instead of live endpoints.
- Virtualizers are deterministic stand-ins (e.g. `reflexia/openrouter-virtualizer/`) with a **control API** (`/_virt/scenario`, `/_virt/reset`, `/_virt/state`) to queue failure scenarios: `timeout`, `http_402`, `http_429`, `retry_then_success`, `malformed`, etc.
- **Fail-closed guards:** the app must refuse to run prod against the virtualizer, and virt must reject real production keys (e.g. live `sk-or-v1-` keys).
- Virtualizers get their own `Dockerfile`, `kube-deploy/`, tests, and CI build job.

## 6. Testing

- **Never trigger live paywalls or paid APIs in tests.** All external vendors are virtualized with stubs/fakes in unit, integration, and E2E tests. A test that spends real money is a defect.
- **Playwright E2E is mandatory** for every new feature or behavior change — validate the user-visible outcome before marking work complete. E2E lives in `e2e/` and is qa-owned.
- **Unit + integration tests gate CI** — the build fails if any test fails.
  - .NET: `tests/UnitTests`, `tests/IntegrationTests` with a MySQL service container (`mysql:8.0`, healthcheck `mysqladmin ping`) — never the home-lab DB over VPN.
  - Python: pytest with SQLite (`aiosqlite`) in CI.
  - Clients: jest / jest-expo. Node servers: vitest.
- **Behavioral tests** are written in Gherkin using the **sociable testing pattern**, with Scenario Outlines where applicable.

### E2E Test Isolation & Parallelism

- **Playwright E2E is thread/worker-local and isolated.** Each test creates its own data via API fixtures (`test.beforeEach`) and cleans it up (`test.afterEach`). A test must **never mutate data it did not create** — no shared/seeded record mutations, no cross-test dependencies, no ordering assumptions.
- **Tests run in parallel in CI** (`workers: N` in `playwright.config`), which is only safe because of the isolation rule above. Flakiness caused by shared state is a test defect, not a retry.
- **E2E runs against the virt environment** (§5) — never against prod or live vendor endpoints.
- Prefer unique-per-test identifiers (UUID prefixes) for any created entities so parallel workers can never collide.
- **Load testing & profiling:** JMeter, pointed at the **virt environment** — never at prod or live vendor endpoints.
- QA artifacts land in `screenshots/`, `qa-evidence/`, `playwright-report/`, `test-results/` (gitignored where appropriate).

## 7. CI/CD Workflow Conventions

- Standard actions: `actions/checkout@v4`, `setup-python@v5` (3.12) / `setup-dotnet` / `setup-node@v4`, `docker/login-action@v3` + `docker/build-push-action@v6`, GHCR auth via `GITHUB_TOKEN` with `permissions: packages: write`.
- Job pipeline: **build → test → push image → deploy (kubectl)**. Deploy jobs gated on branch/environment.
- Use `concurrency` groups with `cancel-in-progress` for build jobs.
- VPN teardown steps use `if: always()` so cleanup runs on failure.

### CI Speed Rules

- **Cache dependencies:** `actions/cache` (or built-in caching in setup-* actions) for pip, npm, NuGet, and Docker layers (`docker/build-push-action` with `cache-from`/`cache-to` on GHCR). Cold builds are the exception, not the norm.
- **Path filters:** jobs skip when their component didn't change (`dorny/paths-filter` or `on.push.paths`) — a docs-only commit must not trigger a 10-minute image build.
- **Parallelize:** independent components (server, client, virtualizer, workers) build in parallel jobs, not sequentially.
- **Fail fast:** lint/type-check jobs run before (or concurrently with) long test jobs so a trivially broken PR fails in seconds, not minutes.

### Observability

- Structured JSON logging with correlation/request IDs on every server (pino for Node, structlog/logging for Python, Seq for .NET). No bare `print`/`console.log` in committed code.
- Every server exposes `/health` (liveness) and `/ready` (readiness, checks DB/dependencies) endpoints.

## 8. Pull Requests & Definition of Done

- PRs are small and reviewable — target < ~400 changed lines where practical. One concern per PR.
- Every PR: CI green (build, lint, type-check, tests), Playwright E2E updated for user-visible changes, `REQUIREMENTS.md`/docs updated if behavior changed, no new secrets.
- **A task is done when:** code merged via squash/rebase PR, CI green on master, deployed to `dev`, E2E validated, and any new defects logged in `DEFECTS.md`. "Works on my machine" is not done.

## 9. Agent Tooling

- Each repo carries `opencode.json` (opencode.ai config: permission block, providers z.ai / LiteLLM `192.168.1.194:4000` / llama.cpp `192.168.1.149:8080`).
- `.github/copilot-instructions.md`, `instructions/`, `skills/`, `agents/` where agent workflows exist.
- `.devcontainer/` for consistent dev environments.
