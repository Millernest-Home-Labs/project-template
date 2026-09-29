---
name: loki-error-query
description: 'Query Loki logs for most frequent errors in LiteLLM, llama.cpp, and OpenClaw containers via Loki HTTP API'
---

# Loki Error Query Skill

**Query Loki logs for the most frequent errors across homelab containers.**

The Loki HTTP API is at `http://192.168.1.206:30953/loki/api/v1/query_range`. All queries use `pattern` to extract error messages into a `msg` label, then aggregate by `msg` with `sum by (msg) (count_over_time(...))`.

## Grafana Dashboard Aggregation

When building Grafana table panels from these queries, use `sum by (msg) (count_over_time(...))` with `queryType: "instant"` and `instant: true`. A range query returns repeated samples for the same message and produces duplicate table rows. Use `labelsToFields` followed by `organize`; do not add a second `groupBy` after Loki has already aggregated the message counts.

The complete three-tile dashboard recipe, including the ID-stripping patterns for llama.cpp and OpenClaw, is documented in [grafana-loki-error-dashboard.md](../../learnings/grafana-loki-error-dashboard.md).

## How to Run

Two options:

**Option A — bash (from Unraid or any Linux/SSH box with curl):**
```bash
LOKI="http://192.168.1.206:30953/loki/api/v1/query_range"
SIX_HOURS_AGO=$(date -d '6 hours ago' +%s)000000000
NOW=$(date +%s)000000000
```

**Option B — PowerShell (from Windows/VSCode, no SSH needed):**
```powershell
$start = [DateTimeOffset]::UtcNow.AddHours(-6).ToUnixTimeSeconds() * 1000000000
$end = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() * 1000000000
$loki = "http://192.168.1.206:30953/loki/api/v1/query_range"
```

Use the `Invoke-RestMethod` examples in each section for PowerShell queries.

---

## LiteLLM Errors

**Container name:** `LiteLLM`
**Log format:** `2025-01-01T00:00:00Z - INFO proxy_server.py:123 - func_name() - Message text`
**Pattern:** `<ts> - <lvl> <file>: <func> - <msg>`

### Most frequent error messages (last 6 hours)

**bash:**
```bash
curl -s "$LOKI" --data-urlencode "query=sum by (msg) (count_over_time({container=\"LiteLLM\"} |= \"ERROR\" | pattern \"<_> - <_> <_>: <_> - <msg>\" [6h]))" --data-urlencode "start=$SIX_HOURS_AGO" --data-urlencode "end=$NOW" --data-urlencode "step=3600" | python3 -c "
import json, sys
d = json.load(sys.stdin)
results = d.get('data',{}).get('result',[])
rows = []
for r in results:
    msg = r.get('metric',{}).get('msg','(no msg)')
    val = r.get('values',[[None,'0']])[0][1]
    rows.append((int(val), msg))
rows.sort(reverse=True)
for count, msg in rows:
    print(f'{count:>5}x  {msg}')
if not rows:
    print('No error results')
"
```

**PowerShell:**
```powershell
$query = 'sum by (msg) (count_over_time({container="LiteLLM"} |= "ERROR" | pattern "<_> - <_> <_>: <_> - <msg>" [6h]))'
$result = Invoke-RestMethod -Uri "$loki?query=$([System.Web.HttpUtility]::UrlEncode($query))&start=$start&end=$end&step=3600"
$rows = [System.Collections.ArrayList]@()
foreach($r in $result.data.result) {
    $msg = if ($r.metric.msg) { $r.metric.msg } else { '(no msg)' }
    $count = [int]$r.values[0][1]
    $rows.Add([PSCustomObject]@{Count = $count; Message = $msg}) | Out-Null
}
$rows | Sort-Object Count -Descending | Format-Table -AutoSize
```

### Raw error logs (last 30 minutes)

**bash:**
```bash
curl -s "$LOKI" --data-urlencode 'query={container="LiteLLM"} |= "ERROR" | pattern "<_> - <_> <_>: <_> - <msg>"' --data-urlencode "start=$(date -d '30 minutes ago' +%s)000000000" --data-urlencode "end=$NOW" --data-urlencode "step=1" --data-urlencode "direction=backward" --data-urlencode "limit=50" | python3 -c "import json,sys;d=json.load(sys.stdin);[print(line) for s in d.get('data',{}).get('result',[]) for ts,line in s.get('values',[])]"
```

