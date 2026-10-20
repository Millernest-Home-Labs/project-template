# Local Inference Stack Error Remediation

## Purpose

Capture the investigation and remediation path for recurring failures between OpenClaw, LiteLLM, and the local llama.cpp server.

## Topology

| Component | Host | Role |
|---|---|---|
| OpenClaw | Unraid (`192.168.1.194`) | Agent runtime, interactive requests, and scheduled jobs |
| LiteLLM | Unraid (`192.168.1.194:4000`) | OpenAI-compatible proxy and request logging |
| llama.cpp | LLM host (`192.168.1.149:8080`) | Local Qwen inference server |
| Loki | K3s (`192.168.1.206:30953`) | Cross-container log aggregation |

## Symptoms

- GitHub Copilot/OpenClaw reported request recovery after backend failures.
- LiteLLM returned HTTP 500 responses.
- OpenClaw model calls timed out or were aborted.
- llama.cpp generated repeated KV-cache allocation errors.
- Some model responses contained malformed JSON for the `exec` tool.
- OpenClaw periodically called LiteLLM `/models` without an API key.

## Investigation method

1. Inspect the last 15 minutes of the original Docker logs for all three services.
2. Exclude the known context-compaction work from the independent error ranking.
3. Group repeated messages by failure signature, then correlate timestamps across services.
4. Inspect the actual llama.cpp launch arguments instead of assuming the configured concurrency.
5. Never print API keys, gateway tokens, or full request payloads while collecting evidence.

## Findings

### 1. KV-cache allocation pressure was the main independent offender

The llama.cpp logs contained approximately 399 messages in one 15-minute window:

```text
failed to find a memory slot for batch of size ...
failed to find free space in the KV cache, retrying with smaller batch size ...
failed to prepare attention ubatches
```

The server was launched with four slots and a 131072-token slot context:

```text
n_slots = 4, n_ctx_slot = 131072, kv_unified = true
```

The container command used `--cont-batching` but did not set an explicit parallel-slot limit. Concurrent interactive and scheduled requests therefore competed for a very large unified KV cache. Retrying smaller batches did not resolve the underlying allocation pressure.

**Root cause:** too much concurrent long-context work for the available KV-cache capacity.

**Effect:** requests slowed, queued, timed out, or eventually produced HTTP 500 responses.

### Why four slots did not fail immediately

`n_ctx_slot = 131072` describes the logical maximum context of each slot. It does not, by itself, prove that four completely populated 128K KV caches were committed to GPU memory at process startup.

The earlier server also reported `kv_unified = 'true'`. In that mode, llama.cpp manages KV capacity through a shared/unified cache rather than treating each slot as an independent guaranteed physical allocation. Depending on the llama.cpp build and allocator behavior, some memory is reserved up front while other capacity, batch workspace, and slot state are consumed as requests arrive and tokens are processed. A slot that is idle or contains only a short prompt does not consume the same KV capacity as a slot holding a 128K conversation.

Therefore, startup could succeed with the model weights loaded and the server listening even though the workload could not sustain four simultaneously growing long-context requests. The observed failure was not an immediate CUDA out-of-memory error. It appeared later as:

```text
failed to find free space in the KV cache
failed to prepare attention ubatches
```

As requests accumulated tokens, retained conversation history, and required batched decoding, the shared KV cache and temporary attention/batch allocations reached their usable limit. llama.cpp then retried smaller batches, but could not create a batch even at the reduced sizes. This distinction explains why the server initially worked and degraded only under concurrent long-context load.

The safe interpretation is: **slot context is a logical limit; usable concurrent context is bounded by physical KV-cache and workspace capacity.** Do not calculate available VRAM solely as `number of slots × slot context`; validate the actual startup allocation and sustained workload with the exact llama.cpp build and model.

### Current two-slot configuration versus the historical one-slot configuration

The original server omitted an explicit parallel-slot setting. llama.cpp selected four slots and reported four logical 131072-token contexts. The interim one-slot remediation explicitly used:

