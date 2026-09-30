# 02: Lease v1 (script + composite action)

Status: IN-PROGRESS (2026-09-28, labs-infra feature/android-emulator pushed; awaiting CI + merge)
Owner repo: `labs-infra` (branch `feature/android-lease-v1`)
Depends on: 01
Skills: `k3s-kubectl-commands`, `github-cli-operations`

## Goal

Any product repo's workflow on the self-hosted runner can acquire an exclusive, disposable emulator from a named profile, use it, and release it (always, even on failure) with one reusable action.

## Design

- `android-emulator/lease/lease.sh` with subcommands `acquire <profile> <owner>`, `status <lease>`, `release <lease>`. It uses kubectl in-cluster (runner SA already has `ci-deployer` in `ci`).
- **acquire**:
  1. Generate `lease=android-lease-<short-uuid>`.
  2. Enforce capacity: count Deployments with `android.millernest.com/role=lease`; if `>= MAX_LEASES` (default 1; the node fits one emulator comfortably), wait up to 15 min polling, then fail.
  3. Render the task 01 template with labels `android.millernest.com/lease=<lease>`, `.../profile=<profile>`, and annotation `android.millernest.com/owner=<repo>#<run_id>`.
  4. If the profile is not `clean`, add the `copy-profile` initContainer from PVC `android-profile-<profile>-baseline` (read-only mount). A profile is used by at most one lease at a time: reject if another lease has the same profile label.
  5. Apply, wait for readiness (`kubectl wait --for=condition=available --timeout=600s`), and output `ADB_SERIAL=<lease>.ci.svc.cluster.local:5555`.
- **release**: delete Deployment, Service, PVC by lease label (`--wait=false`), idempotent.
- **Reaper**: CronJob `android-lease-reaper` (every 15 min) deletes leases older than `LEASE_TTL` (default 90 min) based on `creationTimestamp`. It covers cancelled runs that never released.
- `.github/actions/android-lease/action.yml` (composite): inputs `profile`, outputs `adb-serial`, `lease`; a post-step or documented `if: always()` release step. Consumers reference `ethanimproving|millernest-home-labs/labs-infra/.github/actions/android-lease@<ref>` (confirm the org; see overview open questions).

## Steps

1. Implement `lease.sh` (bash, `set -euo pipefail`, shellcheck clean).
2. Implement the composite action and the reaper CronJob (with resource limits).
3. Add a labs-infra workflow `android-lease-smoke.yml` (`workflow_dispatch` + PR on `android-emulator/**`): acquire `clean`, adb connect, assert `sys.boot_completed=1`, screenshot to artifact, release in `if: always()`.
4. Update `android-emulator/README.md`: v1 = script/action; HTTP allocator deferred, with the reason.

## Acceptance criteria

- Smoke workflow is green on the self-hosted runner and uploads a screenshot artifact viewable via `gh run download` from the corporate laptop.
- Two concurrent smoke runs: the second waits, then succeeds after the first releases (or fails cleanly at timeout). Never two leases over capacity.
- A cancelled run's lease is removed by the reaper within TTL + 15 min.
- `kubectl -n ci get deploy -l android.millernest.com/role=lease` is empty after runs.

## Evidence to report

PR + both CI run links, artifact screenshot filename, reaper log line from a forced-orphan test.

## Do not

- No lease may be shared between two owners.
- Do not store the adb key or kube credentials in GitHub secrets. The runner authenticates in-cluster and mounts `ci/android-adb-key`.

## Log