**PowerShell:**
```powershell
$query = '{container="LiteLLM"} |= "ERROR"'
$timeAgo = [DateTimeOffset]::UtcNow.AddMinutes(-30).ToUnixTimeSeconds() * 1000000000
$result = Invoke-RestMethod -Uri "$loki?query=$([System.Web.HttpUtility]::UrlEncode($query))&start=$timeAgo&end=$end&step=1&direction=backward&limit=50"
foreach($s in $result.data.result) { foreach($v in $s.values) { Write-Host $v[1] } }
```

---

## llama.cpp Errors

**Container name:** `llama-cpp-server`
**Log format:** `2314.50.567.711 E srv    send_error: task id = N, error: Failed to initialize samplers: ...`
**Note:** Each `send_error` message has a unique task ID, so they appear as separate entries. Use the `count_over_time` fallback for total volume, or the pattern parser to see the top distinct messages.

### Most frequent errors (last 6 hours)

**PowerShell:**
```powershell
$loki = "http://192.168.1.206:30953/loki/api/v1/query_range"
$start = [DateTimeOffset]::UtcNow.AddHours(-6).ToUnixTimeSeconds() * 1000000000
$end = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() * 1000000000

# Pattern parser: extract message after "E srv " component
$query = 'sum by (msg) (count_over_time({container="llama-cpp-server"} |= "error" | pattern "<_> E <_> <msg>" [6h]))'
$result = Invoke-RestMethod -Uri "$loki?query=$([System.Web.HttpUtility]::UrlEncode($query))&start=$start&end=$end&step=3600"
$rows = [System.Collections.ArrayList]@()
foreach($r in $result.data.result) {
    $msg = if ($r.metric.msg) { $r.metric.msg } else { '(empty - grammar parse errors)' }
    $count = [int]$r.values[0][1]
    $rows.Add([PSCustomObject]@{Count = $count; Message = $msg}) | Out-Null
}
$rows | Sort-Object Count -Descending | Format-Table -AutoSize -Wrap

# Fallback: total error line count
Write-Host "`n=== Total error lines ==="
$q2 = 'count_over_time({container="llama-cpp-server"} |= "error" [6h])'
$r2 = Invoke-RestMethod -Uri "$loki?query=$([System.Web.HttpUtility]::UrlEncode($q2))&start=$start&end=$end&step=3600"
$total = 0
foreach($series in $r2.data.result) { foreach($v in $series.values) { $total += [int]$v[1] } }
Write-Host "Total error lines in 6h: $total"
```

**bash:**
```bash
# Pattern parser
curl -s "$LOKI" --data-urlencode "query=sum by (msg) (count_over_time({container=\"llama-cpp-server\"} |= \"error\" | pattern \"<_> E <_> <msg>\" [6h]))" --data-urlencode "start=$SIX_HOURS_AGO" --data-urlencode "end=$NOW" --data-urlencode "step=3600" | python3 -c "import json,sys;d=json.load(sys.stdin);rows=[(int(r.get('values',[[None,'0']])[0][1]),r.get('metric',{}).get('msg','(empty)')) for r in d.get('data',{}).get('result',[])];rows.sort(reverse=True);[print(f'{c:>5}x  {m[:200]}') for c,m in rows[:20]] or print('No pattern results')"

# Total error line count
curl -s "$LOKI" --data-urlencode "query=count_over_time({container=\"llama-cpp-server\"} |= \"error\" [6h])" --data-urlencode "start=$SIX_HOURS_AGO" --data-urlencode "end=$NOW" --data-urlencode "step=3600" | python3 -c "import json,sys;d=json.load(sys.stdin);total=sum(int(v[1]) for r in d.get('data',{}).get('result',[]) for v in r.get('values',[]));print(f'Total error lines in 6h: {total}')"
```

### Raw llama.cpp logs (last 30 minutes)

```powershell
$timeAgo = [DateTimeOffset]::UtcNow.AddMinutes(-30).ToUnixTimeSeconds() * 1000000000
$result = Invoke-RestMethod -Uri "$loki?query=$([System.Web.HttpUtility]::UrlEncode('{container="llama-cpp-server"}'))&start=$timeAgo&end=$end&step=120&direction=backward&limit=30"
foreach($s in $result.data.result) { foreach($v in $s.values) { Write-Host $v[1] } }
```

---

## OpenClaw Errors

**Container name:** `OpenClaw`
**Log format:** `2026-08-05T15:18:53.853-07:00 [ws] ⇄ res ✗ agent 142ms errorCode=INVALID_REQUEST errorMessage=Error: Channel is required...`
**Note:** OpenClaw logs use `errorCode=INVALID_REQUEST errorMessage=...` format, not structured Python logging. The LiteLLM pattern won't match. Use grep-based counts or the per-category queries below.

### Error categories (last 6 hours)

**PowerShell:**
```powershell
$loki = "http://192.168.1.206:30953/loki/api/v1/query_range"
$start = [DateTimeOffset]::UtcNow.AddHours(-6).ToUnixTimeSeconds() * 1000000000
$end = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() * 1000000000