```text
-c 131072 -np 1
```

That interim configuration provided one full 128K-token context, but only permitted one request to use the inference cache at a time. Additional requests waited instead of competing for multiple growing long-context sessions.

The current deployment, applied on 2026-08-06, uses:

```text
-c 176128 -np 2
```

llama.cpp verifies this as `n_slots = 2, n_ctx_slot = 88064`. LiteLLM and OpenClaw advertise two concurrent local requests and an `88064`-token context window per OpenClaw session. The authoritative deployment workflow is [llama-cpp-config-sync](../skills/llama-cpp-config-sync/SKILL.md).

The change is specifically a concurrency change, not a model or context-window reduction. These settings remain unchanged:

- Qwen3.6-27B Q4_K_M model
- GPU offload
- Q8 KV-cache types
- Flash attention
- Batch and ubatch sizes
- Model-serving image and restart policy

The interim `-np 2` experiment must not be confused with the earlier one-slot configuration. With `-c 131072 -np 2`, llama.cpp reported two 65536-token slots, which reduced the per-request context and did not meet the 128K requirement. It was later replaced by the current `-c 176128 -np 2`, which restores an 88064-token per-slot context while retaining two cache slots.

The historical one-slot setting addressed runtime KV-cache contention and related batch-allocation failures. The current two-slot setting still requires semantic compaction: a request whose prompt plus generated output exceeds the per-slot limit requires compaction or another context-management strategy.

### Semantic compaction must follow the per-slot context

The LiteLLM callback at `/mnt/user/appdata/litellm/callbacks/context_semantic_compaction.py` runs before local requests reach llama.cpp. Its `COMPACT_CONTEXT_LIMIT` and `COMPACT_TOKEN_THRESHOLD` must be based on the **per-slot** context, not the total `-c` value. For the current deployment:

```text
COMPACT_CONTEXT_LIMIT=88064
COMPACT_TOKEN_THRESHOLD=60000
```

The previous `90000` trigger scaled proportionally from a `131072` limit to `60480`; it was rounded down to `60000`. The existing `4096` context margin and `4096` default output reserve remain in place. Leaving the callback at `131072` or `90000` would allow compaction to trigger too late for an individual 88064-token slot.

### 2. OpenClaw timeouts and aborts were downstream symptoms

The same window contained 19 timeout-related lines and 5 abort-related lines. One request received LiteLLM HTTP 500 after approximately 75 seconds. Other model calls completed successfully, but some took tens of seconds and one older call ran for several minutes before being aborted.

**Root cause:** OpenClaw requests remained active while llama.cpp was unable to obtain KV-cache memory for new batches.

### 3. LiteLLM malformed tool-call arguments were model-output failures

LiteLLM warned twice about an incomplete `exec` call:

```text
Failed to parse tool call arguments ... Unterminated string ...
Arguments: {"command":"process list
```

The surrounding request returned HTTP 200, so this was not the cause of the HTTP 500 failures. It is a model-output quality issue that should be monitored after capacity pressure is reduced.

### 4. Unauthenticated `/models` calls were low-impact configuration noise

LiteLLM recorded two HTTP 401 responses for `GET /models` with `No api key passed in`. Chat-completion requests from OpenClaw continued to authenticate and return HTTP 200 afterward.

**Root cause:** the model-discovery request path did not supply the configured provider credential.

**Effect:** noisy logs and failed model discovery; not the primary cause of completion failures.

### 5. Context overflow remains a separate workstream

The llama.cpp and LiteLLM logs also showed `Context size has been exceeded`. Automatic compaction is being handled by a separate agent. This document records the interaction with the other failures but does not replace that workstream.

### 6. The 32-tool rejection was an application guard, not a llama.cpp limit

The LiteLLM callback introduced a validation guard with this default:

```python
COMPACT_MAX_TOOL_COUNT = int(
	os.environ.get("LITELLM_COMPACT_MAX_TOOL_COUNT", "32")
)
```

