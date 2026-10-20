# K3s Prod Environment Setup

A record of every infrastructure step taken to add the `prod` namespace and
deploy target alongside the existing `dev` namespace.

**Date**: March 2, 2026  
**Cluster**: K3s at `192.168.1.206` (reachable via WireGuard VPN)  
**Dev domain**: `reflexia.millernest.com`  
**Prod domain**: `reflexia.millernest.com` (same domain, different namespace)

---

## 1. Create the `prod` Namespace

Run once from any machine with `kubectl` access to the cluster.

```bash
kubectl create namespace prod
```

Verify:

```bash
kubectl get namespaces | grep prod
# prod   Active   <age>
```

> The `dev` namespace already existed. The CI/CD pipeline uses
> `--dry-run=client | kubectl apply` so re-running this command on a namespace
> that already exists is safe (idempotent).

---

## 2. YAML Manifests Created for `prod`

The pipeline applies these files to the `prod` namespace on every master deploy.
They live alongside their `dev` counterparts in the respective `kube-deploy/`
directories.

### `reflexia-server/kube-deploy/config-map-prod.yml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: reflexia-server
  namespace: prod
data:
  ASPNETCORE_ENVIRONMENT: "Production"
  ASPNETCORE_URLS: "http://0.0.0.0:8080"
  ConnectionStrings__DefaultConnection: "Server=192.168.1.206;Port=30306;Database=reflexia_db;User=root;Password=root"
  # Optional: keep the MySQL host for reference
  MYSQL_SERVICE_HOST: "192.168.1.206"
  Cors__AllowedOrigins__0: "https://reflexia.millernest.com"
  Cors__AllowedOrigins__1: "https://reflexia.millernest.com"
```

Key differences from dev:
- `ASPNETCORE_ENVIRONMENT`: `Production` (dev uses `Development`)
- `ConnectionStrings__DefaultConnection`: points to `reflexia_db` (dev uses `reflexia_db_dev`)
- `ASPNETCORE_URLS`: `8080` — matches the container's `containerPort` (the original prod config had `5000`, which was a bug)
- `Cors__AllowedOrigins`: `reflexia.millernest.com` (dev allows `reflexia.millernest.com`)
- `Features__EnableDevSampleData` is absent — prod uses live scraping

### `reflexia-client/kube-deploy/config-map-prod.yml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: reflexia-client
  namespace: prod
data:
  NODE_ENV: "production"
  EXPO_PUBLIC_API_URL: "/api/v1"
```

Key differences from dev:
- `NODE_ENV`: `production`
- No `PORT` override — nginx listens on `8080` per `nginx.conf` regardless of env

### `reflexia-server/kube-deploy/ingress-prod.yml`

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: reflexia-server
  annotations:
    kubernetes.io/ingress.class: traefik
spec:
  rules:
    - host: api.reflexia.millernest.com
      http:
        paths:
          - backend:
              service:
                name: reflexia-server
                port:
                  number: 80
            path: /
            pathType: Prefix
```

### `reflexia-client/kube-deploy/ingress-prod.yml`

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: reflexia-client
  annotations:
    kubernetes.io/ingress.class: traefik
spec:
  rules:
    - host: reflexia.millernest.com
      http:
        paths:
          - backend:
              service:
                name: reflexia-server
                port:
                  number: 80
            path: /api
            pathType: Prefix
          - backend:
              service:
                name: reflexia-client
                port:
                  number: 80
            path: /
            pathType: Prefix
```

---

## 3. What the CI/CD Pipeline Applies Automatically

On every push to `master` the `deploy-prod` job (in both
`.github/workflows/dotnet-k3s-ci.yml` and
`.github/workflows/react-native-web-build.yml`) runs the following against the
`prod` namespace after `build-and-deploy-dev` succeeds:

```bash
# Idempotently create the namespace (safe if it already exists)
kubectl create namespace prod --dry-run=client -o yaml | kubectl apply -f -

# Create / refresh the GHCR image pull secret
kubectl create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=<actor> \
  --docker-password=<GITHUB_TOKEN> \
  -n prod \
  --dry-run=client -o yaml | kubectl apply --validate=false -f -

# Apply config map, service, deployment, ingress
kubectl apply --validate=false -n prod -f kube-deploy/config-map-prod.yml
kubectl apply --validate=false -n prod -f kube-deploy/service.yml
kubectl apply --validate=false -n prod -f kube-deploy/deployment.yml
kubectl set image -n prod deployment/reflexia-server reflexia-server=<image>
kubectl rollout status -n prod deployment/reflexia-server --timeout=600s
kubectl apply --validate=false -n prod -f kube-deploy/ingress-prod.yml
```

---

## 4. DNS

Two DNS records need to point to the cluster's ingress IP (`192.168.1.206`):

| Record | Type | Value |
|--------|------|-------|
| `reflexia.millernest.com` | A | `192.168.1.206` |
| `api.reflexia.millernest.com` | A | `192.168.1.206` |

The `dev` records (`reflexia.millernest.com`, `api.reflexia.millernest.com`)
use the same domains (different namespaces).