# Total log volume
$q = 'count_over_time({container="OpenClaw"} [6h])'
$r = Invoke-RestMethod -Uri "$loki?query=$([System.Web.HttpUtility]::UrlEncode($q))&start=$start&end=$end&step=3600"
$total = 0; foreach($s in $r.data.result) { foreach($v in $s.values) { $total += [int]$v[1] } }
Write-Host "Total log lines: $total"

# Error/exception/traceback lines (case-insensitive)
$q = 'count_over_time({container="OpenClaw"} |~ "(?i)error|exception|traceback" [6h])'
$r = Invoke-RestMethod -Uri "$loki?query=$([System.Web.HttpUtility]::UrlEncode($q))&start=$start&end=$end&step=3600"
$c = 0; foreach($s in $r.data.result) { foreach($v in $s.values) { $c += [int]$v[1] } }
Write-Host "`n--- Error category breakdown ---"
Write-Host "error/exception lines: $c"

# errorCode lines (structured errors)
$q = 'count_over_time({container="OpenClaw"} |= "errorCode" [6h])'
$r = Invoke-RestMethod -Uri "$loki?query=$([System.Web.HttpUtility]::UrlEncode($q))&start=$start&end=$end&step=3600"
$c = 0; foreach($s in $r.data.result) { foreach($v in $s.values) { $c += [int]$v[1] } }
Write-Host "  errorCode lines: $c"

# unknown method warnings (client-side issues)
$q = 'count_over_time({container="OpenClaw"} |= "unknown method" [6h])'
$r = Invoke-RestMethod -Uri "$loki?query=$([System.Web.HttpUtility]::UrlEncode($q))&start=$start&end=$end&step=3600"
$c = 0; foreach($s in $r.data.result) { foreach($v in $s.values) { $c += [int]$v[1] } }
Write-Host "  unknown method lines: $c"

# model-fallback decisions (model routing events)
$q = 'count_over_time({container="OpenClaw"} |= "model-fallback" [6h])'
$r = Invoke-RestMethod -Uri "$loki?query=$([System.Web.HttpUtility]::UrlEncode($q))&start=$start&end=$end&step=3600"
$c = 0; foreach($s in $r.data.result) { foreach($v in $s.values) { $c += [int]$v[1] } }
Write-Host "  model-fallback events: $c"

# Channel is required errors
$q = 'count_over_time({container="OpenClaw"} |= "Channel is required" [6h])'
$r = Invoke-RestMethod -Uri "$loki?query=$([System.Web.HttpUtility]::UrlEncode($q))&start=$start&end=$end&step=3600"
$c = 0; foreach($s in $r.data.result) { foreach($v in $s.values) { $c += [int]$v[1] } }
Write-Host "  Channel is required errors: $c"

# model-fetch errors
$q = 'count_over_time({container="OpenClaw"} |= "model-fetch" |= "error" [6h])'
$r = Invoke-RestMethod -Uri "$loki?query=$([System.Web.HttpUtility]::UrlEncode($q))&start=$start&end=$end&step=3600"
$c = 0; foreach($s in $r.data.result) { foreach($v in $s.values) { $c += [int]$v[1] } }
Write-Host "  model-fetch errors: $c"
```

**bash:**
```bash
LOKI="http://192.168.1.206:30953/loki/api/v1/query_range"
SIX_HOURS_AGO=$(date -d '6 hours ago' +%s)000000000
NOW=$(date +%s)000000000

