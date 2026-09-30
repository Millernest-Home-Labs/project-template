# 05: amminox Native E2E Migration + Retire Product Emulator

Status: IN-PROGRESS (2026-09-28, amminox feature/shared-emulator-native-e2e pushed; blocked on labs-infra merge + runner registration)
Owner repo: `amminox` (branch `feature/shared-emulator-native-e2e`)
Depends on: 02, 03
Skills: `qa-verification`, `github-cli-operations`, `k3s-kubectl-commands`

## Goal

Carte's Maestro flows run on the self-hosted runner against a leased shared emulator, producing downloadable artifacts. amminox no longer owns any emulator infrastructure.

## Steps

1. **Workflow**: rewrite `.github/workflows/native-e2e.yml`:
   - `runs-on: [self-hosted, linux, x64]` (remove GitHub-hosted `reactivecircus/android-emulator-runner`; hosted runners are billing-blocked).
   - Build a debug APK (`expo prebuild` + Gradle) with `EXPO_PUBLIC_API_URL=https://api.amminox.millernest.com`. Cache Gradle and npm.
   - Acquire a lease via the labs-infra `android-lease` action (profile input, default `clean`). `adb install`, then `maestro test` over `e2e/native/*.yaml`, or a single flow via `workflow_dispatch` input `flow`.
   - Always collect artifacts: Maestro report, screenshots (`takeScreenshot` in flows plus a final `adb exec-out screencap -p`), `uiautomator dump` XML, logcat tail. Upload with `actions/upload-artifact@v4`.
   - Release the lease in `if: always()`.
   - Add a `workflow_dispatch` input `flow` so an agent can run one exploratory flow (e.g. `e2e/native/explore/*.yaml`, gitignored or kept small).
2. **Retire product-owned emulator** (confirm with the user before deleting cluster resources):
   - Delete `deploy/android-emulator.yaml`, `deploy/android-emulator-svc.yaml`, `client/k8s/emulator-deployment.yaml`, `client/k8s/emulator-service.yaml`, `k8s/mvp9/emulator-deploy.yaml`, `k8s/mvp9/emulator-svc.yaml`.
   - Delete cluster objects `dev/amminox-android-emulator` (Deployment) and `dev/amminox-android-emulator-adb` (NodePort 30185).
   - Update `docs/android-emulator.md`, `INFRASTRUCTURE.md`, `README.md`, and `e2e/native/README.md` to point at labs-infra leases and the CI loop.
3. **Proof-of-control**: run `e2e/native/walmart-connect.yaml` via `workflow_dispatch` from the corporate laptop (`gh workflow run` + `gh run watch` + `gh run download`) and inspect the screenshots.

## Agent loop from the corporate laptop (document in e2e/native/README.md)

```powershell
gh workflow run native-e2e.yml -f flow=e2e/native/explore/<name>.yaml -f profile=clean --ref <branch>
gh run watch
gh run download <run-id> -D .\qa-evidence\native\<run-id>
```

## Acceptance criteria

- `native-e2e.yml` is green on the self-hosted runner for `walmart-connect.yaml`; artifacts contain screenshots showing the Retailers screen and the Walmart sign-in page.
- No emulator manifests remain in amminox; `kubectl -n dev get deploy,svc | grep emulator` is empty.
- The lease is released (none left in `ci`) after success, failure, and cancel.

## Do not

- Do not reintroduce NodePorts or product-owned emulators.
- Do not type retailer credentials in CI flows against the `clean` profile. Authenticated flows use the `walmart-authenticated` profile (task 04).

## Log