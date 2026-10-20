# OpenClaw Cron Tool Caused Local Qwen Grammar Failures

**Date:** 2026-08-05
**Symptom:** OpenClaw scheduled-agent requests routed through LiteLLM to the local Qwen/llama.cpp server failed with `502 Bad Gateway`. The underlying llama.cpp error was a grammar initialization failure involving the generated `cron` tool schema, including `tool-cron-arg-patch-schema` in the failure path.

## Root Cause

OpenClaw's scheduler and its model-facing `cron` tool are separate features, but the `cron` tool was included in the tool schema sent to the local Qwen model. The schema was large enough, and contained enough nested/optional arguments, to trigger llama.cpp grammar-generation failures. The model did not need to manage schedules dynamically; the schedules were already registered in OpenClaw.

The important distinction is:

- `.cron.enabled` controls whether OpenClaw executes scheduled jobs.
- `.cron.triggers.enabled` controls cron-triggered execution.
- `.tools.deny` controls which tools are exposed to models.

Disabling `.cron.enabled` would have stopped the jobs and would have addressed the wrong layer of the problem.

## Solution

Back up the live configuration, add `cron` to the global model-tool deny list, and restart OpenClaw:

```sh
config=/mnt/user/appdata/openclaw/config/openclaw.json
backup="$config.bak-before-cron-tool-removal"
cp "$config" "$backup"
jq '.tools.deny = (((.tools.deny // []) + ["cron"]) | unique)' \
  "$config" > "$config.tmp"
mv "$config.tmp" "$config"
docker restart OpenClaw
```

The resulting configuration preserves scheduling while removing the model-facing tool:

```json
{
  "tools": {
    "profile": "coding",
    "deny": ["cron"]
  },
  "cron": {
    "enabled": true,
    "triggers": {
      "enabled": true
    }
  }
}
```

## Verification

Verify the policy and scheduler independently:

```sh
jq '{cronEnabled: .cron.enabled, triggerEnabled: .cron.triggers.enabled, deniedTools: .tools.deny}' \
  /mnt/user/appdata/openclaw/config/openclaw.json

docker inspect OpenClaw --format 'status={{.State.Status}} startedAt={{.State.StartedAt}}'
docker exec OpenClaw openclaw cron list --json
```

Expected results:

- `cronEnabled` is `true`.
- `triggerEnabled` is `true`.
- `deniedTools` contains `cron`.
- OpenClaw is running after the restart.
- Existing cron jobs remain registered and enabled.
- Scheduled agents no longer receive the `cron` tool schema.

The live verification showed three registered enabled jobs: `orchestrator-health-watchdog`, `gbrain-watchdog`, and `gbrain-nightly-dream`.

## Lessons

- Do not disable the scheduler to remove a tool from the model context.
- Use `.tools.deny: ["cron"]` when schedules are managed statically and agents do not need to create, edit, or delete jobs.
- Inspect the llama.cpp logs for the underlying grammar error; a LiteLLM `502` is only the proxy-level symptom.
- Keep a configuration backup before editing the live OpenClaw JSON.
- Use `jq` to preserve existing deny entries and `unique` to avoid duplicate tool names.
