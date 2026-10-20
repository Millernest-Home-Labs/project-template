# Learning: Adding HTTPS/SSL to an Existing Nginx Proxy Manager Domain

**Date:** 2026-03-14
**Issue:** Browser showing "Not Secure" on reflexia.millernest.com despite Let's Encrypt being configured elsewhere on the same Nginx Proxy Manager instance.

---

## Background

The Reflexia app has two relevant domains:

- reflexia.millernest.com  the dev k3s namespace, **already had HTTPS**
- reflexia.millernest.com  the prod k3s namespace, **HTTP only** (no SSL configured)

The app was deployed to prod but HTTPS was never configured in the Nginx Proxy Manager (NPM) instance running on Unraid. The browser saw plain HTTP and correctly flagged it as "Not Secure."

---

## Infrastructure Overview

| Component | Location | Role |
|---|---|---|
| Nginx Proxy Manager | Unraid Docker container NginxProxyManager | Reverse proxy, SSL termination |
| k3s cluster | 192.168.1.206 (Unraid VM) | Runs wish-hunter-client + wish-hunter-server pods |
| Traefik | Inside k3s | Internal ingress, HTTP only (TLS terminated at NPM) |
| NPM data | /mnt/user/appdata/NginxProxyManager/ | Persistent volume with SQLite DB and cert files |

Port mapping on NPM container: 443 -> 4443 (host:container), 80 -> 8080.

---

## Step 1: Confirm SSH Connectivity to Unraid

```powershell
ssh root@192.168.1.194 "echo 'Connected'"
```

**Why:** Before any remote investigation, verify that key-based SSH auth to the Unraid server works. The Unraid IP is 192.168.1.194. SSH keys were already configured (see .github/skills/unraid-ssh-connection/SKILL.md).

---

## Step 2: Identify the Nginx Container

```powershell
ssh root@192.168.1.194 "docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}'"
```

**Why:** Need to know the exact container name to run docker exec commands. Found NginxProxyManager image jlesage/nginx-proxy-manager with ports 443->4443, 80->8080.

---

## Step 3: Find All Let's Encrypt Certificates

```powershell
ssh root@192.168.1.194 "docker exec NginxProxyManager ls /etc/letsencrypt/live/"
```

**Why:** NPM stores each cert in a numbered directory (
pm-1, 
pm-2, ...). Need to find which number corresponds to the auctions/wishlist domains. The naming scheme is opaque  you have to check each cert.

```powershell
ssh root@192.168.1.194 "docker exec NginxProxyManager openssl x509 -noout -subject -enddate -in /etc/letsencrypt/live/npm-46/cert.pem"
```

**Why:** openssl x509 -noout -subject -enddate shows the domain name (CN) and expiry date without printing the full cert. Ran this for all numbered dirs to identify:
- 
pm-46 = uctions.millernest.com (has cert, expires 2026-05-29)
- No cert for wishlist.millernest.com yet

---

## Step 4: Inspect NPM's Nginx Config Files

```powershell
ssh root@192.168.1.194 "docker exec NginxProxyManager grep -rl 'wishlist' /data/nginx/"
#  /data/nginx/proxy_host/14.conf

ssh root@192.168.1.194 "docker exec NginxProxyManager cat /data/nginx/proxy_host/14.conf"
```

**Why:** NPM generates one .conf file per proxy host in /data/nginx/proxy_host/. By searching for the domain name you find the relevant config. The conf for host 14 only had listen 8080 (HTTP) with no listen 4443 ssl or ssl_certificate directives  confirming no HTTPS.

---

## Step 5: Query the NPM SQLite Database

```powershell
ssh root@192.168.1.194 "sqlite3 /mnt/user/appdata/NginxProxyManager/database.sqlite 'SELECT id, domain_names, ssl_forced, certificate_id FROM proxy_host'"
```

**Why:** NPM uses a SQLite database at /mnt/user/appdata/NginxProxyManager/database.sqlite to store all proxy host configuration. The columns that matter for SSL are:
- ssl_forced  1 = redirect HTTP to HTTPS; 0 = HTTP only
- certificate_id  FK to the certificate table; 0 = no cert assigned

