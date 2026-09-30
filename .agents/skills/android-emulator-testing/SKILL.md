---
name: android-emulator-testing
description: 'Run native Android workflows on the shared labs-infra emulator pool from GitHub Actions, acquire and release disposable leases, read screenshots and logs, and troubleshoot runner/API/Maestro failures. USE WHEN: Android emulator, Maestro, native E2E, shared emulator, emulator lease, adb, Android testing, Walmart connect flow, device screenshot, emulator smoke test.'
---

# Shared Android Emulator Testing

Use the shared emulator pool in `labs-infra/android-emulator/`. Emulators belong to `labs-infra`, not to individual app repositories. Apps build their APKs and own their Maestro flows; CI leases a disposable emulator, runs the flow, uploads evidence, and releases the lease.

## Fast Path: App Native E2E

Run from a workstation with GitHub CLI access. Do not use local ADB or expose an ADB NodePort.

```powershell
gh workflow run native-e2e.yml `
  --repo Millernest-Home-Labs/amminox `
  --ref feature/shared-emulator-native-e2e `
  -f flow=e2e/native/walmart-connect.yaml `
  -f profile=clean

gh run list --repo Millernest-Home-Labs/amminox --workflow native-e2e.yml -L 3
gh run view <run-id> --repo Millernest-Home-Labs/amminox --json status,conclusion,jobs
gh run download <run-id> --repo Millernest-Home-Labs/amminox -D qa-evidence/native/<run-id>
```

The workflow builds an x86_64 **release** APK against `https://amminox.millernest.com`, leases the requested profile, installs the APK, runs Maestro, captures the final screenshot/UI hierarchy/logcat, uploads artifacts, and releases the lease even when a test fails.

The emulator is controlled with **ADB**. For CI tests, ADB runs on the self-hosted Linux runner inside the cluster: the lease action creates a temporary emulator Deployment and ClusterIP Service, installs the cluster ADB key on the runner, waits for boot, and returns the device serial. Workflow steps use that serial with `adb` to install/inspect the app, and Maestro sends UI actions through the same ADB connection. The workstation commands above only dispatch and inspect GitHub Actions; they do not control the device directly.

When adding a client dependency and its lockfile is out of sync, use the one-time workflow input `refresh-lock=true`; download the `refreshed-client-package-lock-<run-id>` artifact and commit the generated `client/package-lock.json`. Leave this input false for normal test runs.

For the shared-pool device-only smoke test:

```powershell
gh workflow run android-emulator.yml `
  --repo Millernest-Home-Labs/labs-infra `
  --ref main `
  -f profile=clean
```

The pool smoke asserts device boot, Google Play installation, Settings launch, and screenshot/UI dump capture. The main-branch smoke passed after setting emulator CPU requests to 100m.

## HTTPS Interactive Debugging

The request/response viewer is `https://emulator.millernest.com` after the control service is deployed and its OAuth Secret exists. It is restricted to Millernest-Home-Labs GitHub members and does not use WebSockets or expose ADB. Confirm corporate acceptable-use permits access; if the proxy blocks the host, stop rather than tunnel around it.

Start the clean debug lease from GitHub Actions:

```powershell
gh workflow run android-emulator-debug.yml `
  --repo Millernest-Home-Labs/labs-infra `
  --ref main

gh run list --repo Millernest-Home-Labs/labs-infra --workflow android-emulator-debug.yml -L 3
gh run view <run-id> --repo Millernest-Home-Labs/labs-infra --json status,conclusion,jobs
gh run cancel <run-id> --repo Millernest-Home-Labs/labs-infra
```

Open the viewer after the lease step has completed. It polls screenshots once per second and sends taps, swipes, keys, and text as same-origin HTTPS requests. Cancel the workflow when finished; the device lease is limited to 60 minutes and the 90-minute reaper is the backstop. Debug sessions consume the same single emulator slot as native E2E.

To install an app, download the APK from an authorized workflow artifact to the workstation, then use the viewer's APK picker. The control app accepts one APK up to 300 MiB, validates its archive, installs it, and deletes the temporary copy. The amminox native-E2E artifact must include the release APK for this path to be available; that artifact workflow is QA-owned.

For persistent Google Play/Walmart sign-in, run `android-profile-enrollment.yml` with profile `walmart-authenticated`, sign in through the viewer, then run `android-profile-finalize.yml` with the same profile. Future debug runs can select `walmart-authenticated`; the baseline is copied into disposable leases and is never modified by tests.

## Profiles And Credentials

- `clean` is the default: no retailer account, fresh disposable device state.
- `walmart-authenticated` requires operator enrollment from a lab/personal machine with a dedicated QA account and any required MFA.
- Do not put credentials in `gh workflow run -f` inputs, commit them, print them, or include them in logs/artifacts. The throwaway account Secret is `dev/walmart-test-account`; key names are `email`, `password`, `phone`, and `retailer`.
- The existing manual flow `e2e/native/manual/walmart-full-journey.yaml` types retailer credentials and proceeds beyond sign-in toward grocery resolution/cart actions. Do not run it when only sign-in validation is requested. Prefer an authenticated profile and a dedicated sign-in-only flow.

## Interactive Enrollment Or ADB Session

Only from a machine permitted to access the cluster directly, follow `labs-infra/android-emulator/README.md`. ADB is ClusterIP-only and protected by the key in `ci/android-adb-key`. For operator enrollment, the documented service port-forward is:

