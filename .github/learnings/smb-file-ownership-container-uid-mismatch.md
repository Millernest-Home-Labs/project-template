---
description: 'SMB file ownership fix for NAS-mounted repos: running the Docker container as UID 1000 to match the SMB user so files created by the container are writable over SMB from the laptop'
---

# SMB File Ownership Mismatch: Docker Container as Root vs SMB User

## Problem

The `reflexia-dev` container runs as `root` (UID 0). Files it creates/modifies in the bind-mounted repo (`/workspace`) end up owned by `root:root` on the host filesystem. When accessing the repo over SMB from a laptop as user `ethan` (UID 1000), Samba applies "other" permissions — read-only for files with `-rw-r--r--` (644). The container (OpenCode) can write freely (Docker bind mounts bypass SMB), but the laptop user cannot.

## Symptoms

- `.fuse_hidden*` files appear in the repo directory listing (FUSE artifacts from failed SMB writes)
- `smbstatus` shows all open file handles as `RDONLY`
- `ls -la` shows files owned by `root:root` instead of `ethan:users`
- OpenCode inside the container can write fine; the laptop user cannot

## Root Cause

Both `/mnt/user/appdata` and `/mnt/user/Media` are on the same `shfs` (FUSE SHFS) filesystem — no different mount type. The issue is purely about UID mismatch:

| Access path | UID | Can write? |
|---|---|---|
| Container (Docker bind mount) | root (0) | Yes — matches file owner `root` |
| Laptop (SMB/CIFS) | ethan (1000) | No — "other" permissions only, read-only on 644 files |

## Solution: Run Container as UID 1000

### 1. Add `user: "1000:1000"` to compose.yaml

```yaml
services:
  reflexia-dev:
    user: "1000:1000"
    # ...
    volumes:
      - /mnt/user/appdata/reflexia/opencode-data:/home/node/.local/share/opencode
```

### 2. Fix opencode data directory ownership

```bash
chown -R 1000:1000 /mnt/user/appdata/reflexia/opencode-data
```

### 3. Install opencode to a system-wide PATH (not just /root/.opencode)

```dockerfile
# Old: only accessible to root
ENV PATH="/root/.opencode/bin:${PATH}"

# New: accessible to all users
RUN curl -fsSL https://opencode.ai/install | bash \
    && cp /root/.opencode/bin/opencode /usr/local/bin/opencode \
    && rm -rf /root/.opencode
```

### 4. Fix the opencode data volume path

The `node` user's home is `/home/node`, not `/root`. The volume mount must point to the correct location:

```yaml
# Old: /root/.local/share/opencode
# New: /home/node/.local/share/opencode
volumes:
  - /mnt/user/appdata/reflexia/opencode-data:/home/node/.local/share/opencode
```

### 5. Pre-create the node user's writable directories in Dockerfile

When running as UID 1000 (`node` user), the container needs `/home/node/.local/state` to exist and be owned by `node`. The base image doesn't create it. Add this to the Dockerfile:

```dockerfile
# Pre-create home directories for the node user (UID 1000) so it can write
RUN mkdir -p /home/node/.local/state /home/node/.local/share/opencode \
    && chown -R 1000:1000 /home/node/.local
```

Without this, opencode (which uses Bun) crashes on startup with:
```
EACCES: permission denied, mkdir '/home/node/.local/state'
```

## Key Files

- `/boot/config/plugins/compose.manager/projects/opencode/compose.yaml`
- `/boot/config/plugins/compose.manager/projects/opencode/.devcontainer/Dockerfile`

## Verification

After the container restarts, files created by OpenCode will be owned by `ethan:users` (UID 1000:1000) and writable over SMB from the laptop.