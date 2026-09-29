---
description: 'Troubleshooting guide for NGINX Proxy Manager, DNS, and network routing issues'
---

# NGINX Proxy Manager & Network Troubleshooting

Procedures for diagnosing and resolving NGINX reverse proxy, DNS resolution, and network routing issues in the home lab infrastructure.

## Quick Diagnostic Checklist

1. Check **IP address** of Unraid Server (should be `192.168.1.194`).
2. Check **A Records** on [Namecheap](https://ap.www.namecheap.com/Domains/DomainControlPanel/millernest.com/advancedns) (should be host=`paperless`, value=[99.129.41.20](http://whatismyip.com/)).
3. Check [NGINX](http://192.168.1.194:7818/login) reverse proxy (should be public Let's Encrypt `https://paperless.millernest.com/` = http://192.168.1.194:8000).
4. Check [AT&T default Gateway](http://192.168.1.254) Port Forwarding on port 80 and 443. (*Firewall > NAT/Gaming*, password `?98#0>&@24`).
5. Verify NGINX host ports are 443 and 80.

## DNS Verification

Split-brain DNS configuration:
- **Internal (Pi-hole 192.168.1.10):** Resolves `*.millernest.com` to internal IPs (e.g., 192.168.1.206 for k3s)
- **External (Public DNS):** Resolves `*.millernest.com` to public IP (99.129.41.20)

Test DNS resolution:

```powershell
# Check resolution using Pi-hole
nslookup paperless.millernest.com

# Should return: 192.168.1.194 or internal IP

# Check resolution using public DNS
nslookup paperless.millernest.com 8.8.8.8

# Should return: 99.129.41.20 (external IP)
```

## WireGuard Interference (Common Issue)

WireGuard's high-priority default route (metric 0 via wg0) and tunnel IPs (10.253.0.x) can run on startup and block or conflict with br0's DHCP broadcasts to 192.168.1.255 before the AT&T reservation at .194 can respond.

### Fix WireGuard Routing Issues

From Unraid console or SSH:

```bash
# Disable WireGuard tunnel
wg-quick down wg0

# Force DHCP renew on br0
ifdown br0
ifup br0

# Check if it pulls 192.168.1.194
ip addr show br0
```

If successful, configure WireGuard to avoid conflicts:

**In VPN Manager:**
- Set PostUp/PostDown scripts to lower metric (add `metric 100` to routes)
- **OR** disable Auto Start
- Then reboot

Reference: [pfSense blocks static and DHCP IP requests from Unraid](https://forum.netgate.com/topic/139027/solved-pfsense-blocks-static-and-dhcp-ip-requests-from-unraid-when-bridging-is-enabled)

## NGINX Proxy Manager Port Configuration

NGINX Proxy Manager must listen on standard ports inside the container:
- **Container port 443** (HTTPS) → Host port 443
- **Container port 80** (HTTP) → Host port 80
- **Container port 81** (Admin UI) → Host port 7818

### Verify Port Mappings

```bash
ssh root@192.168.1.194 "docker port NginxProxyManager"
```

Expected output:
```
443/tcp -> 0.0.0.0:443
443/tcp -> [::]:443
80/tcp -> 0.0.0.0:80
80/tcp -> [::]:80
81/tcp -> 0.0.0.0:7818
81/tcp -> [::]:7818
```

### Fix Incorrect Port Mappings

If ports are mapped incorrectly (e.g., 4443→443, 8080→80), recreate the container:

```bash
ssh root@192.168.1.194 "docker stop NginxProxyManager && docker rm NginxProxyManager"
```

Then recreate via Unraid Docker UI with correct port mappings:
- Container Port: `443` → Host Port: `443`
- Container Port: `80` → Host Port: `80`
- Container Port: `81` → Host Port: `7818`

![NGINX Host Ports Configuration](https://i.imgur.com/s1DeBjF.png)

## Network Connectivity Tests

### Test Direct Connection to Services

```powershell
# Test k3s Rancher
Test-NetConnection -ComputerName 192.168.1.206 -Port 443

# Test Unraid NGINX Proxy Manager
Test-NetConnection -ComputerName 192.168.1.194 -Port 443

# Test through proxy
curl -I -k https://rancher.millernest.com
```

### Check Unraid Routing Table

```bash
ssh root@192.168.1.194 "ip route show"
```

Look for:
- Default gateway via 192.168.1.254 (AT&T router)
- Local network 192.168.1.0/24 via br0
- No conflicting WireGuard routes with metric 0

## Common Issues & Solutions

| Symptom | Cause | Solution |
|---------|-------|----------|
| Domain resolves to external IP internally | Windows not using Pi-hole DNS | Check `ipconfig /all`, set DNS to 192.168.1.10 |
| Connection timeout to domain | NGINX listening on wrong ports | Verify container ports 443/80, not 4443/8080 |
| Unraid DHCP fails on boot | WireGuard interfering with br0 | Disable WireGuard auto-start or lower route metric |
| SSL certificate error | Let's Encrypt cert not accessible | Check NGINX cert paths in proxy host config |
| 502 Bad Gateway | Backend service down | Verify target service is running (e.g., k3s pod) |

## NGINX Proxy Manager Access

- **Web UI:** http://192.168.1.194:7818/login
- **Default credentials:** 
  - Email: `admin@example.com`
  - Password: `changeme` (change on first login)

## AT&T Gateway Port Forwarding

Access: http://192.168.1.254
Password: `?98#0>&@24`

Navigate to: **Firewall > NAT/Gaming**

Ensure port forwarding rules exist:
- **Port 443** (HTTPS) → 192.168.1.194:443
- **Port 80** (HTTP) → 192.168.1.194:80