```bash
kubectl -n ci port-forward deploy/android-profile-walmart-authenticated-enrollment 5556:5556
adb connect 127.0.0.1:5556
scrcpy -s 127.0.0.1:5556
```

Do not create a NodePort, ingress, or host-network endpoint for ADB. Use the enrollment runbook to install the cluster-provided ADB key without displaying its value.

## Constraints And Safety

- Corporate Windows workstations have received WSAEACCES 10013 on LAN ports and McAfee proxy HTML/TLS failures through Rancher. Do not tunnel, change endpoint controls, or repeatedly retry a known blocked path. Use GitHub Actions for the test loop; use another authorized machine for interactive ADB.
- For browser interaction, use the HTTPS control page only if corporate acceptable-use permits it; otherwise remain on CI artifacts. The screen/actions use ordinary HTTPS, not WebSockets or a tunnel.
- The Rancher kubeconfig requires streaming upgrades for `kubectl exec` and `port-forward`; when those fail, do not work around corporate controls. The self-hosted runner performs lease operations in-cluster.
- `ghcr.io/millernest-home-labs/labs-infra-android-emulator` runs a QEMU/KVM API 34 Google Play emulator. ADB inside the pod is loopback-bound and made reachable to authorized in-cluster clients by a socat sidecar. The Kubernetes Service is ClusterIP-only.
- A lease is disposable; its AVD data is deleted at release. A failed job may leave a lease until the 90-minute reaper runs. Check before retrying:

```bash
kubectl -n ci get deploy -l android.millernest.com/role=lease
```

- The self-hosted runner is registered to product repos. Check its online status in GitHub before diagnosing the emulator. The deploy runner uses the separate `infra-deploy` label.
- The `adb-bridge` sidecar forwards the emulator's loopback ADB port to its ClusterIP Service on port 5556. This makes ADB reachable to authorized in-cluster pods; it does **not** expose ADB directly to a workstation. NetworkPolicy permits the runner and explicitly labelled in-cluster clients. An operator can use `kubectl port-forward` from an authorized machine when that machine's Kubernetes connection supports streaming.
- Screenshots are captured by ADB on the runner (`adb -s "$SERIAL" exec-out screencap -p`) and uploaded with the workflow artifacts. Downloading those artifacts is how a workstation can view the emulator screen without connecting to the emulator itself.
- Debug leases use a separate `ci/android-debug-adb-key`; do not use or expose the CI pool key in the viewer.
- Only the GitHub account that started the active debug workflow may see/control that emulator. An authenticated but different org member sees `busy` only.

## Troubleshooting

1. **No runner picks up the job:** check the repo's runner registration status and the `ci/github-runner` pods. A powered-off cluster leaves runner registrations offline even if Actions settings are correct.
2. **Lease remains Pending / `Insufficient cpu`:** the one-node cluster is over its schedulable CPU requests. The emulator lease requests `100m` CPU / `3Gi` memory and limits `2` CPU / `6Gi`. Reduce idle reservations through a PR, not a live-only patch; do not remove limits.
3. **Lease starts but ADB is unauthorized:** confirm `ci/android-adb-key` is mounted into the emulator and runner. The lease action installs the key and waits for `sys.boot_completed=1`.
4. **`api.amminox.millernest.com` returns 404:** use `https://amminox.millernest.com`; that host's `/api` path proxies to `amminox-server`. There is no ingress for the `api.amminox` hostname.
5. **Expo minSdk manifest merge says Health Connect needs API 26:** `react-native-health-connect` requires minSdk 26. `android.minSdkVersion` directly in Expo's `android` object was ignored by prebuild; use `expo-build-properties` with `android.minSdkVersion: 26` in `client/app.json`, and keep `client/package-lock.json` synchronized.
6. **Expo says “Development Build” or waits for Metro:** native E2E must install a standalone release APK (`assembleRelease`) with its JS bundle embedded, not `assembleDebug`.
7. **Maestro says `Config Field Required` at a subflow separator:** every flow document, including `runFlow` subflows, needs `appId`; the amminox app-signin subflow uses `com.millernest.amminox`.
8. **Maestro reports `Unknown error` without failed assertion detail:** inspect the run's JUnit report, `device/final-screen.png`, `device/final-ui.xml`, and `device/logcat.txt`. Check server logs for the test fixture's `/api/auth/signup` and subsequent `/api/auth/login`. No login request plus the login form still visible points to the fixture/subflow handoff; an API signup request confirms the script ran.
9. **Flow passes sign-in but retailer page fails:** check app state and the deployed backend/retailer registry. The `walmart-connect.yaml` flow stops at the live sign-in page and does not submit retailer credentials or add cart items.

## Current Validation Snapshot

As of 2026-09-30, the shared emulator smoke passes; the APK builds, installs, obtains a lease, launches `MainActivity`, and the workflow releases the lease. The first amminox Maestro flow still fails after starting the app and creating its API test user; the final UI is the login form and Maestro reports only `Unknown error`. This is a remaining QA-owned flow issue, not an emulator-control failure. Check the latest workflow run before assuming it is still current.

## Source Of Truth

- Shared pool/lease operations: `labs-infra/android-emulator/README.md` and `labs-infra/android-emulator/lease/lease.sh`.
- Amminox workflow and flow definitions: `amminox/.github/workflows/native-e2e.yml` and `amminox/e2e/native/`.
- Corporate network restrictions: `.github/learnings/2026-09-28-corporate-workstation-network-limits.md`.
- Project plan: `.github/plans/android-testing/00-overview.md`.