Result confirmed proxy host 14 (wishlist.millernest.com) had ssl_forced=0, certificate_id=0.

---

## Step 6: Verify the Existing TLS Handshake (Baseline)

```bash
# Run from Unraid via SSH
echo | openssl s_client -connect auctions.millernest.com:443 -servername auctions.millernest.com 2>&1 | grep -E 'subject|issuer|Verify|Protocol|depth'
```

**Why:** Before making changes, establish a working baseline. This confirmed that uctions.millernest.com was serving valid TLS 1.3 with Verify return code: 0 (ok)  so the NPM/nginx stack was healthy, the problem was purely config.

---

## Step 7: Temporarily Add the ACME Challenge Handler

Let's Encrypt verifies domain ownership by placing a file at /.well-known/acme-challenge/ and checking that it's publicly accessible. NPM's HTTPHTTPS redirect was interfering  HTTP requests to wishlist were being proxied directly to k3s (which returned the SPA, not the challenge file).

```python
# Wrote this Python script, copied into the NPM container, and ran it:
with open('/data/nginx/proxy_host/14.conf', 'r') as f:
    content = f.read()
acme = '\n  include conf.d/include/letsencrypt-acme-challenge.conf;\n'
content = content.replace('\n  location / {', acme + '  location / {', 1)
with open('/data/nginx/proxy_host/14.conf', 'w') as f:
    f.write(content)
```

```powershell
# Copy script into container and run it
docker cp /tmp/fix_acme.py NginxProxyManager:/tmp/fix_acme.py
docker exec NginxProxyManager python3 /tmp/fix_acme.py

# Reload nginx to activate the change
docker exec NginxProxyManager nginx -s reload
```

**Why NPM's built-in acme include works:** The file /etc/nginx/conf.d/include/letsencrypt-acme-challenge.conf serves files from /data/letsencrypt-acme-challenge (the webroot) before any proxy or redirect rules apply. Adding it before location / gives certbot a path to place and serve challenge tokens.

---

## Step 8: Issue the Let's Encrypt Certificate

```powershell
ssh root@192.168.1.194 "docker exec NginxProxyManager certbot certonly \
  --webroot -w /data/letsencrypt-acme-challenge \
  -d wishlist.millernest.com \
  --agree-tos --email ethan.romans5.8@gmail.com \
  --non-interactive --cert-name npm-48"
```

**Why each flag:**
- certonly  obtain cert but don't configure any server (NPM manages nginx, not certbot)
- --webroot -w /data/letsencrypt-acme-challenge  use the HTTP-01 challenge via the webroot already served by NPM
- --cert-name npm-48  name it 
pm-48 to continue NPM's numbering convention; files land in /etc/letsencrypt/live/npm-48/
- --non-interactive  required for scripted/automated use

Result: Successfully received certificate. Certificate is saved at: /etc/letsencrypt/live/npm-48/fullchain.pem

---

## Step 9: Register the Cert in the NPM Database

NPM only knows about certs that are in its SQLite certificate table. The cert we issued manually with certbot is on disk but NPM doesn't know it exists yet.

```bash
# Insert the cert record
sqlite3 "" "INSERT OR REPLACE INTO certificate (id, created_on, modified_on, owner_user_id, is_deleted, provider, nice_name, domain_names, expires_on, meta)
VALUES (48, datetime('now'), datetime('now'), 1, 0, 'letsencrypt', 'wishlist.millernest.com', '[\"wishlist.millernest.com\"]', '2026-06-12 00:00:00',
'{\"letsencrypt_agree\":true,\"dns_challenge\":false,\"nginx_online\":true,\"nginx_err\":null,\"letsencrypt_email\":\"ethan.romans5.8@gmail.com\"}')"

# Update the proxy host to use the cert and force SSL
sqlite3 "" "UPDATE proxy_host SET ssl_forced=1, certificate_id=48, http2_support=1, meta='{\"letsencrypt_email\":\"ethan.romans5.8@gmail.com\",\"letsencrypt_agree\":true,\"dns_challenge\":false,\"nginx_online\":true,\"nginx_err\":null}', modified_on=datetime('now') WHERE id=14"
```

