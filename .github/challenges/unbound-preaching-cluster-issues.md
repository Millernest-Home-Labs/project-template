# UnboundPreaching — Opus 5.5 Challenge Ledger

Opus 5.5-worthy challenges, labeled like defects (`CH-NNN`). These are hard
problems worth handing to a strong model so the solution becomes the pattern
the rest of the Millernest Labs projects copy.

---

## CH-001: Playwright-to-jest user-test migration (pattern-setting)

- Status: OPEN
- Severity: HIGH
- Found by: orchestrator
- Phase: testing-conversion

**The challenge:** Migrate UnboundPreaching's Playwright E2E suite to the
browserless user-level pattern — `jest-cucumber` + `@testing-library/react-native`
running the real client tree in jsdom against the real backend, no Chromium —
per the `create-user-tests` skill. Playwright stays ONLY for scenarios where
the browser itself is the behavior (media playback, fullscreen, touch,
a11y, layout geometry).

**Why this is the #1 Opus 5.5 handoff:**

1. **It sets the pattern for every other project.** UnboundPreaching goes first;
   reflexia, wish-hunter, speak-bible, and amminox inherit the structure. If the
   migration is done well here, the rest are mechanical. If it's done poorly,
   every project pays for it forever.
2. **The hard part is the level-split, not the port.** Each existing Playwright
   spec must be classified against the decision table: user-level browserless,
   user-level browser-gated, or API-level sociable. One scenario, exactly one
   level — no duplicated coverage. This requires judgment, not transcription.
3. **Shared Gherkin, two runners.** The target architecture is feature files
   whose steps bind to the fast browserless runner (PR-time default) and,
   only where the browser is the behavior, the Playwright runner. Designing
   that binding layer cleanly is the reusable artifact.
4. **Token economics.** Browserless tests are the anti-waste configuration —
   fast, parallel, no Chromium. The migration must land with CI wiring so the
   browserless suite gates PRs and the browser suite runs as a smaller gate.

**Acceptance shape:** every existing Playwright scenario is either (a) ported
to jest-cucumber browserless, (b) kept in Playwright with a written reason the
browser is the behavior, or (c) deleted as duplicate coverage with a note.
CI runs the browserless suite on every PR. The structure is documented well
enough that another project can copy it without asking questions.

---

## CH-002: Agent cluster-access path is unreliable (root cause of agent timeouts)

- Status: OPEN
- Severity: HIGH
- Found by: orchestrator
- Phase: deployment

**The challenge:** The OpenCode agent on the LLM box times out because it
cannot reach `kubectl` or the internal registry from the LLM box — it probes
cluster state as the first step of every deployment flow, and every probe
fails. The agent can't do anything useful until it can read the cluster.

**Candidate fixes:**
- Install `kubectl` on the LLM box with a valid kubeconfig, or
- Route cluster commands through a helper that already has access (the OpenClaw
  container on Unraid has kubectl via its mounted kubeconfig).

Until this is solid, every deployment agent run stalls at the same
"tree API probe failed" step.

---

## CH-003: Multi-layer deployment path gives no fast, meaningful failures

- Status: OPEN
- Severity: MEDIUM
- Found by: orchestrator
- Phase: deployment

**The challenge:** The traffic path is Namecheap DNS → NGINX → Traefik → K3s
ingress → service → pod. A failure at any layer is invisible to the agent until
it hits a timeout, and the agent cannot distinguish "the resource doesn't
exist yet" from "the network path is broken."

**Candidate fix:** a lightweight connectivity check (e.g., `curl` the Traefik
entrypoint before trying kubectl) so the agent fails fast with a meaningful
error instead of a generic timeout. Ideally this becomes a reusable
`deploy-path-check` skill/script all projects share.