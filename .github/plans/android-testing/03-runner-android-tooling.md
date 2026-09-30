# 03: Runner Android Tooling (labs-infra)

Status: IN-PROGRESS (2026-09-28, labs-infra feature/runner-android-tooling pushed; deploys on merge to main)
Owner repo: `labs-infra` (branch `feature/runner-android-tooling`)
Depends on: none (can run in parallel with 01)
Skills: `k3s-kubectl-commands`, `github-cli-operations`

## Goal

The consolidated runner image can build an Expo Android debug APK and drive an emulator with adb + Maestro.

## Context

`runner/runner-image/Dockerfile` has Node 20, .NET 8, Python 3.12, kubectl and Playwright chromium, but no JDK, Android SDK, adb, or Maestro. The runner is a StatefulSet in `ci` rolled by `.github/workflows/ci.yml`.

## Steps

1. Add to the Dockerfile (single layer per tool, cache-friendly):
   - Temurin JDK 17.
   - Android cmdline-tools at `/opt/android-sdk` with `platform-tools`, `platforms;android-34`, `build-tools;34.0.0` (licenses accepted at build). Set `ANDROID_HOME`, `ANDROID_SDK_ROOT`, PATH.
   - Maestro CLI pinned to a version (install script to `/opt/maestro`, add to PATH).
2. Keep the image size in check: no emulator/system images in the runner (the emulator runs in its own pod).
3. Ensure the runner pod mounts `ci/android-adb-key` at `/home/runner/.android/` (update `runner/deployment.yaml`, read-only, mode 0400). Alternatively the lease action copies it at job start; pick one and document it.
4. Merge via PR. `ci.yml` builds, pushes, and rolls the StatefulSet (with automatic rollback).

## Acceptance criteria

- On the rolled runner: `java -version` (17), `adb version`, `maestro --version`, `sdkmanager --list_installed` all succeed (prove via a `workflow_dispatch` job that prints them).
- Existing product CI jobs still pass (no regression to Node/.NET/Python/Playwright).

## Evidence to report

PR link, CI run link for the image roll, tool-version job output.

## Do not

- Do not install anything on the corporate laptop to compensate.
- Do not create per-repo runners (hard rules: one consolidated runner stack).

## Log