**Why the meta field matters:** NPM uses the meta JSON to know a cert is Let's Encrypt-managed and to track the email for renewal. Getting letsencrypt_agree: false in proxy host meta or unquoted JSON in the cert meta causes NPM to ignore the SSL association when regenerating configs.

**Fields set on proxy_host:**
- ssl_forced=1  generate HTTPHTTPS 301 redirect
- certificate_id=48  reference the new cert
- http2_support=1  enable HTTP/2 (matches the working auctions config)

---

## Step 10: Generate the SSL Nginx Config

NPM only regenerates proxy host .conf files when a change is made through its web UI or API  **not on container restart**. Since we modified the database directly, NPM will not automatically regenerate conf 14 with SSL. The solution is to generate it manually by templating from the working conf 13 (auctions).

```python
with open('/data/nginx/proxy_host/13.conf', 'r') as f:
    content = f.read()
content = content.replace('auctions.millernest.com', 'wishlist.millernest.com')
content = content.replace('npm-46', 'npm-48')
content = content.replace('proxy-host-13', 'proxy-host-14')
with open('/data/nginx/proxy_host/14.conf', 'w') as f:
    f.write(content)
```

**Why template from conf 13:** Conf 13 was generated by NPM with identical settings (same forward host 192.168.1.206, same port 80, same Force SSL, same HSTS map). The only differences are domain name, cert name, and log file names  all are simple string replacements.

The resulting conf 14 gains:
- listen 4443 ssl;  HTTPS on the mapped port
- http2 on;
- ssl_certificate /etc/letsencrypt/live/npm-48/fullchain.pem;
- ssl_certificate_key /etc/letsencrypt/live/npm-48/privkey.pem;
- include conf.d/include/force-ssl.conf;  301 redirect for HTTP

---

## Step 11: Validate Config and Reload Nginx

```powershell
ssh root@192.168.1.194 "docker exec NginxProxyManager nginx -t"
#  nginx: configuration file /etc/nginx/nginx.conf syntax is ok

ssh root@192.168.1.194 "docker exec NginxProxyManager nginx -s reload"
```

**Why 
ginx -t before reload:** A syntax error in any conf file will cause 
ginx -s reload to fail and take down all proxy hosts. Always validate first.

---

## Step 12: Verify End-to-End

```bash
# Test TLS handshake  must show Verify return code: 0 (ok)
echo | openssl s_client -connect wishlist.millernest.com:443 -servername wishlist.millernest.com 2>&1 | grep -E 'subject|issuer|Verify|Protocol|depth'

# Test HTTP redirect
curl -Is --max-time 5 http://wishlist.millernest.com | head -5
#  HTTP/1.1 301 Moved Permanently

# Test HTTPS response
curl -Isk --max-time 10 https://wishlist.millernest.com | head -5
#  HTTP/2 200
```

**What each check proves:**
- openssl s_client ... Verify return code: 0  cert chain is valid and trusted by the system CA store
- 301 on HTTP  force-ssl redirect is working
- HTTP/2 200 on HTTPS  full HTTPS stack serving the app correctly, with HTTP/2 enabled

---

## Key Lessons

### 1. NPM Does Not Auto-Regenerate Configs
When you modify NPM's SQLite database directly, the .conf files in /data/nginx/proxy_host/ are **not** automatically updated. You must either use the NPM web UI/API or manually write the conf file and reload nginx.

### 2. Certbot Webroot Requires the Challenge Location to Be Served
If nginx is proxying all requests to a backend service (like a k3s pod), the ACME challenge tokens never reach certbot's webroot. You must add the letsencrypt-acme-challenge.conf include **before** the location / proxy block so nginx serves those specific paths directly.

### 3. Match the Meta JSON Exactly
NPM's cert and proxy_host meta fields must contain valid JSON with specific keys (letsencrypt_agree: true, letsencrypt_email, 
ginx_online: true, 
ginx_err: null). Malformed JSON or letsencrypt_agree: false causes NPM to treat the proxy host as if no cert is assigned.

