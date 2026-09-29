---
name: namecheap-dns
description: 'Manage DNS records for millernest.com via the Namecheap API using credentials from the k3s cluster. Add, list, and verify A records without a browser.'
---

# Namecheap DNS Skill

**Manage DNS records for `millernest.com` via the Namecheap API.**

This skill uses the Namecheap XML API, not browser automation. Browser automation
(`agent-browser`) is **not viable** for Namecheap: Cloudflare Turnstile blocks
headless browsers indefinitely and flags automated clicks even in headed mode.
The API is the purpose-built, headless, agent-friendly path and works identically
from a laptop and from the OpenClaw container.

## Prerequisites

- `kubectl` configured for the k3s cluster (verify: `kubectl get secret namecheap-login -n default`)
- The k3s secret `namecheap-login` (namespace `default`) must contain **four** keys:
  `username`, `password`, `api_user`, `api_key`.
  - `username` / `password` — the Namecheap account login (used in the API hash).
  - `api_user` / `api_key` — the API credentials from the Namecheap UI:
    **Account → Advanced API → API User / API Key**.
  - If `api_user` / `api_key` are missing from the secret, stop and ask the user to
    create an API user in the Namecheap UI and add the two keys to the secret:
    `kubectl patch secret namecheap-login -n default -p '{"data":{"api_user":"<b64>","api_key":"<b64>"}}'`
    (base64-encode the values first).
- PowerShell (Windows) or bash + `jq` + `python3` + `curl` (Linux/OpenClaw).

## Step 1 — Add an A record

Windows PowerShell (from the skill directory):

```powershell
.\namecheap.ps1 -Command namecheap.domains.dns.host.create -Params @{
    sld='millernest'; tdn='com'; host='api.reflexia'; ip='99.129.41.20'; type='A'; ttl='600'
}
```

Linux / OpenClaw:

```bash
./namecheap.sh namecheap.domains.dns.host.create sld=millernest tdn=com \
    host=api.reflexia ip=99.129.41.20 type=A ttl=600
```

Parameters:

| Param | Meaning | Example |
|---|---|---|
| `sld` | Second-level domain | `millernest` |
| `tdn` | Top-level domain | `com` |
| `host` | Record host (subdomain). Use `@` for the apex | `api.reflexia` |
| `ip` | IPv4 address (for `A` records) | `99.129.41.20` |
| `type` | Record type | `A` |
| `ttl` | Time-to-live in seconds | `600` |

The script prints `API_STATUS=... COMMAND_STATUS=...` followed by the raw XML.
Success looks like:

```xml
<CommandStatus Status="OK" Description="Host record created successfully" />
```

## Step 2 — Verify

List the domain's custom DNS records and confirm the new record is present:

```powershell
.\namecheap.ps1 -Command namecheap.domains.dns.custom -Params @{ sld='millernest'; tdn='com' }
```

```bash
./namecheap.sh namecheap.domains.dns.custom sld=millernest tdn=com
```

The response contains a `<HostRecord>` element per record with `Host`, `IP`,
`Type`, and `TTL`. Confirm the requested host/value appears. Report the record
as displayed to the user.

## Other record operations

| Operation | Command | Extra params |
|---|---|---|
| List records | `namecheap.domains.dns.custom` | — |
| Create record | `namecheap.domains.dns.host.create` | `host`, `ip`, `type`, `ttl` |
| Update record | `namecheap.domains.dns.host.update` | `host`, `ip`, `type`, `ttl` |
| Delete record | `namecheap.domains.dns.host.delete` | `host`, `type` |

Only perform operations the user explicitly requested. Never delete or modify
records without an explicit request.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `API_STATUS=ERROR` with `Invalid credentials` | The `username`/`password` in the secret are wrong, or the account is locked. Ask the user. |
| `API_STATUS=ERROR` with `Invalid API user or key` | `api_user`/`api_key` missing or wrong in the secret. See Prerequisites. |
| `API_STATUS=ERROR` with `Invalid hash` | Clock skew — sync the system clock; the hash includes a timestamp. |
| `Host already exists` on create | The record exists. Use `host.update` only if the user asked to change it; otherwise report and stop. |
| `kubectl: command not found` (OpenClaw) | Use `/appdata/bin/kubectl` with `KUBECONFIG=/appdata/kube/config`. |
| `jq: command not found` | `apt-get install -y jq` (or use the PowerShell script from a Windows host). |

## Rules

- Never print, log, or commit the username, password, api_user, or api_key.
  The helper scripts decode them in memory only.
- Only add/modify/delete records the user explicitly requested.
- Stop and report the exact API error on any failure. Do not retry more than once.
- Do not fall back to browser automation — Cloudflare Turnstile blocks it.

## Why not browser automation?

`namecheap.com` sits behind Cloudflare Turnstile. Observed behavior (2026-08):

- Headless `agent-browser`: the "Verify you are human" checkbox loops forever.
- Headed `agent-browser` with human-like mouse movement: passes once, then
  subsequent challenges flag the automated click and loop.
- The login URL `https://www.namecheap.com/account/login/` 404s; the working
  path is the homepage "Sign in" overlay.

These are anti-automation controls by design. The API is the supported,
stable, headless path for programmatic DNS management.
