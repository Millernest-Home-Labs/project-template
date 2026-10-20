# LLM-001: llama.cpp `MAX_REPETITION_THRESHOLD` breaks tool-calling with many optional params

**Date:** 2026-07-31
**Symptom:** LiteLLM logs show `litellm.BadRequestError: OpenAIException - Failed to initialize samplers: failed to parse grammar` when OpenClaw sends requests with tools to local llama.cpp models (Qwen3.6-27B, Qwen3.6-35B-A3B).

**Root cause (two separate issues):**

1. **Regex escapes in tool schemas** — The primary cause. OpenClaw tool schemas contain JSON Schema `pattern` fields with regex escapes like `\S` (non-whitespace), `\d`, `\w`, etc. When llama.cpp converts tool schemas to GBNF grammar, these regex escapes are invalid in GBNF syntax. The grammar parser fails with `parse: error parsing grammar: unknown escape at \S") "\""`. This is the error that was actually happening in production.

2. **`MAX_REPETITION_THRESHOLD` too low** — A secondary issue. llama.cpp hardcodes `#define MAX_REPETITION_THRESHOLD 2000` in `src/llama-grammar.cpp`. Tool schemas with many optional parameters can exceed this limit. This was patched to 100000 as a precaution, but was NOT the cause of the production errors.

**Fixes applied (both required, verified working 2026-07-31):**

### Fix 1: Strip regex escapes from tool schema patterns (LiteLLM callback)

Updated `sanitize_tool_schemas.py` in the LiteLLM container (`/app/callbacks/sanitize_tool_schemas.py`) to strip `pattern` fields that contain regex escapes GBNF can't handle (`\S`, `\d`, `\w`, `\D`, `\W`, `\b`, `\s`). The callback checks each `pattern` field with `re.compile(r'\\[SdDwWbBsS]')` and removes the pattern entirely if it contains unsupported escapes. Valid patterns are still anchored with `^` and `$` as before.

### Fix 2: Recompile llama.cpp with `MAX_REPETITION_THRESHOLD=100000`

The `MAX_REPETITION_THRESHOLD` constant lives in `src/llama-grammar.cpp` (line 14). The constant is compiled into `libllama.so` (NOT `libllama-common.so` as initially assumed — `grep -c "repetitions"` confirmed the string is in `libllama.so.0.0.10202`).

**Critical build lesson — the `llama-server` binary is a 17KB thin wrapper.** The actual code lives in shared libraries:
- `libllama.so.0.0.10202` (4.2MB) — contains the grammar parser with `MAX_REPETITION_THRESHOLD`
- `libllama-common.so.0.0.10202` (5.9MB) — common utilities
- `libllama-server-impl.so` (7.4MB) — server implementation

**The Dockerfile must:**
1. `rm -f` the OLD versioned `.so` files from the base image (`libllama-common.so.0.0.9859`, `libllama.so.0.0.9859`) — otherwise the old unpatched libraries remain and the symlinks still point to them
2. Copy the NEW versioned `.so` files from the builder (`libllama-common.so.0.0.10202`, `libllama.so.0.0.10202`)
3. Recreate the symlinks to point to the new versioned files
4. Run `ldconfig` to update the dynamic linker cache

**Verification commands:**
```bash
# Confirm symlinks point to patched version
docker exec llama-cpp-server readlink -f /app/libllama-common.so  # should show .0.0.10202
docker exec llama-cpp-server readlink -f /app/libllama.so          # should show .0.0.10202

# Confirm old versioned file is gone
docker exec llama-cpp-server ls /app/libllama-common.so.0.0.9859  # should fail

# Confirm the patched library has the grammar code
docker exec llama-cpp-server grep -c "repetitions" /app/libllama.so.0.0.10202  # should be >0

# Confirm ldd links against patched libs
docker exec llama-cpp-server ldd /app/llama-server | grep llama
```

**Build gotchas:**
- The official `ghcr.io/ggml-org/llama.cpp:server-cuda` image has the CUDA **runtime** but not the **toolkit** (no `nvcc`) — can't build from it directly
- The `nvidia/cuda:*-devel-*` image has `nvcc` but not `libcuda.so.1` (driver lib) — need to create a stub symlink for linking
- Unlimited parallelism (`-j`) causes OOM kills on 32GB RAM — use `-j 2`
- The container was deployed via Portainer, not `docker-compose` (which is broken on Python 3.12 due to missing `distutils`). Use `docker run` directly.
- **Copying just the `llama-server` binary is NOT enough** — it's a 17KB wrapper. Must copy the actual `.so` files and remove old versioned files first.

**Deployed:** Container `llama-cpp-server` running `llama-cpp-patched:latest` image on LLM box (`192.168.1.149:8080`). Compose file at `~/llamacpp-portainer-compose.yml` updated with:
- `MODEL_FILE: Qwen3.6-27B-Q4_K_M.gguf`
- `MODEL_ALIAS: Qwen3.6-27B`
- `CTX_SIZE: 131072`
- `NGL: 99`
- `BATCH_SIZE: 1024`
- `UBATCH_SIZE: 512`
- `CACHE_K_TYPE: q8_0`, `CACHE_V_TYPE: q8_0`

**Verified end-to-end:** 48-parameter browser tool + write tool request through LiteLLM → successful `tool_calls` response. Zero grammar errors in llama.cpp logs. `successful_requests: 1, failed_requests: 0`.

**Upstream status:** As of build 10202, the constant is still 2000 on master. PR #21216 (autoparser simplification) closed the issue but did not raise the constant. The fix has not been merged upstream.

**References:**
- https://github.com/ggml-org/llama.cpp/issues/20867
- https://github.com/ggml-org/llama.cpp/pull/21216
- Constant location: `src/llama-grammar.cpp` line 14
- Grammar code compiled into: `libllama.so` (NOT `libllama-common.so`)

**Wrong turns to avoid:**
- Blaming `--jinja` is a red herring. The flag controls templating, not grammar limits.
- Assuming `MAX_REPETITION_THRESHOLD` is the only cause — the actual production error was `unknown escape at \S`, a regex-to-GBNF conversion issue. Always check the llama.cpp server logs for the specific parse error, not just the LiteLLM error.
- Stripping `response_format`/`grammar` in a LiteLLM callback disables structured output entirely — it masks the problem but loses the feature.
- **Copying only the `llama-server` binary does nothing** — it's a 17KB wrapper. The actual code is in `libllama.so` and `libllama-common.so`. Must remove old versioned `.so` files and copy new ones + fix symlinks.
- **The grammar code is in `libllama.so`, not `libllama-common.so`.** Verify with `grep -c "repetitions"` on each library before assuming the patch took.
