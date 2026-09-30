# 01: Shared Emulator Baseline (labs-infra)

Status: IN-PROGRESS (2026-09-28, labs-infra feature/android-emulator pushed; awaiting CI + merge)
Owner repo: `labs-infra` (branch `feature/android-emulator-baseline`)
Depends on: none
Skills: `k3s-kubectl-commands`, `delivery-planning`

## Goal

A working, reusable Android emulator manifest in `labs-infra/android-emulator/` that boots in the `ci` namespace and exposes a healthy, authorized ADB endpoint on a ClusterIP Service. This is the building block that leases (task 02) and enrollment (task 04) instantiate.

## Context

- The existing `dev/amminox-android-emulator` proves the QEMU approach boots (~60s after SDK setup) on node `k3-lab-01` with `/dev/kvm`, but:
  - ADB binds loopback only (`-ports 5554,5555`), so the Service gets `Connection refused`.
  - The emulator's own post-boot adb calls fail (`Unable to connect to adb daemon on port: 5037`, `device offline`).
  - Data is `emptyDir`, and it installs the system image on every start (slow).
- `qemu.adb.secure=1`: remote adb clients must present an authorized key.
- The Redroid examples in `lease.example.yaml` / `profile-enrollment.example.yaml` will not run (no binder/ashmem in the host kernel).

## Steps

1. **Emulator image**: add `android-emulator/image/Dockerfile` FROM `ghcr.io/cirruslabs/android-sdk:34` that pre-installs `platform-tools`, `emulator`, and `system-images;android-34;google_apis_playstore;x86_64`, and pre-creates AVD `test` (Pixel profile, `hw.ramSize=4096`, `disk.dataPartition.size=6G`, swiftshader GPU). Baking the image removes per-boot `sdkmanager` downloads. Publish via labs-infra CI (new job, path-filtered to `android-emulator/image/**`), tag `$(date +%Y%m%d%H%M).${GITHUB_RUN_NUMBER}`.
2. **ADB auth**: generate one adb keypair for the lab, stored as Secret `ci/android-adb-key` (keys `adbkey`, `adbkey.pub`) created with `kubectl create secret generic ... --dry-run=client -o yaml | kubectl apply -f -`. Mount it into the emulator at `/root/.android/adbkey*` so the emulator trusts it, and into consumers (runner job) at `~/.android/`. Never commit the key.
3. **Template manifest**: `android-emulator/emulator.template.yaml` (Deployment + Service + PVC), parameterized by lease/profile name via labels:
   - Container `emulator`: privileged, `/dev/kvm` + `/dev/net/tun` hostPath, `-no-window -no-audio -no-boot-anim -gpu swiftshader_indirect -ports 5554,5555 -no-snapshot-save`, AVD data dir on the PVC (`/root/.android/avd/test.avd` userdata files).
   - Sidecar `adb-bridge`: `alpine/socat` running `TCP-LISTEN:5556,fork,reuseaddr TCP:127.0.0.1:5555` (shared pod network namespace).
   - Probes: startup/readiness exec `adb -s emulator-5554 shell getprop sys.boot_completed | grep -q 1` (inside the emulator container), liveness TCP 5556 on the sidecar.
   - Resources: emulator requests `1`/`3Gi`, limits `2`/`5Gi`; sidecar `10m`/`16Mi`, `100m`/`64Mi`.
   - Service: ClusterIP, port `5555` -> targetPort `5556`.
4. **Fix post-boot adb**: start `adb start-server` before launching the emulator, or drop the emulator's own post-boot adb dependencies. Confirm no `device offline` in the logs.
5. **Rewrite the examples**: replace Redroid in `lease.example.yaml` and `profile-enrollment.example.yaml` with the template; remove the "Requires the CSI snapshot controller" comment (the README chose copy-from-baseline, not snapshots).
6. **Verification (in-cluster only)**: apply one instance named `android-smoke` in `ci`, then run a probe pod (`restartPolicy: Never`, script in a YAML block scalar) that mounts `ci/android-adb-key`, runs `adb connect android-smoke.ci.svc.cluster.local:5555`, and prints `sys.boot_completed`, `ro.build.version.release`, `wm size`, a Settings launch, and a `uiautomator dump` excerpt. Read results via `kubectl logs`. Delete both afterwards.
7. Update `labs-infra/android-emulator/README.md`: QEMU decision, ADB key handling, template usage, resource footprint.

## Acceptance criteria

- `adb devices` from an in-cluster pod shows the emulator as `device` (not `unauthorized`/`offline`).
- `sys.boot_completed=1` within 5 minutes of pod start, with no per-boot SDK downloads.
- Google Play is present (`pm list packages | grep com.android.vending`).
- No NodePort/Ingress exists for any emulator. Everything is in `ci`.
- Manifests are idempotent (`kubectl apply` twice = no changes) and shipped via PR + CI.

## Evidence to report

PR link, CI run link, probe pod log excerpt (no secrets), `kubectl -n ci get deploy,svc,pvc -l app.kubernetes.io/name=android-emulator`, and confirmation that the smoke resources were deleted.

## Do not

- Do not expose ADB via NodePort, ingress, or `hostNetwork`.
- Do not use Redroid.
- Do not touch `dev/amminox-android-emulator` (task 05 retires it).
- Do not attempt `kubectl exec`/`port-forward` or LAN connections from the corporate laptop.

## Log