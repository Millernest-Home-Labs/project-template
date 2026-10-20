# CI/CD: Self-Hosted Registry & WireGuard Integration Learnings

**Date:** 2026-02-27  
**Branch:** `copilot/fix-e2e-test-validations`  
**Context:** Getting a GitHub Actions pipeline to build, push a Docker image, run integration tests against a LAN MySQL instance, and deploy to a k3s cluster  all from GitHub-hosted runners.

---

## Problem 1: Docker Push Failing with `Client Closed Request`

### Symptom
`docker push` to `packages.millernest.com` failed after exactly 60 seconds with:
```
unknown: Client Closed Request
##[error]Process completed with exit code 1.
```
Affected layers retried in a countdown (`Retrying in 5 seconds... 4... 3...`) then re-attempted, cycling for the full 60s before giving up.

### What Did NOT Work

| Attempt | Reason It Failed |
|---------|-----------------|
| Add `proxy_read_timeout 900s` to NGINX custom config | NGINX was not the bottleneck  the 60s limit was in **Traefik**, the k3s ingress controller behind NGINX |
| Add `client_body_timeout 900s` to NGINX | Same  Traefik's `readTimeout` is independent of NGINX |
| Move push step before VPN connect | Ruled out WireGuard interference; push still failed identically before any tunnel was active |

### Root Cause
`packages.millernest.com` routes through **NGINX Proxy Manager  Traefik (k3s ingress)**. Traefik's default `respondingTimeouts.readTimeout` is **60 seconds**. Large .NET Docker layers (100200 MB) take longer than 60s to upload from Azure-hosted GitHub runners over a residential internet connection. Traefik closes the connection mid-upload.

### What Worked
**Switch to `ghcr.io` (GitHub Container Registry).**

- `ghcr.io` is GitHub's own CDN  no NGINX, no Traefik, no residential uplink in the upload path.
- Auth via `GITHUB_TOKEN` with `permissions: packages: write`  no registry secrets needed.
- Push time: **12 seconds** for the same image that previously timed out at 60s.

```yaml
jobs:
  ci-cd:
    permissions:
      contents: read
      packages: write   # Required for ghcr.io push via GITHUB_TOKEN

    steps:
      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Push Docker image
        run: docker push "ghcr.io/<owner-lowercase>/reflexia-server:${TAG}"
```

**Note:** ghcr.io requires the owner name to be **lowercase**:
```bash
OWNER=$(echo "${{ github.repository_owner }}" | tr '[:upper:]' '[:lower:]')
```

---

## Problem 2: k3s Cannot Pull Image from `ghcr.io`

### Symptom
After switching to ghcr.io, the pod stayed in `Pending` / `ErrImagePull` because the k3s node had no credentials to pull from the private ghcr.io package.

### What Worked
Create an `imagePullSecret` in k3s each run using the same `GITHUB_TOKEN`. Using `--dry-run=client | kubectl apply` makes it idempotent (creates or updates on every run):

```yaml
- name: Create GHCR imagePullSecret in k3s
  run: |
    kubectl create secret docker-registry ghcr-pull-secret \
      --docker-server=ghcr.io \
      --docker-username=${{ github.actor }} \
      --docker-password=${{ secrets.GITHUB_TOKEN }} \
      -n "${{ env.K8S_NAMESPACE }}" \
      --dry-run=client -o yaml | kubectl apply -f -
```

Add `imagePullSecrets` to the deployment manifest:
```yaml
spec:
  template:
    spec:
      imagePullSecrets:
        - name: ghcr-pull-secret
      containers:
        - name: reflexia-server
          image: ghcr.io/ethanimproving/reflexia-server:${TAG}
```

---

## Problem 3: `kubectl` Cannot Reach the k3s API

### Symptom
```
error: error validating "STDIN": failed to download openapi:
Get "https://rancher.millernest.com/k8s/clusters/local/openapi/v2": 
dial tcp 99.129.41.20:443: connect: connection refused
```

### Root Cause
`KUBECONFIG_DATA` was generated from Rancher and points to `https://rancher.millernest.com` (external IP `99.129.41.20:443`). GitHub Actions runners cannot reach this address  it requires NAT hairpin from inside the LAN, which the router does not support.

### What Worked
Patch the KUBECONFIG server URL at runtime **after** VPN connects, replacing the external Rancher URL with the internal k3s API endpoint (`192.168.1.206:6443`), which is reachable via WireGuard:

```yaml
- name: Configure kube context
  shell: bash
  run: |
    mkdir -p "$HOME/.kube"
    echo "${KUBECONFIG_DATA}" > "$HOME/.kube/config"
    # Rewrite cluster server to internal k3s API (reachable via WireGuard).
    sed -i 's|server: https://.*|server: https://192.168.1.206:6443|g' "$HOME/.kube/config"
    # Replace CA cert with insecure flag (k3s uses a self-signed cert).
    sed -i 's|certificate-authority-data:.*|insecure-skip-tls-verify: true|g' "$HOME/.kube/config"
    kubectl config current-context || true
```

**Key:** This step must run **after** `wg-quick up wg0`  the VPN must be connected first so `192.168.1.206` is reachable.

---

## Problem 4: WireGuard Connects but MySQL Is Unreachable

### Symptom
`wg show` confirmed the interface came up with `Tunnel IP: 10.253.0.6/32`, but the MySQL wait loop exhausted all attempts and failed. The `wg show` output had no `latest handshake` line  the peer handshake had not yet completed.

### Root Cause
The WireGuard interface (`wg0`) comes up immediately, but the **handshake with the server peer** (Unraid at `192.168.1.194:51820`) happens asynchronously. The MySQL probe loop was firing before the tunnel was actually routing packets.

### What Worked
Extend the wait loop from `20  3s` (60s) to `30  3s` (90s), giving the WireGuard handshake time to complete before the first probe:

```yaml
- name: Verify MySQL is reachable via VPN
  run: |
    for i in $(seq 1 30); do
      if mysqladmin ping -h 192.168.1.206 -P 30306 -u root -proot --silent 2>/dev/null; then
        echo "MySQL is ready"
        exit 0
      fi
      echo "Attempt $i/30: not ready yet, waiting 3s..."
      sleep 3
    done
    echo "ERROR: MySQL not reachable via VPN" && exit 1
```

---

## Problem 5: WireGuard `AllowedIPs` Must Not Be `0.0.0.0/0`

### Symptom
Using `AllowedIPs = 0.0.0.0/0` (default route) in the runner's `wg0.conf` caused all runner traffic  including calls to `ghcr.io`, the GitHub API, and `apt`  to route through the tunnel. This broke every step that needed public internet access.

### What Worked
Restrict `AllowedIPs` to **only the LAN subnets that need to be reached via VPN**:

```ini
[Peer]
PublicKey = <server-public-key>
AllowedIPs = 192.168.1.0/24, 10.253.0.0/24
```

This routes only LAN traffic (MySQL at `192.168.1.206`, k3s API at `192.168.1.206`) through the tunnel, while all other traffic (GitHub, ghcr.io, apt) continues over the runner's default internet route.

---

## Problem 6: Rollout Timeout Too Short

### Symptom
```
error: timed out waiting for the condition
Waiting for deployment "reflexia-server" rollout to finish: 1 old replicas are pending termination...
```

### Root Cause
The 180s timeout did not account for the full pod lifecycle:

| Phase | Duration |
|-------|----------|
| Old pod `preStop` hook (sleep) | 30s |
| Old pod `terminationGracePeriodSeconds` | 90s |
| New pod: pull image from ghcr.io (~200MB) | ~60s |
| New pod: `initialDelaySeconds` on readiness probe | 60s |
| **Worst case total** | **~240s** |

### What Worked
Increase rollout timeout to 600s:
```yaml
- name: Wait for rollout
  run: kubectl rollout status -n "${{ env.K8S_NAMESPACE }}" deployment/reflexia-server --timeout=600s
```

---

## Summary: The Working Pipeline Order

```
Build & Unit Tests
    
Set version / image name (ghcr.io/<owner-lowercase>/...:tag)
    
Build Docker image
    
docker/login-action  ghcr.io
    
docker push (12s, no proxy chain)
    
wg-quick up wg0  (AllowedIPs = LAN only)
    
Wait for MySQL at 192.168.1.206:30306 (up to 90s)
    
Integration Tests (real MySQL, real k3s cluster)
    
Install kubectl
    
Write KUBECONFIG, patch server URL  192.168.1.206:6443
    
kubectl create secret docker-registry ghcr-pull-secret (idempotent)
    
kubectl apply ConfigMap / Service / Deployment / Ingress
    
kubectl rollout status --timeout=600s
    
wg-quick down wg0 (always)
```
