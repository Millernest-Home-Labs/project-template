# Amminox (Carte) Android Emulator - First Pass Learnings

Date: 2026-09-28
Goal: Confirm an agent can drive the K3s-hosted Android emulator to replicate a user workflow before starting the Carte shopping-integration challenge (`.github/challenges/carte-shopping-integration.md`).
Outcome: **Not yet drivable.** The emulator boots, but ADB is unreachable from outside the pod.

> **Superseded direction (2026-09-28):** emulators belong to `labs-infra/android-emulator/` as shared, leased infrastructure, not to amminox. Fixes below that target the amminox deployment are now implemented in labs-infra instead. Execution plan: `.github/plans/android-testing/00-overview.md`.

> See `2026-09-28-corporate-workstation-network-limits.md` before retrying any connection from the corporate laptop. The 10013 errors below are a deliberate corporate control and must not be bypassed.

## Installed (local Windows workstation)

| Tool | Method | Version / Location |
|---|---|---|
| kubectl | `winget install -e --id Kubernetes.kubectl --source winget --silent --disable-interactivity` | 1.37.1, `%LOCALAPPDATA%\Microsoft\WinGet\Packages\Kubernetes.kubectl...` |
| adb / fastboot | `winget install -e --id Google.PlatformTools --source winget --silent --disable-interactivity` | `%LOCALAPPDATA%\Microsoft\WinGet\Packages\Google.PlatformTools...` |

Not installed yet: Maestro, Java (Maestro prerequisite), scrcpy.

### Install gotchas

- Without `--source winget` and `--disable-interactivity`, winget printed only a package table and exited 1 without installing.
- winget updates the user PATH, but the running shell does not pick it up. Refresh in-session:
  ```powershell
  $env:Path = [Environment]::GetEnvironmentVariable('Path','User') + ';' + [Environment]::GetEnvironmentVariable('Path','Machine')
  ```
  Appending `%LOCALAPPDATA%\Microsoft\WinGet\Links` alone was not enough.

## Configured

- `KUBECONFIG` set per command to `project-template\.github\secrets\kubeconfig.yaml` (never print its contents).
- The kubeconfig server is `https://rancher.millernest.com/k8s/clusters/local` (Rancher proxy, not the K3s API directly).
- Temporarily scaled `dev/amminox-android-emulator` 0 -> 1 for testing, then restored to 0. No manifests or repo files were changed.
- Throwaway `dev/adb-probe` pods were created and deleted.

## Cluster State Observed

| Resource | State |
|---|---|
| `dev/amminox-client` | Running |
| `dev/amminox-metro` | Running, NodePort 8081:30181 |
| `dev/amminox-server` (old RS) | Running, serving traffic |
| `dev/amminox-server` (new RS) | **CrashLoopBackOff** - migration fails with `Duplicate column name 'dislikes'` (MVP14 diet work). Migration must be idempotent. |
| `dev/amminox-android-emulator` | Deployment scaled to **0** by default; Service `amminox-android-emulator-adb` NodePort 5555:30185 |
| Node `k3-lab-01` (192.168.1.206) | ~11% CPU, ~31% memory - capacity for the emulator |

Emulator spec: image `ghcr.io/cirruslabs/android-sdk:34`, API 30 `google_apis;x86_64` AVD, 1.5GB guest RAM, swiftshader GPU, privileged with `/dev/kvm`, `emptyDir` data (state lost on restart), requests 500m/2Gi, limits 2/4Gi. Boot completes in ~60s; rollout (including SDK image install) takes several minutes.

## Generic `android-emulator`: Does Not Exist Yet

- No generic emulator workload exists in any namespace; only `dev/amminox-android-emulator`.
- `labs-infra/android-emulator/` contains only a design (`README.md`, `lease.example.yaml`, `profile-enrollment.example.yaml`): profiles (`clean`, `walmart-authenticated`), exclusive leases, an allocator API (`POST/GET/DELETE /leases`), `ci` namespace, ClusterIP-only ADB.
- The allocator is unbuilt. Per the README, the Amminox emulator stays product-owned until it exists.
- The current Amminox emulator violates the shared contract (NodePort, `dev` namespace, no persistent profile), so authenticated retailer sessions do not survive a restart.

## Blockers Found (Root Causes)