The guard rejects the request before it reaches llama.cpp. The resulting error:

```text
Local request contains 91 tools; the safe limit is 32
```

is therefore generated by the custom LiteLLM callback. It is not a native llama.cpp limit and does not indicate that llama.cpp supports only 32 tools.

The exact 91-tool request was accounted for by the VS Code language-model tool registry. The following inventory measures each tool's compact JSON schema using the active llama.cpp tokenizer. `Schema characters` is the character count of the serialized individual tool definition. `Tokens` is the token count for that individual definition; the combined payload total is measured separately because JSON-array separators and shared tokenization can change the sum slightly.

| Source | Tool | Schema characters | Tokens |
| --- | --- | ---: | ---: |
| GitHub Copilot Chat | `copilot_searchCodebase` | 794 | 165 |
| GitHub Copilot Chat | `search_subagent` | 1,530 | 323 |
| GitHub Copilot Chat | `copilot_searchWorkspaceSymbols` | 616 | 127 |
| GitHub Copilot Chat | `copilot_getVSCodeAPI` | 2,160 | 413 |
| GitHub Copilot Chat | `copilot_findFiles` | 1,166 | 258 |
| GitHub Copilot Chat | `copilot_findTextInFiles` | 2,648 | 571 |
| GitHub Copilot Chat | `copilot_applyPatch` | 1,504 | 352 |
| GitHub Copilot Chat | `copilot_readFile` | 924 | 200 |
| GitHub Copilot Chat | `copilot_listDirectory` | 516 | 114 |
| GitHub Copilot Chat | `copilot_getErrors` | 878 | 191 |
| GitHub Copilot Chat | `copilot_readProjectStructure` | 177 | 36 |
| GitHub Copilot Chat | `copilot_getChangedFiles` | 925 | 206 |
| GitHub Copilot Chat | `copilot_testFailure` | 516 | 114 |
| GitHub Copilot Chat | `copilot_createNewWorkspace` | 2,151 | 431 |
| GitHub Copilot Chat | `copilot_getProjectSetupInfo` | 875 | 188 |
| GitHub Copilot Chat | `copilot_installExtension` | 761 | 157 |
| GitHub Copilot Chat | `copilot_runVscodeCommand` | 982 | 212 |
| GitHub Copilot Chat | `copilot_createNewJupyterNotebook` | 934 | 193 |
| GitHub Copilot Chat | `copilot_insertEdit` | 1,848 | 429 |
| GitHub Copilot Chat | `copilot_createFile` | 717 | 152 |
| GitHub Copilot Chat | `copilot_createDirectory` | 669 | 133 |
| GitHub Copilot Chat | `copilot_replaceString` | 2,257 | 477 |
| GitHub Copilot Chat | `copilot_multiReplaceString` | 1,781 | 352 |
| GitHub Copilot Chat | `copilot_editNotebook` | 2,141 | 494 |
| GitHub Copilot Chat | `copilot_runNotebookCell` | 1,734 | 369 |
| GitHub Copilot Chat | `copilot_getNotebookSummary` | 998 | 218 |
| GitHub Copilot Chat | `copilot_readNotebookCellOutput` | 1,029 | 231 |
| GitHub Copilot Chat | `copilot_fetchWebPage` | 848 | 188 |
| GitHub Copilot Chat | `copilot_findTestFiles` | 518 | 120 |
| GitHub Copilot Chat | `copilot_getSearchResults` | 342 | 74 |
| GitHub Copilot Chat | `copilot_githubRepo` | 912 | 195 |
| GitHub Copilot Chat | `copilot_toolReplay` | 436 | 96 |
| GitHub Copilot Chat | `copilot_switchAgent` | 1,857 | 384 |
| GitHub Copilot Chat | `copilot_memory` | 3,148 | 700 |
| GitHub Copilot Chat | `copilot_editFiles` | 242 | 54 |
| Playwright MCP Relay | `browser_close` | 393 | 95 |
| Playwright MCP Relay | `browser_resize` | 600 | 131 |
| Playwright MCP Relay | `browser_console_messages` | 542 | 114 |
| Playwright MCP Relay | `browser_handle_dialog` | 613 | 138 |
| Playwright MCP Relay | `browser_evaluate` | 880 | 182 |
| Playwright MCP Relay | `browser_file_upload` | 639 | 143 |
| Playwright MCP Relay | `browser_fill_form` | 1,115 | 249 |
| Playwright MCP Relay | `browser_install` | 696 | 149 |
| Playwright MCP Relay | `browser_press_key` | 582 | 141 |
| Playwright MCP Relay | `browser_type` | 1,048 | 219 |
| Playwright MCP Relay | `browser_navigate` | 492 | 118 |
| Playwright MCP Relay | `browser_navigate_back` | 459 | 110 |
| Playwright MCP Relay | `browser_network_requests` | 537 | 113 |
| Playwright MCP Relay | `browser_take_screenshot` | 1,717 | 355 |
| Playwright MCP Relay | `browser_snapshot` | 606 | 125 |
| Playwright MCP Relay | `browser_click` | 1,057 | 227 |
| Playwright MCP Relay | `browser_drag` | 1,028 | 206 |
| Playwright MCP Relay | `browser_hover` | 685 | 145 |
| Playwright MCP Relay | `browser_select_option` | 888 | 187 |
| Playwright MCP Relay | `browser_tabs` | 728 | 171 |
| Playwright MCP Relay | `browser_wait_for` | 761 | 174 |
| PostgreSQL extension | `pgsql_bulk_load_csv` | 3,040 | 672 |
| PostgreSQL extension | `pgsql_connect` | 1,283 | 259 |
| PostgreSQL extension | `pgsql_db_context` | 1,597 | 324 |
| PostgreSQL extension | `pgsql_describe_csv` | 701 | 154 |
| PostgreSQL extension | `pgsql_disconnect` | 574 | 111 |
| PostgreSQL extension | `pgsql_list_databases` | 844 | 169 |
| PostgreSQL extension | `pgsql_list_connection_profiles` | 509 | 98 |
| PostgreSQL extension | `pgsql_modify` | 1,975 | 389 |
| PostgreSQL extension | `pgsql_query` | 3,047 | 610 |
| PostgreSQL extension | `pgsql_get_dashboard_context` | 902 | 177 |
| PostgreSQL extension | `pgsql_get_dashboard_metric_data` | 1,068 | 214 |
| PostgreSQL extension | `pgsql_migration_oracle_app` | 1,273 | 282 |
| PostgreSQL extension | `pgsql_migration_show_report` | 550 | 119 |
| PostgreSQL extension | `pgsql_open_script` | 1,353 | 273 |
| PostgreSQL extension | `pgsql_visualize_schema` | 790 | 152 |
| PostgreSQL extension | `pgsql_query_plan` | 1,769 | 384 |
| DBCode | `dbcode-get-connections` | 490 | 106 |
| DBCode | `dbcode-workspace-connection` | 778 | 152 |
| DBCode | `dbcode-get-databases` | 674 | 147 |
| DBCode | `dbcode-get-schemas` | 784 | 174 |
| DBCode | `dbcode-get-tables` | 1,214 | 265 |
| DBCode | `dbcode-execute-query` | 1,229 | 276 |
| DBCode | `dbcode-execute-dml` | 1,275 | 288 |
| DBCode | `dbcode-execute-ddl` | 1,315 | 300 |
| DBCode | `dbcode-disconnect` | 1,042 | 219 |
| DBCode | `dbcode-set-inferred-relationships` | 1,979 | 420 |
| DBCode | `dbcode-get-inferred-relationships` | 928 | 194 |
| .NET Install Tool | `install_dotnet_sdk` | 1,253 | 304 |
| .NET Install Tool | `list_available_dotnet_versions_to_install` | 890 | 186 |
| .NET Install Tool | `recommended_dotnet_sdk_version` | 682 | 145 |
| .NET Install Tool | `find_dotnet_executable_path` | 1,039 | 235 |
| .NET Install Tool | `uninstall_system_dotnet_sdk` | 1,410 | 323 |
| .NET Install Tool | `uninstall_vscode_owned_dotnet_runtime` | 1,139 | 256 |
| .NET Install Tool | `get_settings_info_for_dotnet_installation_management` | 772 | 159 |
| .NET Install Tool | `list_installed_dotnet_versions` | 983 | 218 |
| **Total** | **91 tools** | **98,843** | **21,090** |

