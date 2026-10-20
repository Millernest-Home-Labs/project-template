# WireGuard, DNS, and Plex Remote Access Learnings

## Purpose
Capture key operational learnings from troubleshooting WireGuard peer routing, split-brain DNS behavior, and Plex external accessibility.

## Core learnings

1. **WireGuard `AllowedIPs` has different meaning on client and server.**
   - **Client-side `AllowedIPs`** controls what destination traffic is routed into the tunnel.
   - **Server-side `AllowedIPs`** identifies which tunnel source IP(s) belong to that peer and where return traffic should be routed.

2. **A peer IP is set by `Address` in `[Interface]`, not dynamically assigned by WireGuard.**
   - Example: `Address=10.253.0.3/32` means the peer interface uses that IP when tunnel is up.

3. **`Endpoint` is only tunnel ingress, not final application destination.**
   - Traffic is encapsulated to `Endpoint=<public-ip>:51820`, then decrypted and routed internally to final destinations (e.g., `192.168.1.x`, internet, etc.).

4. **Client-side full tunnel (`0.0.0.0/0`) does not change server-side peer identity routes.**
   - Server still keeps per-peer `10.253.0.x/32` routes.

5. **Split-brain DNS was the main cause of intermittent domain behavior.**
   - Router DNS (`192.168.1.254`) resolved `rancher.millernest.com` to public IP `99.129.41.20`.
   - Pi-hole DNS (`192.168.1.10`) resolved it to internal K3s IP `192.168.1.206`.
   - Browser behavior varied depending on which DNS server the client used.

6. **Plex “Not available outside your network” can be transient.**
   - Even with forwarding configured, Plex can temporarily show unavailable until validation/NAT state refreshes.
   - Confirm manual mapping mode and external reachability before making invasive changes.

## Peer Allowed IPs table (captured from server + peer client configs)

| Peer | VPN IP (`Address`) | Client-side `AllowedIPs` | Server-side `AllowedIPs` |
|---|---|---|---|
| Ethan iPhone | `10.253.0.2/32` | `0.0.0.0/0` | `10.253.0.2/32` |
| Ethan Laptop | `10.253.0.3/32` | `0.0.0.0/0` | `10.253.0.3/32` |
| Ethan Desktop | `10.253.0.4/32` | `0.0.0.0/0` | `10.253.0.4/32` |
| Ethan Work Laptop | `10.253.0.5/32` | `0.0.0.0/0` | `10.253.0.5/32` |
| GitHub Runners | `10.253.0.6/32` | `0.0.0.0/0` *(updated from `10.253.0.1/32, 192.168.1.0/24`)* | `10.253.0.6/32` |

## Verification patterns that worked

- `wg show` to validate effective server-side peer routes.
- `ip route show` and `ip route show table 200` to detect tunnel policy/routing side effects.
- `nslookup <domain>` against multiple resolvers to detect split-brain DNS mismatch.
- `Test-NetConnection <host> -Port <port>` for fast transport checks.
- Direct service checks (Plex local endpoint, NGINX proxy health, K3s host reachability) before changing configs.

## Practical guardrails

- Keep internal clients pointed at Pi-hole when relying on internal A records for `*.millernest.com`.
- Treat client and server WireGuard `AllowedIPs` as separate routing contracts.
- Prefer staged validation (DNS → TCP reachability → app endpoint) before changing firewall/NAT rules.
- Avoid exposing secrets/keys in logs or docs; capture only routing and behavior metadata.