### 4. NPM's Cert Numbering Scheme
NPM names certbot certs 
pm-1, 
pm-2, etc. When manually issuing a cert, use the next available number (check ls /etc/letsencrypt/live/) and use the same number as the cert's id in the database. This keeps things consistent if you later use the NPM UI.

### 5. Template From a Working Config
When manually writing an nginx SSL config for NPM, copy from an existing working proxy host config rather than writing from scratch. This ensures you get all the correct includes (orce-ssl.conf, ssl-cache.conf, ssl-ciphers.conf) and the correct $forward_scheme variable pattern.

---

## Relevant File Paths

| Path | Description |
|---|---|
| /mnt/user/appdata/NginxProxyManager/database.sqlite | NPM SQLite database (on Unraid host) |
| /data/nginx/proxy_host/<n>.conf | Per-proxy-host nginx config (inside container) |
| /etc/letsencrypt/live/npm-<n>/ | Cert files: ullchain.pem, privkey.pem, cert.pem, chain.pem |
| /data/letsencrypt-acme-challenge/ | Webroot for ACME HTTP-01 challenge |
| /etc/nginx/conf.d/include/letsencrypt-acme-challenge.conf | NPM's built-in ACME challenge nginx include |
| /etc/nginx/conf.d/include/force-ssl.conf | NPM's HTTPHTTPS 301 redirect include |

---

## Follow-Up Incident: "Your connection isn't private" on auctions.millernest.com

**Date:** 2026-03-14
**Symptom:** Chrome and Edge showed "Your connection isn't private" (ERR_CERT_AUTHORITY_INVALID) on `https://auctions.millernest.com`. The cert was known-good: `openssl s_client` from Unraid returned `Verify return code: 0 (ok)`, and the cert appeared valid via the NPM UI.

### Root Cause: Pi-hole DNS Routing App Domains to k3s Directly

The SSL architecture requires:
```
Browser  Pi-hole DNS  192.168.1.194 (NPM)  TLS termination  HTTP proxy  192.168.1.206 (k3s)
```

Pi-hole's custom DNS (`/mnt/user/appdata/official-pihole/pihole/pihole.toml`) had both app domains pointing to **`192.168.1.206`** (k3s) instead of **`192.168.1.194`** (NPM):

```toml
# WRONG  bypasses NPM entirely
hosts = [
  "192.168.1.206 auctions.millernest.com",
  "192.168.1.206 wishlist.millernest.com",
  ...
]
```

Browsers on the LAN resolved both domains straight to the k3s Traefik ingress, which serves HTTP only (no TLS). Port 443 on k3s had nothing listening  so the browser received a connection error or a self-signed cert, not the valid Let's Encrypt cert from NPM. `openssl s_client` from Unraid worked because it connected to the **external IP** (`99.129.41.20`), which routes through the router's port-forward  NPM  valid cert.

### Investigation Steps

```powershell
# 1. Confirm cert is valid from Unraid (connects via external IP, bypasses Pi-hole)
ssh root@192.168.1.194 "echo | openssl s_client -connect auctions.millernest.com:443 -servername auctions.millernest.com 2>&1 | grep Verify"
#  Verify return code: 0 (ok)   cert itself is fine

# 2. Confirm external IP via public DNS
ssh root@192.168.1.194 "nslookup auctions.millernest.com 8.8.8.8"
#  99.129.41.20   the public/external IP

# 3. Confirm cert is valid when hitting external IP directly
ssh root@192.168.1.194 "echo | openssl s_client -connect 99.129.41.20:443 -servername auctions.millernest.com 2>&1 | grep Verify"
#  Verify return code: 0 (ok)   valid via external path

# 4. Read Pi-hole's custom DNS config from Unraid host
ssh root@192.168.1.194 "sed -n '125,145p' /mnt/user/appdata/official-pihole/pihole/pihole.toml"
# KEY FINDING: "192.168.1.206 auctions.millernest.com"  should be 192.168.1.194
```

