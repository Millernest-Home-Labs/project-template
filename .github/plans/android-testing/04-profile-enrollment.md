# 04: Profile Enrollment (clean, walmart-authenticated)

Status: IN-PROGRESS (2026-09-28, tooling done; operator enrollment pending on a lab machine)
Owner repo: `labs-infra` (branch `feature/android-profiles`)
Depends on: 01, 02
Skills: `k3s-kubectl-commands`

## Goal

Read-only baseline PVCs that leases copy from, so tests start from a known device state and authenticated retailer sessions persist across runs without sharing mutable state.

## Profiles

| Profile | Contents | Enrollment |
|---|---|---|
| `clean` | Factory AVD, Play Store signed out | None needed; the lease uses template defaults (no baseline copy) |
| `walmart-authenticated` | Walmart app installed from Play, signed in to the **dedicated QA account** (`dev/walmart-test-account`; copy to `ci` as `ci/walmart-test-account`) | Operator, interactive |
| `kroger-authenticated` | Same pattern | Blocked until the user provides a dedicated Kroger QA account |

## Steps

1. Manifest `android-emulator/profiles/enrollment.yaml`: the task 01 template in "enrollment" mode (writes directly to `android-profile-<name>-baseline` PVC, 8Gi `local-path`), `replicas: 0` by default.
2. Enrollment runbook in `android-emulator/README.md`:
   - Operator scales enrollment to 1 **from a lab or personal machine** (not the corporate laptop), port-forwards ADB, uses `scrcpy` or `adb` to sign in to Play and the retailer app with the QA account, completes MFA themselves, then cleanly shuts down the emulator (`adb emu kill`) so userdata is consistent, and scales to 0.
   - Label the PVC `android.millernest.com/enrolled-at=<date>`.
3. Lease init copy (task 02) mounts the baseline read-only. Verify a lease boots signed in and that changes made during a lease do not appear in the baseline.

## Acceptance criteria

- A lease from `walmart-authenticated` shows the Walmart app signed in (screenshot artifact via the task 02 smoke workflow, parameterized by profile).
- The baseline PVC checksum or mtime is unchanged after a lease run.
- No credentials appear in manifests, logs, artifacts, or plan files.

## Risks

- Retailer apps may detect emulators or fail Play Integrity. If sign-in is blocked, record it in `.github/learnings/` and treat retailer-app steps as real-device-verified.
- Sessions expire. Document re-enrollment cadence once observed.

## Do not

- Never use personal accounts. Dedicated QA accounts only.
- Never automate credential entry into profiles from CI. Enrollment is operator-driven.

## Log