The combined 91-tool schema payload measured approximately **98,843 characters and 21,090 tokens** using the extension manifests and tokenizer state inspected on 2026-08-06. The sum of isolated per-tool token counts was 21,163; the combined-payload measurement is the relevant figure for request budgeting. The earlier `105,742/100,000` rejection came from a live request whose serialized schemas included additional request-time representation or metadata beyond this manifest-only inventory.

#### Character-versus-token guard failure

After both tool-specific guards were removed, a third stale preflight guard rejected this request:

```text
Rendered local prompt is too large to tokenize safely: 134546/131072 characters
```

This comparison was invalid because `131072` is the model's **token** context limit, while `134546` was a **character** count. The user's short request was not 134,546 characters; the rendered prompt also contained the system instructions, conversation history, all available tool schemas, Qwen's tool-format instructions, and the assistant generation marker. The callback was incorrectly refusing to send that rendered text to the actual tokenizer.

The stale character guard was removed on 2026-08-06. A 134,546-character synthetic input subsequently reached the active llama.cpp tokenizer and produced 16,819 tokens. The authoritative safety decision is now made from the tokenizer's result plus the requested output budget and context margin. This preserves the 131,072-token model context without treating characters as tokens.

VS Code serializes the available tool schemas into the model request even when the model does not call most of them. Additional MCP servers, including the configured GitHub MCP servers, can increase the count in other sessions. The tool count is therefore a property of the active VS Code extension and MCP configuration, not an indication that OpenClaw independently created 91 application tools.