**Why openssl worked from Unraid but browsers failed:** Unraid does not use Pi-hole for DNS resolution. LAN clients (browsers) use Pi-hole as their DNS server, so only Pi-hole-using clients hit the wrong IP.

### The Fix

Edit `pihole.toml` on the Unraid **host** filesystem directly. Pi-hole v6 stores custom DNS overrides in the `hosts` array inside `pihole.toml`. Do not edit inside the container  `python3` is not available there and edits won't survive restarts.

```bash
# Run on Unraid via SSH  fix both app domain entries
ssh root@192.168.1.194 "awk '/192.168.1.206 auctions.millernest.com/{gsub(\"192.168.1.206\",\"192.168.1.194\")} /192.168.1.206 wishlist.millernest.com/{gsub(\"192.168.1.206\",\"192.168.1.194\")} {print}' /mnt/user/appdata/official-pihole/pihole/pihole.toml > /tmp/pihole_fixed.toml && mv /tmp/pihole_fixed.toml /mnt/user/appdata/official-pihole/pihole/pihole.toml"

# Verify the fix
ssh root@192.168.1.194 "grep -E 'auctions|wishlist' /mnt/user/appdata/official-pihole/pihole/pihole.toml"
#  "192.168.1.194 auctions.millernest.com"
#  "192.168.1.194 wishlist.millernest.com"

# Restart Pi-hole to pick up the change
ssh root@192.168.1.194 "docker restart binhex-official-pihole"
```

After the restart, flush DNS on Windows clients (`ipconfig /flushdns`) and browsers resolve both domains to NPM, which terminates TLS correctly.

---

### Key Lesson 6: Pi-hole Custom DNS Must Point App Domains to NPM, Not k3s

The correct internal DNS architecture for this setup:

| Domain | Pi-hole custom DNS target | Why |
|---|---|---|
| `*.millernest.com` apps using NPM SSL | `192.168.1.194` (NPM) | NPM terminates TLS; k3s has no cert |
| `api.auctions.millernest.com` (HTTP-only proxy) | `192.168.1.206` (k3s) | NPM proxy host is HTTP-only, so k3s direct is fine |

**Rule:** Any domain whose NPM proxy host has SSL enabled (`ssl_forced=1`) must resolve to `192.168.1.194`. Pointing it to `192.168.1.206` bypasses SSL termination entirely  the browser hits k3s directly on port 443, finds nothing, and reports a cert error.

**Pi-hole v6 note:** Custom DNS in Pi-hole v6 lives in `pihole.toml` under the `hosts = [...]` array, **not** in `/etc/pihole/custom.list` (which was the Pi-hole v5 location). Edit the toml on the Unraid host filesystem at `/mnt/user/appdata/official-pihole/pihole/pihole.toml`.

---

## Follow-Up Incident: "Your connection isn't private" on auctions.millernest.com

**Date:** 2026-03-14
**Symptom:** Chrome and Edge showed "Your connection isn't private" (ERR_CERT_AUTHORITY_INVALID) on `https://auctions.millernest.com`. The cert was known-good: `openssl s_client` from Unraid returned `Verify return code: 0 (ok)`, and the cert appeared valid via the NPM UI.

### Root Cause: Pi-hole DNS Routing App Domains to k3s Directly

The SSL architecture requires:
```
Browser  Pi-hole DNS  192.168.1.194 (NPM)  TLS termination  HTTP proxy  192.168.1.206 (k3s)
```

Pi-hole's custom DNS (`/mnt/user/appdata/official-pihole/pihole/pihole.toml`) had both app domains pointing to **`192.168.1.206`** (k3s) instead of **`192.168.1.194`** (NPM):

```toml
# WRONG  bypasses NPM entirely
hosts = [
  "192.168.1.206 auctions.millernest.com",
  "192.168.1.206 wishlist.millernest.com",
  ...
]
```

