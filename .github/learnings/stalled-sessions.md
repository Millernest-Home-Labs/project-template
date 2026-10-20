---
description: "Living catalog of every known reason an OpenCode session (Reflexia, Amminox, etc.) stalls or hangs, with 5-Whys root-cause analysis, evidence, and prevention. Append new incidents here."
---

# Stalled Sessions — Living Learnings

> **Purpose**: This is the persistent, living catalog of every distinct reason an OpenCode
> session stalls. Each incident is analyzed with the **5 Whys** method, every WHY backed by
> **proof** (log lines, process state, issue links), and assumptions **red-teamed**. As new
> stalls happen, append them here so we get robust at preventing them.

## How to use this doc

1. **New stall?** Add a new `## Incident` section below with the 5-Whys analysis.
2. **Diagnosing?** Read the "Root cause catalog" table first — your symptom likely matches a known cause.
3. **Preventing?** Apply the "Prevention playbook" for the matching cause.

---

## Root Cause Catalog (quick reference)

| # | Symptom (log signature) | Root cause | OpenCode issue | Affected versions |
|---|--------------------------|------------|----------------|-------------------|
| 1 | Subagent: last line `evaluated permission=bash ... action=allow`, then silence; abort → `error=Aborted stack=undefined` | Bash tool hangs on backgrounded/detached process holding stdout/stderr descriptor | [#47546](https://github.com/sst/opencode/issues/47546), [#48414](https://github.com/sst/opencode/issues/48414), [#22012](https://github.com/sst/opencode/issues/22012) | 1.18.x (still in 1.18.30) |
| 2 | Orchestrator/primary: `stream ... model=...` then `llm runtime selected`, then silence; process spins at ~100% CPU (Worker thread `R`) | Provider SSE stream hangs; OpenCode worker thread enters infinite loop | [#33028](https://github.com/sst/opencode/issues/33028), [#40468](https://github.com/sst/opencode/issues/40468), [#26220](https://github.com/sst/opencode/issues/26220) | 1.18.x |
| 3 | `stream error ... error.error="AI_APICallError: Usage limit reached for 5 hour"` | Provider rate limit (Z.AI 5-hour usage window) | — | any |
| 4 | `stream error ... error.error="ProviderHeaderTimeoutError: Provider response headers timed out after 120000ms"` | Provider slow to start streaming (header timeout) | fixed in v1.18.27 (5-min default) | < 1.18.27 |
| 5 | `stream error ... error.error="TimeoutError: The operation timed out."` | Provider stream timeout | fixed in v1.18.27 (5-min chunk timeout) | < 1.18.27 |
| 6 | `stream error ... error.error="AI_APICallError: This request would exceed your available credits..."` | Provider credit exhaustion / in-flight request cap | — | any |

---

## Incident Log

### 2026-09-11 — Reflexia (149) + Amminox (194) both stalled overnight

**Symptom**: Two independent sessions stalled the same night.
- **Reflexia** (149, `opencode --continue` PID 188820): stalled on **Orchestrator · GLM-5.3 Flash (Z.AI)**. No rate limit reached.
- **Amminox** (194, `opencode --continue` PID 948664): stalled on **backend-dev** using `deepseek/deepseek-v4-flash-0731` via OpenRouter.

---

#### Incident 1: Amminox — backend-dev subagent hang (Root cause #1)

**5 Whys**

1. **Why did Amminox stall?** The backend-dev subagent stopped issuing its next LLM request after a bash tool call.
   - *Proof*: `opencode.log` line 483496 `05:25:34.133Z stream ... deepseek/deepseek-v4-flash-0731 ... agent=backend-dev mode=subagent`, then line 483497 `05:25:40.752Z evaluated permission=bash pattern="setsid bash -c 'DB_NAME=amminox_test PORT=4199 node src/index.js > /tmp/opencode/live-server.log 2>&1'" action=allow`, then **silence** until `13:40:52Z cancel ... error=Aborted stack=undefined` (user abort, ~8h later).
2. **Why did the loop stop after the bash call?** The bash tool never returned its result to the loop.
   - *Proof*: No `loop step=45` line ever appears after step 44. The server process `node 947300 node src/index.js` (started 05:25) is **still alive** in the container.
3. **Why did the bash tool never return?** The command launched a **long-lived detached server** via `setsid bash -c '... node src/index.js ...'`. The server inherited the tool's stdout/stderr descriptor, so the tool's output collector waited for EOF that never comes.
   - *Proof*: `live-server.log` shows `server listening port 4199 db amminox_test` at `05:25:43.505Z` — the server started and kept running. The `2>&1` redirects the inner `node` output but the `bash -c` wrapper still holds the tool's stderr (the "bash -c redirect-scope trap" from issue #48414).
4. **Why did `setsid` make it unbounded?** `setsid` detaches the child into a new process group, so OpenCode's 2-minute timeout (which kills the process group) cannot reach it. The descriptor is never released, so the timeout cannot recover the call.
   - *Proof*: Issue #48414: *"With `setsid` the hang is unbounded. The 2-minute timeout kills the process group; a `setsid`-ed child isn't in it, so the descriptor is never released and the timeout cannot recover the call."*
5. **Why did the fallback model not trigger?** There was **no error** — the tool call simply never resolved. Fallback logic only fires on an error/exception; a hung promise that never rejects is invisible to fallback.
   - *Proof*: No `stream error` line for this session. The stall is a **hang**, not a **failure**. Fallback cannot detect a hang that never throws.

**Red-team of assumptions**
- *Assumption*: "The server process caused the hang." → **Verified**: killing the wrapper would return the call (per issue #48414 step 4). The server (947300) is confirmed alive.
- *Assumption*: "This is a rate limit." → **Rejected**: no 429/rate-limit error in the log; the user confirmed no rate limit was reached.
- *Assumption*: "Fallback should have caught it." → **Rejected**: fallback triggers on errors, not on unresolved promises. This is a hang, not a failure.

**Prevention**
- Never launch long-running servers with `setsid bash -c '... > log 2>&1'` inside the bash tool. Redirect **both** descriptors of the *wrapper* too: `setsid bash -c '...' </dev/null >/dev/null 2>&1 &` (per issue #48414, line 3 of the demo: `sleep 3 </dev/null >/dev/null 2>&1 &` returns immediately).
- Prefer a dedicated background primitive (e.g. `nohup ... & disown`, or a separate service/container) over backgrounding inside the tool.
- Add a **watchdog**: if a subagent's last event is `evaluated permission=bash` and no `loop`/`stream` follows within N minutes, treat it as a hang and abort/retry.

---

#### Incident 2: Reflexia — Orchestrator Z.AI stream hang (Root cause #2)

**5 Whys**

1. **Why did Reflexia stall?** The orchestrator (GLM-5.3 Flash via Z.AI) started a stream that never returned content.
   - *Proof*: `opencode.log` line 591462 `17:09:36.775Z stream providerID=zai modelID=glm-5.3-flash ... agent=orchestrator mode=primary`, line 591463 `17:09:36.776Z llm runtime selected`, then **silence** — no `loop step=158`, no tool call, no error.
2. **Why did the stream never return?** The Z.AI SSE stream hung — the connection produced no completion and no error.
   - *Proof*: The process (PID 188820) has **no external network connections** (only localhost listeners in `/proc/188820/net/tcp`), yet it's spinning. The stream connection was closed/never established, but the code kept waiting.
3. **Why did the process spin at 100% CPU instead of timing out?** A Worker thread (PID 188831) entered an infinite loop.
   - *Proof*: `top -H -p 188820` shows thread 188831 `Worker` at **99.9% CPU, state R (running)**, wchan `0` (no wait channel — actively executing, not waiting). This persisted across multiple checks (17:18 → 17:28).
4. **Why did the timeout not fire?** The server runs OpenCode **1.18.25**, which **predates** the v1.18.27 fix that added default streamed-chunk timeouts and fixed unhandled errors when canceling timed-out SSE reads.
   - *Proof*: `opencode --version` → `1.18.25`. v1.18.27 release notes: *"Default streamed chunk timeouts to five minutes... Avoid unhandled errors when canceling timed-out SSE reads."*
5. **Why did fallback not trigger?** Same as Incident 1 — the stream hung without raising an error, so the fallback path (which fires on exceptions) never ran. The hang is invisible to error-based fallback.

**Red-team of assumptions**
- *Assumption*: "Z.AI is down." → **Rejected**: direct `curl` to `https://api.z.ai/api/coding/paas/v4` returns in 0.64s (HTTP 400 on malformed body = reachable). The API is up.
- *Assumption*: "Rate limit." → **Rejected**: no `Usage limit` error at the stall time. (Rate limits *were* hit earlier — see Incident 3 — but not at 17:09.)
- *Assumption*: "The process is just slow." → **Rejected**: 99.9% CPU on a Worker thread for 14+ hours is an infinite loop, not slow I/O.

**Prevention**
- **Upgrade OpenCode to ≥ 1.18.27** (ideally latest) on both servers. The v1.18.27 SSE timeout fixes directly address this class of hang.
- Add a **CPU watchdog**: if an OpenCode process exceeds ~90% CPU for > 10 minutes with no log progress, it's likely a spin — restart the session.
- Consider a **stream idle timeout** at the provider layer (Z.AI) so a hung SSE connection is closed server-side.

---

#### Incident 3 (context) — Reflexia: Z.AI rate limit (Root cause #3)

**Symptom**: `stream error ... error.error="AI_APICallError: Usage limit reached for 5 hour. Your limit will reset at 2026-09-10 11:54:17"` (multiple times, 2026-09-10 01:05–01:07).

**Why fallback didn't help**: The Z.AI provider config has `timeout: 900000` and `headerTimeout: 120000`, but the **model** `z-ai/glm-5.3-flash` on OpenRouter has `allow_fallbacks: true`. However, the **direct Z.AI provider** (`zai/glm-5.3-flash`) has **no fallback configured** — it's a single-provider setup. When the orchestrator uses the direct Z.AI provider, there's no fallback model to switch to.

**Prevention**: Configure a fallback model for the direct Z.AI provider, or route through OpenRouter (which has `allow_fallbacks: true`).

---

## Prevention Playbook (consolidated)

1. **Never background long-running processes inside the bash tool** without fully detaching all descriptors: `setsid bash -c '...' </dev/null >/dev/null 2>&1 &`. (Fixes #1)
2. **Upgrade OpenCode to ≥ 1.18.27** on all servers. (Fixes #2, #4, #5)
3. **Add a hang watchdog**: monitor for "last event = `evaluated permission=bash`" or "stream started but no loop within N min" → abort/retry. (Fixes #1, #2)
4. **Add a CPU watchdog**: >90% CPU for >10 min with no log progress → restart session. (Fixes #2)
5. **Configure fallback models for direct providers** (Z.AI), not just OpenRouter. (Fixes #3, #6)
6. **Monitor provider credits** (Z.AI 5-hour usage window, OpenRouter in-flight cap) proactively. (Fixes #3, #6)

---

## Implementation Status (2026-09-11)

| # | Prevention | Status | Details |
|---|------------|--------|---------|
| 2 | Upgrade OpenCode to ≥ 1.18.27 | ✅ **DONE** | Both servers upgraded to **1.18.30**. Reflexia (149): `opencode.bak-1.18.25` backup. Amminox (194): `opencode.bak-1.18.21` backup. |
| 3+4 | Hang + CPU watchdog | ✅ **DONE** | `opencode-watchdog.sh` deployed to both servers, runs every 5 min via cron. **v3 (signature-based)**: only kills on proven stall signatures (bash-tool descriptor hang, Worker-thread spin), never on generic log-idle. Kills the stuck process, then **auto-resumes** by sending `opencode --continue` to the tmux pane. |
| 1 | Never background servers in bash tool | ⚠️ **Behavioral** | Requires agent-prompt discipline; document the correct `setsid ... </dev/null >/dev/null 2>&1 &` pattern. |
| 5 | Fallback models for direct providers | ⏳ **Pending** | Z.AI direct provider has no fallback; route through OpenRouter or add a fallback model. |
| 6 | Monitor provider credits | ⏳ **Pending** | No automated credit monitoring yet. |

### Watchdog deployment reference

- **Script**: `W:\.github\learnings\opencode-watchdog.sh` (source of truth)
- **Reflexia (149)**: `/home/ethan/scripts/opencode-watchdog.sh`, cron `*/5 * * * *`, tmux target `Reflexia:0.0`
- **Amminox (194)**: `/mnt/user/appdata/opencode/scripts/opencode-watchdog.sh`, cron `*/5 * * * *`, tmux target `Amminox:0.0`, persisted via `/boot/config/go`
- **Log**: `/tmp/opencode-watchdog/watchdog.log` on each host
- **Test**: `DRY_RUN=1 bash <script> --log <path> --tmux <session:pane>` (dry-run reports without killing)
- **Auto-resume**: after killing a stuck process, the watchdog waits for the shell prompt to return in the tmux pane, then sends `opencode --continue` so the session resumes work automatically.

### Watchdog detection logic (v3 — signature-based, conservative)

**IMPORTANT LESSON**: The original watchdog used "log idle" as a hang signal and **killed healthy sessions**. A session can be legitimately idle (waiting for a model response, between turns) or busy (running tests at high CPU) while the log is quiet. Killing on log-idle alone caused repeated false-positive kills (the "Too execution aborted" errors).

The watchdog now only kills on **proven stall signatures**:
- **SIG-1 (bash-tool descriptor hang)**: last log line is `evaluated permission=bash` for a command that backgrounds/detaches a process (`setsid`, `nohup`, `disown`, ` &`), AND process is idle (low CPU), AND log idle ≥ 10 min. This is the proven Amminox signature.
- **SIG-2 (Worker-thread spin)**: main process idle (low CPU) but a worker thread at ≥ 90% CPU, AND log idle ≥ 10 min. This is the proven Reflexia signature.

Anything else (busy session, idle-but-healthy session) is **NOT killed**. This eliminates false positives while still catching the two proven stall types.

### Watchdog validation (2026-09-11)

The watchdog **caught and killed stalled sessions in production** the same day it was deployed:
- **Reflexia (149)**: `19:05:11Z` HANG → killed PID 197289; `19:05:16Z` HANG → killed PID 249504. New sessions resumed healthy.
- **Amminox (194)**: `18:55:02Z` HANG → killed PID 948664 (the previously-stalled session). New session resumed healthy.

**CAUTION**: These kills were from the **v1 (kill-only)** and **v2 (log-idle)** watchdog versions, which were **too aggressive** and also killed healthy busy sessions (causing "Too execution aborted"). The **v3 (signature-based)** version is now deployed and only kills on proven stall signatures.

---

## Diagnostic cheat sheet

| Question | Command |
|----------|---------|
| What was the last thing the session did? | `grep -n '<session_id>' opencode.log \| tail` |
| Is the process spinning? | `docker exec OpenCode top -b -n 1 -H -p <pid>` (look for `R` state, ~100% CPU) |
| Is a detached process holding a descriptor? | `ls -l /proc/<pid>/fd/2` (shows `socket:[N]` held by opencode) |
| Did the provider error? | `grep -iE 'stream error\|429\|rate\|timeout\|limit' opencode.log \| tail` |
| Is the provider reachable? | `curl -s -o /dev/null -w '%{http_code} %{time_total}s' <provider-url>` |
| What OpenCode version? | `docker exec OpenCode opencode --version` |