#### Recommendation

Do not treat a fixed count of 32 as the safety boundary for this deployment. The callback already has more meaningful controls: rendered-prompt token counting against the 131072-token context, a tool-schema character budget, output-token limits, and message compaction. A hard count limit rejects valid VS Code requests before those context-aware controls can decide whether the request actually fits.

The hard count rejection was removed from the mounted callback on 2026-08-06. The callback initially retained a second fixed schema-size guard of `100000` characters, which then rejected a legitimate 91-tool request at `105742/100000` characters. That second guard was also removed. The callback now relies on rendered-token counting and the 131072-token context budget rather than either arbitrary tool count or raw schema-character thresholds. Do not silently drop arbitrary tools in LiteLLM: the model may need a tool that was removed, and the proxy cannot safely determine which tools are semantically required.

The longer-term optimization is at the source: reduce the active VS Code tool and MCP set for Qwen sessions to the tools needed for that workflow. That reduces prompt overhead without changing the model's 128K context or making the proxy guess which tools to remove. This should be measured by rendered prompt tokens and schema size, not by an arbitrary universal tool count.

This follow-up is separate from the llama.cpp `-c 131072 -np 1` capacity remediation. Increasing or removing the tool-count guard does not change KV-cache concurrency, but a larger tool schema does consume part of the same per-request context budget and must remain subject to the context-aware checks.

#### Remediation verification

- Removed `COMPACT_MAX_TOOL_COUNT` and its `32` default from the live mounted callback.
- Removed `COMPACT_MAX_TOOL_SCHEMA_CHARS` and its `100000`-character default after it rejected the observed 91-tool request at `105742` characters.
- Restarted the existing Unraid-managed `LiteLLM` container; the container remained on the same image and mount configuration.
- Compiled the callback successfully after the change.
- Ran an isolated preflight with 91 synthetic tool schemas and the pre-call hook; it returned an accepted request without either fixed-budget exception.
- The prior schema-limit log entry was confirmed to be from the request before the corrective restart; no new schema-limit entries appeared after the restart.
- The remaining safety boundary is the actual rendered prompt/token budget, including the tool schemas, requested output, and context margin.