1. **ADB binds loopback only inside the pod.** The emulator uses `-ports 5554,5555`; ADB listens on 127.0.0.1. The Service has nothing to reach: an in-cluster pod connecting to `amminox-android-emulator-adb.dev.svc.cluster.local:5555` got `Connection refused`. Also noted in `amminox/docs/MVP9-BACKLOG.md` (line ~155).
2. **Rancher proxy blocks streaming APIs.** `kubectl exec` and `kubectl port-forward` fail with `unable to upgrade connection: Upgrade request required`, for both WebSocket (default in kubectl 1.37) and SPDY (`KUBECTL_PORT_FORWARD_WEBSOCKETS=false`). Plain REST calls (`get`, `logs`, `scale`, `apply`, `run`) work. Likely cause: the NGINX Proxy Manager host for `rancher.millernest.com` lacks WebSocket/Upgrade support.
3. **Workstation cannot reach LAN NodePorts.** `adb connect 192.168.1.206:30185` returned Windows error 10013 (socket access forbidden); `Test-NetConnection 192.168.1.206 -Port 30185` returned False. This points to a local firewall or endpoint policy.
4. **Emulator-internal ADB is unhealthy after boot.** Logs show `Unable to connect to adb daemon on port: 5037` and `adb: device offline` for the emulator's own post-boot commands.

## Techniques That Worked

- **In-cluster probe pod as a remote shell** when exec and port-forward are blocked: `kubectl apply` a `restartPolicy: Never` pod, `kubectl wait --for=jsonpath='{.status.phase}'=Succeeded`, then `kubectl logs`, then delete.
- **Put scripts in a YAML block scalar (`args: - |`) applied from a file.** PowerShell 5.1 strips embedded double quotes when passing `bash -c "..."` to native exes (`unexpected EOF while looking for matching '"'`).
- In `cirruslabs/android-sdk:34`, adb lives at `/opt/android-sdk-linux/platform-tools/adb`, not `/opt/android-sdk/...`. Resolve it with `command -v adb`.
- `kubectl wait` against Rancher timed out even after the pod finished (watch was cancelled); `kubectl logs` still returned full output. Treat the wait as best-effort.

## Recommended Fixes (Not Yet Applied)

1. Add a `socat` sidecar to the emulator Deployment: `TCP-LISTEN:5556,fork,reuseaddr -> TCP:127.0.0.1:5555`, and target the Service at 5556. Prefer ClusterIP over NodePort, per the labs-infra contract.
2. Enable WebSocket support on the `rancher.millernest.com` NGINX proxy host, or issue a kubeconfig that talks to `https://192.168.1.206:6443` directly. This unblocks `kubectl exec` / `port-forward`, which works around the workstation NodePort block.
3. Fallback with no infra change: run Maestro as an in-cluster Job and collect results through logs and a screenshot volume. Too slow for exploratory loops.
4. Fix the `dislikes` migration so it is idempotent (check the column exists before `ADD COLUMN`).
5. Longer term: build the labs-infra lease allocator with a `walmart-authenticated` / `kroger-authenticated` profile so retailer logins persist between runs.

## App Context Gathered

- The product is branded "Carte" (`app.json` name); the package is still `com.millernest.amminox`, and the repo is still `amminox`.
- Retailer registry (`server/src/retailerRegistry.js`): only Walmart is `active: true`. Kroger, Instacart, and others are listed but inactive.
- Shopping code: `client/app/(tabs)/grocery.tsx` (`handleShop(retailer)` -> `api.shopGroceryList`), `client/app/settings/retailers.tsx`, `client/app/shop/*`, `client/src/components/shop/*`, `client/src/lib/walmartDeepLink.ts`, `server/src/shop*.js`, `server/src/retailers.js`.
- Existing native E2E: Maestro flows in `amminox/e2e/native/` (`walmart-connect.yaml` in CI; `manual/walmart-full-journey.yaml` needs the `dev/walmart-test-account` secret). CI uses an ephemeral GitHub-hosted emulator, which conflicts with the hard rule that GitHub-hosted runners are billing-blocked.

## Next Steps Once Unblocked

1. `adb connect` (via port-forward or sidecar) -> verify `sys.boot_completed=1`.
2. Install Maestro, build or install the debug APK against `https://api.amminox.millernest.com`.
3. Run `maestro test e2e/native/walmart-connect.yaml` as the proof-of-control workflow.
4. Begin the Carte shopping-integration challenge (vendor picker on Shop, zip -> nearest store, auto-selected items with swap, native cart handoff).
