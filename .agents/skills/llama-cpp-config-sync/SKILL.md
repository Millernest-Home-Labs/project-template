---
name: llama-cpp-config-sync
description: 'Synchronize llama.cpp Docker launch arguments with LiteLLM and OpenClaw context settings. Use when changing llama.cpp context size, parallel slots, KV-cache configuration, model-serving arguments, or fixing long-context 502/timeouts in the OpenClaw → LiteLLM → llama.cpp pipeline.'
argument-hint: '[total-context] [parallel-slots]'
---

# llama.cpp Configuration Synchronization

Update a remote llama.cpp Docker deployment and reflect its effective capacity in LiteLLM and OpenClaw without losing unrelated serving settings.

## Scope and topology

This workflow is for the repository's local inference path:

| Component | Host | Configuration |
|---|---|---|
| llama.cpp | `ethan@192.168.1.149` | `/home/ethan/llamacpp-portainer-compose.yml`, container `llama-cpp-server` |
| LiteLLM | Unraid `root@192.168.1.194` | `/mnt/user/appdata/litellm/config.yaml`, container `LiteLLM` |
| OpenClaw | Unraid `root@192.168.1.194` | `/mnt/user/appdata/openclaw/config/openclaw.json`, container `OpenClaw` |

Load [Ubuntu LLM access](../ubuntu-llm-server/SKILL.md) for SSH details and [Unraid SSH access](../unraid-ssh-connection/SKILL.md) for connection troubleshooting. Respect [Unraid Docker management](../../instructions/unraid-docker-management.instructions.md) before operating on containers hosted by Unraid.

## Required inputs

- Desired **total context** in tokens, such as `176128`.
- Desired **parallel slots**, such as `2`.
- The target model ID, normally `Qwen3.6-27B`.
- The llama.cpp host, model path, image, and management method if they differ from the defaults above.

Calculate the advertised OpenClaw context as:

$$
\text{per-slot context} = \frac{\text{total context}}{\text{parallel slots}}
$$

The total context must divide evenly by the slot count. Do not advertise the total context as a per-session context when parallel slots are enabled.

## Safety rules

- Inspect before changing anything. Never guess the existing image, mount, model path, network mode, restart policy, or arguments.
- Preserve all arguments unrelated to the requested change, including model alias, GPU layers, batch sizes, threads, KV-cache types, Flash Attention, Jinja, grammar patches, and restart policy.
- Back up every bind-mounted configuration file before editing it. Use a UTC timestamp in the backup name.
- Never print API keys, gateway tokens, passwords, private keys, or complete request payloads.
- Do not change LiteLLM concurrency for every model. Change only the matching local model entry.
- OpenClaw's `contextWindow` must be the per-slot context for the target model. Update both `models.providers.litellm` and `models.providers.llamacpp-local` when both contain the target model.
- Update LiteLLM semantic compaction for the new per-slot context. `COMPACT_CONTEXT_LIMIT` must equal the per-slot context, and `COMPACT_TOKEN_THRESHOLD` must be recalculated; leaving either at the old total or old single-slot value makes compaction trigger too late or not at all.
- Do not use `docker compose` unless the host supports it and the container is explicitly compose-managed. If Compose is unavailable or broken, use the documented manual launch method after recording the existing configuration.
- Do not manually recreate an Unraid-template-managed container. For an Unraid-managed container, edit its persistent configuration through the approved management interface and use Docker only for inspection, `exec`, logs, and restart operations.
- A running container is not sufficient proof. Verify effective arguments, health, slot count, per-slot context, and recent errors.

## Procedure

### 1. Inspect the deployment

Read the current llama.cpp container before modifying it:

```powershell
ssh -i "$env:USERPROFILE\.ssh\id_ed25519_ubuntu" ethan@192.168.1.149 "docker inspect llama-cpp-server --format '{{json .Config.Cmd}}'; docker inspect llama-cpp-server --format 'image={{.Config.Image}} restart={{.HostConfig.RestartPolicy.Name}} mounts={{json .Mounts}} networks={{json .NetworkSettings.Networks}}'"
```

Read the persisted launch definition and identify the management method:

```powershell
ssh -i "$env:USERPROFILE\.ssh\id_ed25519_ubuntu" ethan@192.168.1.149 "sed -n '1,240p' /home/ethan/llamacpp-portainer-compose.yml"
```

Inspect the downstream model entries without exposing credentials. Confirm the target model, API base, current LiteLLM request limit, and OpenClaw context windows.

### 2. Validate the requested values

- Require positive integer values for total context and slots.
- Require `total_context % slots == 0`.
- Compute `per_slot_context` before editing anything.
- Confirm the resulting per-slot value leaves room for the model's output budget and any configured safety margin.
- Do not infer capacity from VRAM estimates alone. The startup logs and `/props` endpoint are authoritative for slot allocation.

For example, `176128 / 2 = 88064`; therefore OpenClaw receives `contextWindow: 88064`, not `176128`.

Semantic compaction uses the same per-slot limit. Preserve the existing margin and output reserve unless the capacity decision explicitly changes them, then recalculate the trigger threshold. A safe proportional migration is:

$$
	ext{new threshold} = \left\lfloor
	ext{old threshold} \times \frac{\text{new per-slot context}}{\text{old context limit}}
