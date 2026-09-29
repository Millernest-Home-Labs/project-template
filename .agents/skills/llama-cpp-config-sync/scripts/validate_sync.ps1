param(
    [int]$ExpectedTotalSlots = 2,
    [int]$ExpectedPerSlotContext = 88064,
    [int]$ExpectedLiteLLMParallelRequests = 2,
    [int]$ExpectedCompactionThreshold = 60000,
    [string]$LlamaHost = '192.168.1.149',
    [string]$UnraidHost = '192.168.1.194'
)

$ErrorActionPreference = 'Stop'

function Assert-Equal {
    param(
        [string]$Name,
        [object]$Actual,
        [object]$Expected
    )

    if ($Actual -ne $Expected) {
        throw "$Name expected '$Expected' but found '$Actual'."
    }

    Write-Host "$Name=$Actual"
}

$health = Invoke-RestMethod -Uri "http://$LlamaHost`:8080/health" -TimeoutSec 15
Assert-Equal -Name 'llama_health' -Actual $health.status -Expected 'ok'

$props = Invoke-RestMethod -Uri "http://$LlamaHost`:8080/props" -TimeoutSec 15
Assert-Equal -Name 'llama_total_slots' -Actual ([int]$props.total_slots) -Expected $ExpectedTotalSlots

$inspect = ssh -i "$env:USERPROFILE\.ssh\id_ed25519_ubuntu" "ethan@$LlamaHost" "docker inspect llama-cpp-server --format '{{json .Config.Cmd}}'"
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to inspect llama-cpp-server.'
}

$command = $inspect | ConvertFrom-Json
$parallelIndex = [Array]::IndexOf([array]$command, '-np')
$contextIndex = [Array]::IndexOf([array]$command, '-c')
if ($parallelIndex -lt 0 -or $contextIndex -lt 0) {
    throw 'The llama.cpp command does not expose -np and -c arguments.'
}
Assert-Equal -Name 'llama_parallel_arg' -Actual ([int]$command[$parallelIndex + 1]) -Expected $ExpectedTotalSlots
Assert-Equal -Name 'llama_total_context_arg' -Actual ([int]$command[$contextIndex + 1]) -Expected ($ExpectedTotalSlots * $ExpectedPerSlotContext)

$liteConfig = ssh root@$UnraidHost "sed -n '1,24p' /mnt/user/appdata/litellm/config.yaml"
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to read LiteLLM configuration.'
}
$liteMatch = [regex]::Match(($liteConfig -join "`n"), '(?s)model_name:\s*Qwen3\.6-27B.*?max_parallel_requests:\s*(\d+)')
if (-not $liteMatch.Success) {
    throw 'Unable to find the Qwen3.6-27B LiteLLM entry.'
}
Assert-Equal -Name 'litellm_qwen_parallel_requests' -Actual ([int]$liteMatch.Groups[1].Value) -Expected $ExpectedLiteLLMParallelRequests

$compactionSource = ssh root@$UnraidHost "grep -nE 'COMPACT_CONTEXT_LIMIT|COMPACT_TOKEN_THRESHOLD' /mnt/user/appdata/litellm/callbacks/context_semantic_compaction.py"
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to read LiteLLM semantic-compaction defaults.'
}
$compactionText = $compactionSource -join "`n"
$limitMatch = [regex]::Match($compactionText, 'COMPACT_CONTEXT_LIMIT[\s\S]*?LITELLM_COMPACT_CONTEXT_LIMIT", "(\d+)"')
$thresholdMatch = [regex]::Match($compactionText, 'COMPACT_TOKEN_THRESHOLD[\s\S]*?LITELLM_COMPACT_TOKEN_THRESHOLD", "(\d+)"')
if (-not $limitMatch.Success -or -not $thresholdMatch.Success) {
    throw 'Unable to find semantic-compaction context limit and threshold.'
}
Assert-Equal -Name 'litellm_compaction_context_limit' -Actual ([int]$limitMatch.Groups[1].Value) -Expected $ExpectedPerSlotContext
Assert-Equal -Name 'litellm_compaction_threshold' -Actual ([int]$thresholdMatch.Groups[1].Value) -Expected $ExpectedCompactionThreshold

$compactionEnv = ssh root@$UnraidHost "docker inspect LiteLLM --format '{{range .Config.Env}}{{println .}}{{end}}'"
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to inspect LiteLLM environment overrides.'
}
foreach ($setting in @(
    @{ Name = 'LITELLM_COMPACT_CONTEXT_LIMIT'; Expected = $ExpectedPerSlotContext },
    @{ Name = 'LITELLM_COMPACT_TOKEN_THRESHOLD'; Expected = $ExpectedCompactionThreshold }
)) {
    $override = [regex]::Match(($compactionEnv -join "`n"), "^$($setting.Name)=(\d+)$", [System.Text.RegularExpressions.RegexOptions]::Multiline)
    if ($override.Success) {
        Assert-Equal -Name "litellm_env_$($setting.Name)" -Actual ([int]$override.Groups[1].Value) -Expected $setting.Expected
    }
}

$nodeScript = @'
const fs = require('fs');
const d = JSON.parse(fs.readFileSync('/root/.openclaw/openclaw.json', 'utf8'));
const rows = [];
for (const [providerName, provider] of Object.entries(d.models?.providers ?? {})) {
  for (const model of provider.models ?? []) {
    if (model.id === 'Qwen3.6-27B') rows.push(`${providerName}=${model.contextWindow}`);
  }
}
if (rows.length === 0) throw new Error('No Qwen3.6-27B OpenClaw model entries found.');
console.log(rows.join('\n'));
'@
$nodeBase64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($nodeScript))
$openclawRows = ssh root@$UnraidHost "echo $nodeBase64 | base64 -d | docker exec -i OpenClaw node -"
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to read or parse OpenClaw configuration.'
}

$rows = @($openclawRows | Where-Object { $_ -match '=' })
if ($rows.Count -lt 2) {
    throw "Expected at least two OpenClaw Qwen entries but found $($rows.Count)."
}
foreach ($row in $rows) {
    $parts = $row -split '=', 2
    Assert-Equal -Name "openclaw_$($parts[0])_context_window" -Actual ([int]$parts[1]) -Expected $ExpectedPerSlotContext
}

Write-Host 'validation=passed'