echo "=== OpenClaw error categories ==="
for filter in "errorCode" "unknown method" "model-fallback" "Channel is required" "model-fetch.*error"; do
  count=$(curl -s "$LOKI" --data-urlencode "query=count_over_time({container=\"OpenClaw\"} |= \"$filter\" [6h])" \
    --data-urlencode "start=$SIX_HOURS_AGO" --data-urlencode "end=$NOW" --data-urlencode "step=3600" | \
    python3 -c "import json,sys;d=json.load(sys.stdin);print(sum(int(v[1]) for r in d.get('data',{}).get('result',[]) for v in r.get('values',[])))")
  echo "  $filter: $count"
done
```

### Raw OpenClaw logs (last 30 minutes)

```powershell
$timeAgo = [DateTimeOffset]::UtcNow.AddMinutes(-30).ToUnixTimeSeconds() * 1000000000
$result = Invoke-RestMethod -Uri "$loki?query=$([System.Web.HttpUtility]::UrlEncode('{container="OpenClaw"}'))&start=$timeAgo&end=$end&step=120&direction=backward&limit=20"
foreach($s in $result.data.result) { foreach($v in $s.values) { Write-Host $v[1]; Write-Host '---' } }
```

---

## All Errors Summary (cross-container)

### Count errors across all 3 containers (last 6 hours)

**PowerShell:**
```powershell
$loki = "http://192.168.1.206:30953/loki/api/v1/query_range"
$start = [DateTimeOffset]::UtcNow.AddHours(-6).ToUnixTimeSeconds() * 1000000000
$end = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() * 1000000000
$containers = @('LiteLLM', 'llama-cpp-server', 'OpenClaw')

foreach($container in $containers) {
    Write-Host "=== $container ==="
    $result = Invoke-RestMethod -Uri "$loki?query=$([System.Web.HttpUtility]::UrlEncode("count_over_time({container=`"$container`"} |= ""error"" [6h])"))&start=$start&end=$end&step=3600"
    $total = 0
    foreach($series in $result.data.result) { foreach($v in $series.values) { $total += [int]$v[1] } }
    Write-Host "  Total error lines: $total"
}
```

**bash:**
```bash
LOKI="http://192.168.1.206:30953/loki/api/v1/query_range"
SIX_HOURS_AGO=$(date -d '6 hours ago' +%s)000000000
NOW=$(date +%s)000000000

for container in LiteLLM llama-cpp-server OpenClaw; do
  total=$(curl -s "$LOKI" --data-urlencode "query=count_over_time({container=\"$container\"} |= \"error\" [6h])" \
    --data-urlencode "start=$SIX_HOURS_AGO" --data-urlencode "end=$NOW" --data-urlencode "step=3600" | \
    python3 -c "import json,sys;d=json.load(sys.stdin);print(sum(int(v[1]) for r in d.get('data',{}).get('result',[]) for v in r.get('values',[])))")
  echo "$container: $total error lines"
done
```

---

## Configuration Reference

| Property | Value |
|---|---|
| Loki URL | `http://192.168.1.206:30953` |
| Loki API path | `/loki/api/v1/query_range` |
| Log containers | `LiteLLM`, `llama-cpp-server`, `OpenClaw` |
| Promtail hosts | Unraid (`host=unraid`), LLM box (`host=llm-box`) |
| Filter all containers | `{host=~"unraid|llm-box"}` |

### Notes

- **LiteLLM** log format: `2025-01-01T00:00:00Z - INFO proxy_server.py:123 - func_name() - Message text`. Pattern `<ts> - <lvl> <file>: <func> - <msg>` extracts well.
- **llama.cpp** log format: `2314.50.567.711 E srv    send_error: task id = N, error: ...`. Use `| pattern "<_> E <_> <msg>"`. Each `send_error` has a unique task ID so they won't group together — use total count for volume.
- **OpenClaw** log format: `2026-08-05T... [ws] ⇄ res ✗ agent ...ms errorCode=X errorMessage=...`. Does NOT use structured Python logging. Use `|~ "(?i)error|exception|traceback"` or per-category `|= "errorCode"` grep queries.
- **PowerShell** works directly from VSCode using `Invoke-RestMethod` with `[System.Web.HttpUtility]::UrlEncode()`. No SSH needed — Loki NodePort `30953` is routable.
- The Loki API is at NodePort `30953` on K3s node `192.168.1.206`.
- ANSI color codes in LiteLLM logs are stripped by Promtail before ingestion.