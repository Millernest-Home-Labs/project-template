---
description: 'Unraid Docker pool 94% full due to ~34GB orphaned overlay2 layers from a storage-driver switch to btrfs; safe to rm -rf without stopping Docker after verifying no open file handles'
---

# Unraid Docker Pool Cleanup — Orphaned overlay2 After Storage-Driver Switch

**Date:** 2026-08-17
**Host:** Unraid 192.168.1.194 (root SSH, key-based)
**Context:** Docker pool reported 68–69GB used of 75GB (93–94%). User asked what was consuming the space and what could be removed without affecting live containers.

---

## Problem

The Docker pool is a 75GB loop image:

```
/mnt/disk1/system/docker/docker.img  ->  /dev/loop3  ->  /var/lib/docker
```

`df -h /var/lib/docker` showed **69G used / 5.0G free (94%)**, while `docker system df` (when it eventually responded) reported only ~29GB of Docker data. A ~39GB gap with no obvious explanation.

## Diagnosis

### 1. `du` is unreliable on this pool

```bash
du -sh /var/lib/docker   # reported 315GB — impossible on a 75GB disk
```

btrfs hardlinks (shared image layers) make `du` double-count. **Use `df` and `btrfs filesystem usage` for real numbers**, not `du`.

### 2. Confirm the actual storage driver (the key finding)

```bash
docker info | grep -i 'storage driver'
ps -eo pid,lstart,cmd | grep dockerd | grep -v grep
```

Both confirmed: **btrfs** (`dockerd ... --storage-driver=btrfs`).

### 3. Find the orphaned old-driver data

```bash
ls /var/lib/docker/overlay2 | wc -l        # 453 layer dirs
ls -lat /var/lib/docker/overlay2 | head -5 # newest: Jul 2 15:17
ls /var/lib/docker/btrfs/subvolumes | wc -l   # 362 subvols
ls -lat /var/lib/docker/btrfs/subvolumes | head -5  # newest: Aug 17 (today)
```

Docker had been switched from **overlay2 to btrfs around Jul 4** and the old `overlay2/` tree (~34GB) was never cleaned up. The live data lives in `btrfs/subvolumes/`.

### 4. Rule out false positives

- `mount | grep overlay` — the only 2 overlay mounts are **Unraid OS's own `/usr` and `/lib`** (`/var/local/overlay/...`), not Docker.
- `lsof | grep '(deleted)'` — no large deleted-but-open files held by Docker.
- `btrfs filesystem usage /var/lib/docker/btrfs` — Data,single Used: 62.96GiB (92.58%), consistent with the `df` gap.

### 5. Breakdown of the 68GB

| Category | Size | Status |
|---|---|---|
| Orphaned `overlay2/` | ~34GB | **NOT in use** (old driver, last touched Jul 2) |
| Live btrfs image layers | ~17.2GB | In use (20 active images) |
| Dangling images (8× `<none>`) | ~5.4GB | NOT in use |
| Container writable layers | 6.19GB | In use (reflexia-dev 4.36GB largest) |
| Build cache | ~1GB | Reclaimable |
| Volumes + metadata | ~460MB | Negligible |

## Fix

### Why stopping Docker is NOT required

The common advice is to stop Docker before `rm -rf`-ing anything under `/var/lib/docker`. That's only necessary if the daemon has file handles open into the target. Since dockerd runs with `--storage-driver=btrfs`, it never touches `overlay2/`. **Verify before deleting:**

```bash
# No dockerd fds pointing at overlay2 (expect empty output):
ls -l /proc/$(cat /var/run/dockerd.pid)/fd 2>/dev/null | grep overlay2

# No process with any file open in the tree (expect empty output):
timeout 20 fuser -v /var/lib/docker/overlay2
```

Both empty → safe to delete live, zero container downtime.

### Commands (run in order)

```bash
# 1. Remove orphaned old-driver tree (~34GB) — no Docker stop needed
rm -rf /var/lib/docker/overlay2

# 2. Prune dangling images
docker image prune -f

# 3. Remove unused named images (verify none are referenced by a container first)
docker rmi ghcr.io/openclaw/openclaw:latest spaceinvaderone/ha_inabox:latest

# 4. Prune build cache
docker builder prune -f

# 5. Verify
df -h /var/lib/docker
```

### Result

| Metric | Before | After |
|---|---|---|
| Pool used | 69G / 75G (94%) | 29G / 75G (40%) |
| Free | 5.0G | 43G |
| Running containers | 18 | 17 (one exited container removed) |

**~40GB reclaimed with zero container downtime.**

## Pitfalls Encountered

### Long remote commands survive SSH disconnects — don't restart them

The first `rm -rf /var/lib/docker/overlay2` ran over SSH and the connection was reset mid-deletion (`client_loop: send disconnect: Connection reset`). The `rm` process **kept running on the remote side** (reparented to init) and eventually finished.

- Check before re-running: `pgrep -af rm` (or `ps -eo pid,cmd | grep 'rm -rf'`).
- A competing second `rm` is harmless but pointless; a *different* command touching the same tree is not.
- To wait for completion from a new session: `while pgrep -x rm >/dev/null 2>&1; do sleep 5; done`
- If you *want* a command to survive disconnects by design, wrap it: `nohup bash -c '...' > /tmp/job.log 2>&1 &` — but be careful with nested quoting through PowerShell (see below).

### PowerShell mangles complex SSH commands

From Windows PowerShell 5.1, these all broke when passed through `ssh host '...'`:

- `$(...)` expands **locally** in PowerShell before SSH sees it.
- `grep -E "rm -rf"` → the `-f` got parsed as a grep option (`grep: option requires an argument -- 'f'`). Use `pgrep -af` instead.
- Nested `nohup bash -c "rm -rf /path; ..."` → inner path lost, `rm: missing operand`.
- `awk` with format strings, `|` in strings, `$?` — all mangled.

**Rules that worked:**
- Single-quote the whole remote command; avoid `$( )`, `$var`, and `|` inside it.
- Prefer `pgrep`/`wc -l`/`df`/`ls` over `awk`/`grep -E` with special chars.
- Use default table output instead of `docker ... --format '{{...}}'` (braces/quotes get eaten).
- Wrap slow remote commands in `timeout N` so they always exit.

### `docker system df` times out on a thrashing daemon

On a 93%-full pool, `docker system df` and `docker ps -a -s` repeatedly hung (daemon I/O thrash). `df -h` and direct `ls`/`btrfs` inspection always worked. After freeing space, `docker system df` still timed out — a pre-existing quirk, not a blocker.

## Generalizable Takeaways

1. **When `df` and `docker system df` disagree by tens of GB, suspect leftover data from a previous storage driver** (`overlay2/`, `aufs/`, `devicemapper/`) that Docker never garbage-collected after a driver switch.
2. **Never trust `du` on btrfs** for capacity questions — hardlinked layers are counted multiple times.
3. **Verify open handles before deleting live daemon data**: `/proc/<pid>/fd` + `fuser -v` are fast, definitive, and let you skip the downtime of stopping Docker.
4. **Orphaned remote processes outlive SSH** — always `pgrep` before re-running a long command after a dropped connection.
