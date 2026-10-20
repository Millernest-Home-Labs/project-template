# Android Emulator Pool: Scale-to-Zero Decision

**Date:** 2026-09-30
**Repo:** `labs-infra` (`android-emulator/`)
**Context:** Deciding whether the shared Android emulator pool should keep a warm standing emulator for QA agents, or scale to 0 between uses. Evaluated against real CI timings from the `Android Emulator` smoke run (`labs-infra#36783949577`, 2026-09-30).

---

## Decision

**Scale to 0 when idle. Do not keep a standing emulator.**

The emulator pool stays disposable: leases and enrollment deployments run only while in use, then scale down. No persistent QA device.

## The Numbers (measured, not estimated)

From the smoke run on the single-node cluster (8 CPU / 32Gi, `k3-lab-01`):

| Phase | Duration |
|---|---|
| Lease acquire → pod scheduled and rolled out | ~11s |
| Android boot wait (`sys.boot_completed=1`) | ~71s |
| **Total acquire-to-drivable** | **~82s** |
| Actual test work (verify drivable) | ~26s |

Boot is ~75% of wall time for a short run. A warm device would save ~82s per run.

## Why 82s Is Acceptable

Emulator testing is **not** a standard part of the test suite. It exists for:

- Exploratory tests and flows that cannot be developed against the web version due to restrictions.
- QA validating a fix on a device when the web version cannot exercise the flow.

Both are occasional, human-paced activities. Waiting 82 seconds during total development time is not a big deal. The cost of a standing emulator is not:

- **3-5Gi RAM held permanently** on a shared single node (32Gi total, ~33% used at baseline).
- **A pool slot blocked**: `max-leases=1` means a standing lease would block every CI native-E2E run (they wait 15 minutes, then fail).

## Supporting Facts

- **Requests do not slow boot.** Runtime CPU is governed by limits, not requests. A pod with `request: 100m, limit: 4` bursts to its full 4 CPUs whenever the node has idle capacity. The CI lease booted in the same ~82s with `100m/3Gi` requests as the enrollment emulator did with higher requests.
- **Requests buy coexistence, not speed.** On the single node (8 CPU allocatable, ~4.2 CPU baseline requests), a 4-CPU request per emulator would prevent a second emulator from scheduling. Low requests (`100m`) let a CI lease and an interactive session run simultaneously, each with a 4-CPU limit.
- **Scale-to-zero buys idle cost.** A pod at 0 replicas holds no CPU and no memory. Request size is irrelevant while idle.
- **The reaper only deletes `role=lease` deployments** (90-minute TTL). Enrollment deployments are never reaped; they are scaled by their workflows.

## If Boot Time Ever Matters

The real lever is not a standing pod — it is that the emulator runs with `-no-snapshot`. Baking a boot snapshot into the AVD inside the image would cut the ~71s Android boot to roughly 10-15s while keeping full scale-to-zero semantics. That is an image-build change in `labs-infra`, worth doing only if agents start running many short test cycles against the emulator.

## Related Session Findings (same day)

- Emulator responsiveness over scrcpy was fixed by: raising limits to 4 CPU / 8Gi, overriding the display to 540x1200 (`wm size`, quarter the pixels for swiftshader), capping scrcpy at 15fps / 4 Mbps, and replacing `kubectl port-forward` with a direct SSH tunnel (`ssh -L 5556:<svc-clusterIP>:5555`). Pod CPU dropped from 2003m (throttled at a 2000m limit) to ~1500m under load.
- The enrollment workflow's 60-minute hold (`sleep 3600`) scales the deployment to 0 when it expires — that is the intended cleanup, not a defect.
- The README enrollment instructions reference `ci/android-adb-key`, but enrollment deployments trust `android-debug-adb-key` (stale doc, fix pending).