\right\rfloor
$$

Round the result down to an operational boundary and verify that:

$$
	ext{threshold} + \text{output reserve} + \text{context margin}
< \text{per-slot context}
$$

For the current migration, the previous `90000 / 131072` trigger scales to `60480`; use `60000` as the rounded trigger, with `COMPACT_CONTEXT_LIMIT=88064`. The live callback currently keeps a `4096` margin and `4096` default output reserve, so the trigger leaves substantial room for the request to be compacted before llama.cpp rejects it.

### 3. Back up and update the llama.cpp launch definition

Back up the persistent launch file before changing defaults. Update only the parallel-slot and total-context values. In this deployment these are represented by:

- `-np ${N_PARALLEL:-...}`
- `-c ${CTX_SIZE:-...}`

Preserve the model path and all other command arguments. If the container was created manually, stop and remove it only after capturing its full inspect output, then recreate it with the same image, mounts, ports, environment, GPU access, restart policy, and preserved arguments. Prefer the existing documented launch mechanism.

After launch, verify logs contain the expected shape:

```text
n_slots = 2, n_ctx_slot = 88064
```

### 4. Update LiteLLM

Back up `/mnt/user/appdata/litellm/config.yaml`. Change only the target local model's `max_parallel_requests` to the configured slot count. Keep the target's `chat_template_kwargs.enable_thinking: false`, API base, guided-decoding setting, and all other model entries unchanged.

LiteLLM's request limit controls upstream concurrency; it does not allocate llama.cpp KV-cache slots. Keep the values aligned unless there is a documented reason to intentionally serialize requests.

### 5. Update OpenClaw

Back up `/mnt/user/appdata/openclaw/config/openclaw.json`. For the target model ID, update `contextWindow` to `per_slot_context` in each relevant local provider:

- `models.providers.litellm.models[]`
- `models.providers.llamacpp-local.models[]`

Do not modify unrelated providers, aliases, costs, credentials, or output limits. Preserve valid JSON formatting and use the OpenClaw container's available Node runtime for parsing and validation when the host has no Python runtime.

### 6. Update semantic compaction

The callback is bind-mounted on Unraid at `/mnt/user/appdata/litellm/callbacks/context_semantic_compaction.py`. Back it up before changing the defaults. Update only the context-dependent values:

```python
COMPACT_CONTEXT_LIMIT = 88064
COMPACT_TOKEN_THRESHOLD = 60000
```

Do not confuse these values:

- `COMPACT_CONTEXT_LIMIT`: hard per-slot prompt/output budget.
- `COMPACT_TOKEN_THRESHOLD`: early semantic-compaction trigger.
- `COMPACT_CONTEXT_MARGIN`: safety margin retained from the existing deployment.
- `COMPACT_DEFAULT_OUTPUT_RESERVE`: fallback output budget retained from the existing deployment.

After editing, inspect the callback source or its environment overrides inside the LiteLLM container. An environment override takes precedence over the Python default and must be updated instead if present.

### 7. Reload services safely

- Restart `llama-cpp-server` only after its effective launch arguments have been updated.
- Restart LiteLLM after its model or semantic-compaction changes.
- Restart OpenClaw after its model config changes.
- Never restart an unrelated service just to validate configuration.

### 8. Verify end to end

Run all of these checks:

```powershell
# llama.cpp health and effective capacity
Invoke-RestMethod http://192.168.1.149:8080/health
Invoke-RestMethod http://192.168.1.149:8080/props

# downstream container states
ssh root@192.168.1.194 "docker inspect LiteLLM OpenClaw --format '{{.Name}} | {{.State.Status}} | {{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}'"
```

Confirm:

- `health.status` is `ok`.
- `total_slots` equals the requested slot count.
- llama.cpp logs report the requested `n_ctx_slot`.
- LiteLLM's target model has the requested `max_parallel_requests`.
- LiteLLM semantic compaction reports the per-slot `COMPACT_CONTEXT_LIMIT` and a recalculated `COMPACT_TOKEN_THRESHOLD`.
- OpenClaw's matching provider entries have the computed per-slot `contextWindow`.
- No new `send_error`, KV-cache allocation, context overflow, or startup failure appears after reload.
- An authenticated, minimal OpenAI-compatible request returns HTTP 200. Do not treat an empty `content` field as a server failure when Qwen reasoning is enabled; verify the LiteLLM thinking override separately.

## Failure handling

- If the container does not start, restore the last backup or original command exactly; do not invent fallback flags.
- If `n_slots` or `n_ctx_slot` differs from the requested values, stop and inspect the actual llama.cpp version's flags before making another change.
- If GPU allocation fails, do not silently reduce context or slots. Report the exact CUDA/KV-cache error and require a deliberate capacity decision.
- If OpenClaw remains unhealthy, inspect its startup log and validate JSON before changing unrelated settings.
- If LiteLLM returns `401`, distinguish reachability from authentication failure; do not disable authentication.

## Bundled validation helper

Use [validate_sync.ps1](./scripts/validate_sync.ps1) for a read-only post-change check. It verifies the remote llama.cpp health, slot count, LiteLLM model concurrency, and OpenClaw context windows without printing secrets.
