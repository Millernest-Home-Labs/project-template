---
description: 'Plex container crashes with ENOTCONN when Unraid share disconnects, fix is stop+start'
---

## Unraid Plex Container Crash - ENOTCONN

### Issue

`binhex-plex` Docker container on Unraid enters FATAL state and refuses to start. Container logs show repeated:

```
mkdir: cannot create directory '/config': Transport endpoint is not connected
sed: can't read /config/Plex Media Server/Preferences.xml: Transport endpoint is not connected
libc++abi: terminating with uncaught exception of type boost::filesystem::filesystem_error:
  boost::filesystem::create_directories: Socket not connected [system:107]: "/config/Plex Media Server/Cache"
```

Supervisor enters `FATAL state, too many start retries too quickly`.

### Root Cause

The Unraid `/mnt/user` share was disconnected from its underlying disks. This means either:
- The Unraid array was **not running**
- Disks had **failed** or **gone offline**
- A transient NFS/mergerfs disconnect on the share

The container bind-mounts `/mnt/user/appdata/Plex` to `/config`, so when the share disconnects, the container loses access to all config files and crashes.

### Diagnosis

```bash
# Check container state
docker ps --filter name=plex --format "{{.Names}}\t{{.Status}}"
# Shows: binhex-plex  Up 19 hours (unhealthy) or FATAL state

# Verify share is accessible
df -h /mnt/user/appdata/Plex
# If disconnected: "Transport endpoint is not connected" or empty output

# Check logs
docker logs --tail 100 binhex-plex
# Look for ENOTCONN errors
```

### Fix

1. **Ensure Unraid array is running** (check from UI)
2. **Restart the container:**
   ```bash
   ssh root@192.168.1.194
   docker stop binhex-plex
   docker start binhex-plex
   ```
3. **Verify health:**
   ```bash
   docker ps --filter name=plex
   # Should show: binhex-plex  Up X minutes (healthy)
   ```

Plex takes 2-3 minutes to fully initialize and pass health checks.

### Known Cosmetic Errors (ignore these)

- **`Critical: libusb_init failed`** — Known issue with binhex-plex container. USB library fails to initialize inside the container. Does not affect Plex functionality.
- **`Crash Uploader --userId error`** — After a crash, the cleanup script prints its help text. Cosmetic, not an error.
- **`database migrations` (HTTP 503)** — Plex runs DB migrations after restart. Normal and expected.

### Prevention

- Monitor Unraid array status via the UI
- Set up Unraid email alerts for disk failures
- Consider adding a health check script that restarts the container if it enters FATAL state

### Related Files

- `/root/.openclaw/workspace/agents/software-engineer/unraid-docker-management.md` — Unraid Docker management rules (NON-NEGOTIABLE)
