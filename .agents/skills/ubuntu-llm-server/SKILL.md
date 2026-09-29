# Ubuntu LLM Server SSH Access

## Hard Rule: Docker Stack Changes Go Through Portainer

Do not edit `docker-compose.yml`/`compose.yaml` files or run `docker compose up`/`docker rm`/`docker run` directly over SSH to add, remove, or modify a Docker stack or service on this box. Make the change in the Portainer UI at `https://192.168.1.149:9443/#!/auth` instead.

Editing a stack's files directly on disk (or recreating its container via the CLI) breaks Portainer's ownership of it, producing "Limited: This stack was created outside of Portainer. Control over this stack is limited." in the Portainer UI afterward. SSH is still fine for read-only diagnostics (`docker ps`, `docker stats`, `docker inspect`, `docker logs`) — just don't use it to mutate stack definitions or recreate containers.

### Browser access notes

- The Portainer cert is self-signed. Opening `https://192.168.1.149:9443/#!/auth` in an automated browser throws `ERR_CERT_AUTHORITY_INVALID` before the page renders — the interstitial "Your connection is not private" warning must be clicked through with the **"Proceed to 192.168.1.149 (unsafe)"** link to reach the login form.
- Login as `emiller25`, password = the `LITELLM_API_KEY` environment variable value with `2026` appended.
- Portainer's own container only has the Docker socket mounted (no host filesystem bind-mount), so `env_file:` entries pointing at absolute host paths (e.g. `/home/ethan/appdata/opencode/.env`) fail to deploy with "env file ... not found". Use `env_file: [stack.env]` in the compose and populate the actual KEY=VALUE pairs via the stack form's "Environment variables" panel (Advanced mode accepts pasted `KEY=value` lines) instead.
- If a compose service uses `build: {context, dockerfile}` pointing at a relative path outside Portainer's own stack storage, redeploying via the Web editor will fail to find that context. Swap `build:` for `image: <already-built-image>:<tag>` (check `docker images` on the host) when the image is already built locally — Portainer only needs the image reference, not the Dockerfile.

## Connection Details

- **Host**: `192.168.1.149`
- **User**: `ethan` (lowercase)
- **SSH Key**: `~/.ssh/id_ed25519_ubuntu` (key-based auth already set up — no password needed)
- **Service**: llama.cpp server running on port 8080

## Quick Connect

```powershell
ssh -i "$env:USERPROFILE\.ssh\id_ed25519_ubuntu" ethan@192.168.1.149
```

No password prompt — the public key is already in `~/.ssh/authorized_keys` on the server.

## Key Paths

| Location | Path |
|---|---|
| Local (Windows) | `$env:USERPROFILE\.ssh\id_ed25519_ubuntu` |
| Local (PowerShell) | `"$env:USERPROFILE\.ssh\id_ed25519_ubuntu"` |
| Server (Linux) | `~/.ssh/id_ed25519_ubuntu.pub` (in authorized_keys) |

## Common Diagnostics

### GPU Status

```bash
nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,utilization.memory --format=csv,noheader,nounits
nvidia-smi --query-compute-apps=pid,name,used_memory --format=csv
```

### llama.cpp Process

```bash
ps aux | grep llama-server
# Check for: -ngl (GPU layers), -c (context), -t (threads), -cb (continuous batching)
```

### System Resources

```bash
free -h            # RAM and swap usage
uptime             # Load average
df -h              # Disk space
```

### Server Health

```bash
curl -s http://localhost:8080/health
curl -s http://localhost:8080/
```

## Current llama.cpp deployment

The production Qwen3.6-27B deployment currently uses:

```text
-np 2 -c 176128
```

llama.cpp reports two slots with an `88064`-token context per slot. LiteLLM and OpenClaw must be updated whenever these values change. Use the [llama.cpp configuration synchronization skill](../llama-cpp-config-sync/SKILL.md), including its semantic-compaction threshold procedure, rather than changing only the Docker arguments.

## Troubleshooting

- **Connection refused**: SSH may not be enabled on port 22. Check with `nc -zv 192.168.1.149 22` from another machine.
- **Permission denied**: Verify username is lowercase `ethan`. Check key file exists: `ls ~/.ssh/id_ed25519_ubuntu`
- **Slow inference**: Check VRAM usage. If >90% full, context window may be too large for available VRAM.
- **Model timeouts**: Check if llama-server process is still running: `ps aux | grep llama-server`

## Key Commands

| Command                                   | Purpose                     |
| ----------------------------------------- | --------------------------- |
| `ssh ethan@192.168.1.149`               | Connect to server           |
| `nvidia-smi`                            | GPU memory and utilization  |
| `htop`                                  | CPU/memory usage            |
| `journalctl -u llama-server`            | Server logs (if systemd)    |
| `docker ps -a`                          | Check for Docker containers |
| `cat /proc/cpuinfo \| grep "model name"` | CPU details                 |

## Common Issues

### VRAM Saturation

RTX 3090 has 24GB VRAM. If model + KV cache uses >90%, context window spills to RAM causing slow inference.

- Check: `nvidia-smi | grep "Memory-Usage"`
- Fix: Reduce context window (`-c`), reduce GPU layers (`-ngl`), or use smaller model

### No GPU Processes

If `nvidia-smi --query-compute-apps` shows no processes but llama-server is running, the server may be CPU-only or using a different GPU.
