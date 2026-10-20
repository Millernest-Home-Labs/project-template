# k3s: Non-Expiring Service Account for GitHub Actions

**Date:** 2026-03-01
**Context:** Rancher-issued user tokens in `KUBECONFIG_DATA` expire, causing `kubectl` steps to fail with 401/connection errors. This documents the permanent fix: a non-expiring Kubernetes service account token that bypasses Rancher entirely.

---

## Problem

Rancher generates `kubeconfig` files using short-lived user tokens (`kubeconfig-user-*`). Once they expire, every CI run fails at `Configure kube context`:

```
error: error validating "STDIN": failed to download openapi:
Get "https://rancher.millernest.com/k8s/clusters/local/openapi/v2": 401 Unauthorized
```

The previous workaround (patching the server URL with `sed -i` at runtime) also broke when the token itself expired  a URL rewrite cannot fix an auth failure.

---

## Solution: k8s Service Account with Non-Expiring Token

Create a `ServiceAccount` in `kube-system`, bind it to `cluster-admin`, and create a `kubernetes.io/service-account-token` Secret (the older type that does **not** expire). Build a `kubeconfig` from the extracted token and store it as the `KUBECONFIG_DATA` GitHub secret.

### Infrastructure

| Component | Value |
|-----------|-------|
| k3s API (direct) | `https://192.168.1.206:6443` |
| Rancher NodePort proxy | `https://192.168.1.206:31046/k8s/clusters/local` (NOT used) |
| Service account | `github-actions` in `kube-system` |
| ClusterRoleBinding | `github-actions-admin`  `cluster-admin` |
| Token Secret | `github-actions-token` in `kube-system` |

---

## Step-by-Step Commands

### 1. Create the ServiceAccount

```bash
kubectl create serviceaccount github-actions -n kube-system
```

### 2. Bind to cluster-admin

```bash
kubectl create clusterrolebinding github-actions-admin \
  --clusterrole=cluster-admin \
  --serviceaccount=kube-system:github-actions
```

### 3. Create the Non-Expiring Token Secret

`kubernetes.io/service-account-token` Secrets do not expire. The kubelet populates the token automatically.

```yaml
# github-actions-token-secret.yml
apiVersion: v1
kind: Secret
metadata:
  name: github-actions-token
  namespace: kube-system
  annotations:
    kubernetes.io/service-account.name: github-actions
type: kubernetes.io/service-account-token
```

```bash
kubectl apply -f github-actions-token-secret.yml
# Wait a few seconds for the token to be populated, then verify:
kubectl get secret github-actions-token -n kube-system -o jsonpath='{.data.token}' | wc -c
# Should be > 100 chars (base64 encoded JWT)
```

### 4. Extract the Token, CA, and Server

```bash
TOKEN=$(kubectl get secret github-actions-token -n kube-system \
  -o jsonpath='{.data.token}' | base64 -d)

CA=$(kubectl get secret github-actions-token -n kube-system \
  -o jsonpath='{.data.ca\.crt}')

# Use the direct k3s API  NOT the Rancher proxy URL
SERVER="https://192.168.1.206:6443"
```

On **Windows/PowerShell** (if kubectl is local):

```powershell
$TOKEN = kubectl get secret github-actions-token -n kube-system `
  -o jsonpath='{.data.token}' | ForEach-Object { [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($_)) }

$CA = kubectl get secret github-actions-token -n kube-system `
  -o jsonpath='{.data.ca\.crt}'

$SERVER = "https://192.168.1.206:6443"
```

### 5. Build the kubeconfig

```bash
cat > /tmp/github-actions-kubeconfig.yml <<EOF
apiVersion: v1
kind: Config
clusters:
  - name: k3s-local
    cluster:
      server: ${SERVER}
      certificate-authority-data: ${CA}
users:
  - name: github-actions
    user:
      token: ${TOKEN}
contexts:
  - name: github-actions@k3s-local
    context:
      cluster: k3s-local
      user: github-actions
current-context: github-actions@k3s-local
EOF
```

**PowerShell equivalent:**

```powershell
$kubeconfig = @"
apiVersion: v1
kind: Config
clusters:
  - name: k3s-local
    cluster:
      server: $SERVER
      certificate-authority-data: $CA
users:
  - name: github-actions
    user:
      token: $TOKEN
contexts:
  - name: github-actions@k3s-local
    context:
      cluster: k3s-local
      user: github-actions
current-context: github-actions@k3s-local
"@
$env:KUBECONFIG = "$env:TEMP\github-actions-kubeconfig.yml"
$kubeconfig | Out-File -Encoding utf8 -FilePath $env:KUBECONFIG
```

### 6. Test It Locally

```bash
KUBECONFIG=/tmp/github-actions-kubeconfig.yml kubectl get namespaces
# Should list all namespaces (24 in this cluster)
```

### 7. Update the GitHub Secret

```bash
# Linux/macOS
gh secret set KUBECONFIG_DATA --repo <org>/<repo> < /tmp/github-actions-kubeconfig.yml
```

```powershell
# Windows PowerShell
Get-Content $env:KUBECONFIG | gh secret set KUBECONFIG_DATA --repo ethanimproving/reflexia
```

---

## Configure kube context Step (Workflow YAML)

With the service account kubeconfig in `KUBECONFIG_DATA`, the workflow step becomes trivially simple  no `sed`, no URL patching, no token extraction:

```yaml
- name: Configure kube context
  if: env.KUBECONFIG_DATA != ''
  shell: bash
  run: |
    mkdir -p "$HOME/.kube"
    echo "${KUBECONFIG_DATA}" > "$HOME/.kube/config"
    chmod 600 "$HOME/.kube/config"

    # KUBECONFIG_DATA uses a k3s service account token (non-expiring, cluster-admin).
    # The server points directly to k3s:6443  no Rancher proxy involved.
    # Reachable via WireGuard VPN (AllowedIPs must include 192.168.1.0/24).
    SERVER=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
    echo "Server: ${SERVER}"
    kubectl cluster-info 2>&1 | head -3
```

**No** `--server`, `--token`, or `--insecure-skip-tls-verify` flags are needed on any subsequent `kubectl` call.

---

## Why Direct k3s:6443, Not Rancher Proxy

| Route | URL | Problem |
|-------|-----|---------|
| Rancher proxy | `https://192.168.1.206:31046/k8s/clusters/local` | Token-scoped; expires with Rancher session |
| Rancher external | `https://rancher.millernest.com:443` | Unreachable from GitHub runners (NAT hairpin) |
| **k3s direct** | `https://192.168.1.206:6443` |  Reachable via WireGuard; SA tokens never expire |

The k3s API self-signed certificate is issued for the cluster's internal DNS/IPs. The `certificate-authority-data` field in the kubeconfig above uses the cluster CA extracted directly from the secret  TLS verification works without `insecure-skip-tls-verify`.

---

## Reproduced In a New Cluster

If you need to recreate this setup on a fresh cluster, run steps 17 above in order. The only cluster-specific values are:

- `SERVER`  the k3s API IP:port
- `CA`  extracted from the new cluster's secret
- `TOKEN`  extracted from the new cluster's secret
