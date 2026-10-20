---
description: 'Persistent storage setup for the reflexia-dev opencode container on Unraid: appdata volume, kubectl, opencode database, and compose configuration'
---

# reflexia-dev Container Persistence

## Problem

The `reflexia-dev` container (running `opencode serve`) loses all state on restart:
- opencode sessions and database are ephemeral
- `kubectl` binary and kubeconfig are gone
- `node_modules` and `.venv` get reinstalled by agents

## Solution: Bind Mounts via Docker Compose

The container is managed by Unraid's Compose Manager at:

```
/boot/config/plugins/compose.manager/projects/opencode/compose.yaml
```

### Final Compose File

```yaml
services:
  reflexia-dev:
    build:
      context: .
      dockerfile: .devcontainer/Dockerfile
    container_name: reflexia-dev
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - AGENT_BROWSER_EXECUTABLE_PATH=/usr/bin/chromium
    ports:
      - "4096:4096"
    volumes:
      - /mnt/user/appdata/reflexia/opencode-data:/root/.local/share/opencode
      - /mnt/user/appdata/reflexia:/appdata:cached
      - /mnt/user/Media/Documents/Working/reflexia:/workspace:cached
    working_dir: /workspace
    entrypoint: []
    command: opencode serve --hostname 0.0.0.0 --port 4096
```

### Volume Mounts Explained

| Host Path | Container Path | Purpose |
|---|---|---|
| `/mnt/user/appdata/reflexia/opencode-data` | `/root/.local/share/opencode` | Persists opencode SQLite DB (sessions, projects) |
| `/mnt/user/appdata/reflexia` | `/appdata` | General persistent storage (kubectl, kubeconfig, scripts) |
| `/mnt/user/Media/Documents/Working/reflexia` | `/workspace` | Project source code (SMB mount from Windows) |

### Why Bind Mount Instead of Symlink

opencode calls `os.MkdirAll()` on startup which replaces symlinks with directories. A bind mount at the Docker level avoids this entirely — the directory is mounted before any process starts.

## Persistent Tools Setup

### kubectl

```bash
# Install kubectl inside the container
docker exec reflexia-dev sh -c 'curl -sLO https://dl.k8s.io/release/v1.33.6/bin/linux/amd64/kubectl && chmod +x kubectl && mv kubectl /usr/local/bin/kubectl'

# Copy to persistent volume
docker exec reflexia-dev mkdir -p /appdata/bin
docker exec reflexia-dev cp /usr/local/bin/kubectl /appdata/bin/kubectl
```

### Kubeconfig

```bash
# Copy from OpenClaw's existing kubeconfig (same K3s cluster)
docker cp /mnt/user/appdata/openclaw/config/workspace/kubeconfig.yaml reflexia-dev:/appdata/kube/config
```

### Setup Script (`/appdata/setup.sh`)

```bash
export PATH=$PATH:/appdata/bin
export KUBECONFIG=/appdata/kube/config
```

Usage: `. /appdata/setup.sh && kubectl get nodes`

### Verifying Persistence After Restart

```bash
docker exec reflexia-dev sh -c '. /appdata/setup.sh && kubectl get nodes'
```

## K3s Cluster Access

The K3s cluster is at `k3-lab-01` (192.168.1.206), not on the Unraid host. The reflexia-dev container can reach it directly:

| Service | Address | Port |
|---|---|---|
| K3s API | `192.168.1.206:6443` | 6443 |
| MySQL (dev) | `192.168.1.206:30306` | 30306 |
| Loki | `192.168.1.206:30953` | 30953 |
| MinIO | `10.43.120.80:9000` (ClusterIP) | 9000 |

The container is on the default Docker bridge network. Container hostnames (like `LiteLLM`) do **not** resolve on this network — use the host IP `192.168.1.194` instead.

## Debugging Commands

```powershell
# Check compose file
ssh root@192.168.1.194 "cat /boot/config/plugins/compose.manager/projects/opencode/compose.yaml"

# Restart container via compose
ssh root@192.168.1.194 "docker compose -f /boot/config/plugins/compose.manager/projects/opencode/compose.yaml up -d reflexia-dev"

# Check container mounts
ssh root@192.168.1.194 "docker inspect reflexia-dev | grep -A10 Mounts"

# Check opencode sessions via API
Invoke-WebRequest -Uri "http://192.168.1.194:4096/session" -UseBasicParsing | Select-Object -ExpandProperty Content | ConvertFrom-Json | Select-Object id, title

# Check opencode config
Invoke-WebRequest -Uri "http://192.168.1.194:4096/config" -UseBasicParsing | Select-Object -ExpandProperty Content | ConvertFrom-Json

# Query opencode database directly
docker exec reflexia-dev sqlite3 /root/.local/share/opencode/opencode.db "SELECT id, title FROM session ORDER BY time_created DESC LIMIT 10;"
```

## Key Lessons

1. **`OPENCODE_DATA_DIR` is not a recognized env var** — opencode determines its data directory from `~/.local/share/opencode/` and the config file's `data.directory` key (which may not be supported in all versions). Use a bind mount instead.
2. **`rm -rf` follows symlinks** — `rm -rf /root/.local/share/opencode` when `opencode` is a symlink will delete the target's contents. Use `rm -f` (without `-r`) to remove just the symlink.
3. **Default Docker bridge doesn't resolve container names** — containers on the `bridge` network must use IP addresses or be on a user-defined network for DNS resolution.
4. **Compose YAML port values must be strings** — `"4096:4096"` not `4096:4096` to avoid YAML parsing issues.