Browsers on the LAN resolved both domains straight to the k3s Traefik ingress, which serves HTTP only (no TLS). Port 443 on k3s had nothing listening  so the browser received a connection error or a self-signed cert, not the valid Let's Encrypt cert from NPM. `openssl s_client` from Unraid worked because it connected to the **external IP** (`99.129.41.20`), which routes through the router's port-forward  NPM  valid cert.

### Investigation Steps

```powershell
# 1. Confirm cert is valid from Unraid (connects via external IP, bypasses Pi-hole)
ssh root@192.168.1.194 "echo | openssl s_client -connect auctions.millernest.com:443 -servername auctions.millernest.com 2>&1 | grep Verify"
#  Verify return code: 0 (ok)   cert itself is fine

# 2. Confirm external IP via public DNS
ssh root@192.168.1.194 "nslookup auctions.millernest.com 8.8.8.8"
#  99.129.41.20   the public/external IP

# 3. Confirm cert is valid when hitting external IP directly
ssh root@192.168.1.194 "echo | openssl s_client -connect 99.129.41.20:443 -servername auctions.millernest.com 2>&1 | grep Verify"
#  Verify return code: 0 (ok)   valid via external path

# 4. Read Pi-hole's custom DNS config from Unraid host
ssh root@192.168.1.194 "sed -n '125,145p' /mnt/user/appdata/official-pihole/pihole/pihole.toml"
# KEY FINDING: "192.168.1.206 auctions.millernest.com"  should be 192.168.1.194
```

**Why openssl worked from Unraid but browsers failed:** Unraid does not use Pi-hole for DNS resolution. LAN clients (browsers) use Pi-hole as their DNS server, so only Pi-hole-using clients hit the wrong IP.

### The Fix

Edit `pihole.toml` on the Unraid **host** filesystem directly. Pi-hole v6 stores custom DNS overrides in the `hosts` array inside `pihole.toml`. Do not edit inside the container  `python3` is not available there and edits won't survive restarts.

```bash
# Run on Unraid via SSH  fix both app domain entries
ssh root@192.168.1.194 "awk '/192.168.1.206 auctions.millernest.com/{gsub(\"192.168.1.206\",\"192.168.1.194\")} /192.168.1.206 wishlist.millernest.com/{gsub(\"192.168.1.206\",\"192.168.1.194\")} {print}' /mnt/user/appdata/official-pihole/pihole/pihole.toml > /tmp/pihole_fixed.toml && mv /tmp/pihole_fixed.toml /mnt/user/appdata/official-pihole/pihole/pihole.toml"

# Verify the fix
ssh root@192.168.1.194 "grep -E 'auctions|wishlist' /mnt/user/appdata/official-pihole/pihole/pihole.toml"
#  "192.168.1.194 auctions.millernest.com"
#  "192.168.1.194 wishlist.millernest.com"

# Restart Pi-hole to pick up the change
ssh root@192.168.1.194 "docker restart binhex-official-pihole"
```

After the restart, flush DNS on Windows clients (`ipconfig /flushdns`) and browsers resolve both domains to NPM, which terminates TLS correctly.

---

### Key Lesson 6: Pi-hole Custom DNS Must Point App Domains to NPM, Not k3s

The correct internal DNS architecture for this setup:

| Domain | Pi-hole custom DNS target | Why |
|---|---|---|
| `*.millernest.com` apps using NPM SSL | `192.168.1.194` (NPM) | NPM terminates TLS; k3s has no cert |
| `api.auctions.millernest.com` (HTTP-only proxy) | `192.168.1.206` (k3s) | NPM proxy host is HTTP-only, so k3s direct is fine |

**Rule:** Any domain whose NPM proxy host has SSL enabled (`ssl_forced=1`) must resolve to `192.168.1.194`. Pointing it to `192.168.1.206` bypasses SSL termination entirely  the browser hits k3s directly on port 443, finds nothing, and reports a cert error.

**Pi-hole v6 note:** Custom DNS in Pi-hole v6 lives in `pihole.toml` under the `hosts = [...]` array, **not** in `/etc/pihole/custom.list` (which was the Pi-hole v5 location). Edit the toml on the Unraid host filesystem at `/mnt/user/appdata/official-pihole/pihole/pihole.toml`.