## Remediation

### Completed in the earlier investigation

- Removed unsupported regex escapes from generated tool schemas.
- Patched llama.cpp grammar handling and deployed the patched libraries.
- Added Loki/Grafana/Promtail observability.
- Denied the model-facing `cron` tool while leaving the scheduler enabled.
- Added LiteLLM credentials to the primary OpenClaw provider path.

### Independent remediation in this workstream

1. Set an explicit lower llama.cpp parallel-slot count so interactive and scheduled requests cannot simultaneously consume four 131K slots. An interim `-np 2` setting produced two 65536-token slots, but that did not satisfy the required per-request context. The final selected setting is `-np 1` with `-c 131072`, producing one 131072-token slot.
2. Preserve the existing model, GPU offload, KV quantization, batching, and patched image; only change concurrency.
3. Inspect the OpenClaw provider model-discovery credential path without exposing or rotating credentials unnecessarily. Chat completions already had a configured provider key and succeeded; the recurring unauthenticated `/models` polling path was not changed because its configuration surface was not established safely.
4. Validate container health, successful authenticated completions, and the absence or reduction of KV-cache allocation errors after the restart.

## Verification results

After restoring the manually managed llama.cpp container with `-np 1` and `-c 131072`:

- llama.cpp reported `n_slots = 1`, `n_ctx_slot = 131072`, `status=running`, and a healthy `/health` response.
- No immediate KV-cache, context, grammar, or send-error messages were present after startup.
- The one-slot setting preserves the required full 128K context; concurrent requests queue instead of reducing each request to 64K.
- The earlier two-slot smoke test completed successfully at `44.76 tokens per second`, but that result belongs to the interim 64K-per-slot configuration.
- The unauthenticated `/models` polling remains a separate low-impact issue and was not changed here.

## Verification checklist

```bash
# llama.cpp configuration and health
docker logs llama-cpp-server 2>&1 | grep -E 'n_slots|n_ctx_slot|server listening|model loaded'

# llama.cpp pressure after a representative window
docker logs llama-cpp-server --since 10m 2>&1 | grep -Ei 'memory slot|free space in the KV cache|attention ubatches'

# LiteLLM HTTP failures
docker logs LiteLLM --since 10m 2>&1 | grep -Ei '500|502|401|No api key|APIConnectionError'

# OpenClaw provider outcomes
docker logs OpenClaw --since 10m 2>&1 | grep -Ei '\[model-fetch\] (start|response|error)'
```

## Lessons learned

- Treat LiteLLM HTTP 500 responses as proxy symptoms until the llama.cpp logs are correlated.
- Count distinct failure signatures and total volume separately; llama.cpp task IDs make raw error counts look more diverse than they are.
- Explicitly configure inference concurrency. Do not infer safe parallelism from the context-window size or assume that successful startup proves all slot capacity is physically available.
- When a full per-request context is required, set the total context and slot count deliberately; `-c 131072 -np 1` means one full 128K slot, while `-c 131072 -np 2` means two 64K slots.
- Separate scheduler configuration from model-facing tools; disabling a tool does not require disabling scheduled execution.
- Keep context compaction and backend capacity remediation as separate changes so each can be validated independently.
- Treat the active VS Code tool registry as request input. A fixed 32-tool limit rejected a legitimate 91-tool registry request; enforce rendered token and schema-size budgets instead, and reduce tools at the VS Code/MCP source when prompt overhead must be lowered.
- Do not replace an arbitrary tool-count limit with another arbitrary raw-character limit. Use the backend tokenizer and total context budget as the authoritative boundary.
- Redact secrets before collecting `docker inspect`, environment, or configuration output.