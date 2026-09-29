---
description: 'Set up SSH key-based auth from the OpenClaw container on Unraid to remote hosts (e.g., LLM box)'
applyTo: '**'
---

# OpenClaw SSH Setup

Set up key-based SSH from the OpenClaw container to a remote host (e.g., LLM box at `192.168.1.149`).

## Why this works

The OpenClaw container has `/mnt/user/appdata` bind-mounted at `/appdata` inside the container. SSH keys stored at `/appdata/openclaw/data/ssh/` inside the container live on the host at `/mnt/user/appdata/openclaw/data/ssh/`, so they persist across container recreation.

## One-time setup (from your laptop)

### Step 1: Generate SSH key on the host

```powershell
ssh root@192.168.1.194 "mkdir -p /mnt/user/appdata/openclaw/data/ssh && ssh-keygen -t ed25519 -C openclaw-copilot -f /mnt/user/appdata/openclaw/data/ssh/id_ed25519_llm -N ''"
```

### Step 2: Copy public key to the target host

```powershell
$pubKey = ssh root@192.168.1.194 "cat /mnt/user/appdata/openclaw/data/ssh/id_ed25519_llm.pub"
ssh ethan@192.168.1.149 "mkdir -p ~/.ssh && echo '$pubKey' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

You'll be prompted for the `ethan` password on the LLM box once.

### Step 3: Verify

```powershell
ssh root@192.168.1.194 "docker exec OpenClaw ssh -i /appdata/openclaw/data/ssh/id_ed25519_llm ethan@192.168.1.149 echo 'SSH key auth works!'"
```

## Usage from inside OpenClaw

```bash
ssh -i /appdata/openclaw/data/ssh/id_ed25519_llm ethan@192.168.1.149
```

## Adding additional hosts

Repeat steps 2–3 for each new target, generating a new key pair with a different filename:

```powershell
# Generate key for a different host
ssh root@192.168.1.194 "ssh-keygen -t ed25519 -C openclaw-agent -f /mnt/user/appdata/openclaw/data/ssh/id_ed25519_agent -N ''"

# Copy to the new host
$pubKey = ssh root@192.168.1.194 "cat /mnt/user/appdata/openclaw/data/ssh/id_ed25519_agent.pub"
ssh user@<host-ip> "mkdir -p ~/.ssh && echo '$pubKey' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

## Key paths reference

| Location | Path |
|---|---|
| Host (Unraid) | `/mnt/user/appdata/openclaw/data/ssh/id_ed25519_llm` |
| Container (OpenClaw) | `/appdata/openclaw/data/ssh/id_ed25519_llm` |
