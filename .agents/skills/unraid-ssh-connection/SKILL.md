---
name: unraid-ssh-connection
description: 'Expert in establishing and managing SSH connections to Unraid servers, troubleshooting connection issues, and executing remote commands.'
---

# Unraid SSH Connection Skill

**Expert in establishing and managing SSH connections to Unraid servers, troubleshooting connection issues, and executing remote commands.**

## Core Capabilities

- Establish SSH connections to Unraid servers via command line
- Configure SSH authentication (password and key-based)
- Diagnose connection failures and resolve configuration issues
- Execute remote commands on Unraid systems
- Configure tunnel and port forwarding when needed


# Prerequisites (Do Only One Time)

## Enable SSH in Unraid WebGUI

For command access to Unraid, SSH must be enabled first:

1. In Unraid WebGUI: **Settings > Management Access > Enable SSH** (set to "Yes").
2. Use **Settings > Management Access > Use SSH** to ensure it's open (port 22 by default).
3. Restart if needed—your ttyd shell at dockerplex.local:7070 suggests Docker/web access is already up.

![](https://i.imgur.com/dG6pOED.png)

![](https://i.imgur.com/83ZuEqX.png)

## SSH Key-Based Authentication Setup (Recommended)

For seamless, password-less SSH access, set up key-based authentication:

### Step 1: Check for Existing SSH Key

```powershell
Test-Path "$env:USERPROFILE\.ssh\id_ed25519"
```

If it returns `True`, you already have a key. If `False`, generate one:

```powershell
ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\id_ed25519" -N ""
```

### Step 2: Add Your Public Key to Unraid

```powershell
$pubKey = Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub"
ssh root@192.168.1.194 "mkdir -p ~/.ssh && echo '$pubKey' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && chmod 700 ~/.ssh"
```

You'll be prompted for the Unraid password once during this setup.

### Step 3: Test Key-Based Authentication

```powershell
ssh root@192.168.1.194 "echo 'SSH key authentication successful!'"
```

If successful, no password prompt appears. Now all subsequent SSH commands work without passwords:

```powershell
ssh root@192.168.1.194 "docker ps"
ssh root@192.168.1.194 "ls -la /mnt/user"
```

**Benefits:**
- ✅ No password prompts
- ✅ Better security
- ✅ Ideal for scripting and automation
- ✅ Can be used with GitHub Actions, cron jobs, etc.

## SSH Connection Methods

### Basic Connection

Connect to Unraid using default SSH (port 22) with password authentication:

```bash
ssh root@<unraid-ip>
```

Password: Use the value in `$UNRAID_PSWD` environment variable

### Connection with Environment Variable

For scripting and automation:

```bash
# Linux/macOS/PowerShell
sshpass -p "$UNRAID_PSWD" ssh root@<unraid-ip>
```

**Note:** `sshpass` must be installed first:

```bash
# macOS
brew install sshpass

# Ubuntu/Debian
sudo apt-get install sshpass

# Windows (via winget)
winget install sshpass
```

### Non-Standard Port

If SSH is configured on a custom port:

```bash
ssh -p <port> root@<unraid-ip>
```

Password: `$UNRAID_PSWD`

### Key-Based Authentication (Optional)

For secure, password-less connections (alternative to password auth):

```bash
ssh -i /path/to/private/key root@<unraid-ip>
```

On Windows with OpenSSH:

```powershell
ssh -i "$env:USERPROFILE\.ssh\id_rsa" root@192.168.1.194
```

## Prerequisites & Troubleshooting

### Installation Requirements

- **sshpass** — Required for automating password authentication

  ```bash
  # macOS
  brew install sshpass

  # Ubuntu/Debian
  sudo apt-get install sshpass

  # Windows (via winget)
  winget install sshpass
  ```
- **SSH client** — Pre-installed on macOS/Linux. Windows 10+ includes OpenSSH.

### Environment Variable Setup

Ensure `$UNRAID_PSWD` is defined:

```bash
# Test it's set
echo $UNRAID_PSWD  # Linux/macOS
echo $env:UNRAID_PSWD  # PowerShell
```

If not set, define it in your shell profile or `.env` file.

### Enable SSH on Unraid

1. Access Unraid WebUI
2. Navigate to **Settings → Management Access**
3. Verify **SSH** is enabled
4. Note the configured port (usually 22)

### Cannot Connect - Connection Closed

- **Wrong port**: Confirm SSH port in Unraid settings (port 7070 is web terminal, not SSH)
- **SSH disabled**: Enable SSH in Unraid Management Access settings
- **Invalid password**: Verify `$UNRAID_PSWD` value is correct
- **Firewall blocking**: Verify firewall allows SSH traffic
- **Network reachability**: Test with `ping <unraid-ip>` first

### Test sshpass Connection

```bash
sshpass -p "$UNRAID_PSWD" ssh root@192.168.1.194 "echo Connected"
```

### Test with nmap

Verify port is open and SSH is running:

```bash
nmap -p 22 <unraid-ip>
```

or (PowerShell):

```powershell
Test-NetConnection -ComputerName 192.168.1.194 -Port 22
```

## Remote Command Execution

Execute commands directly without interactive shell using password authentication:

```bash
sshpass -p "$UNRAID_PSWD" ssh root@<unraid-ip> "command-here"
```

Example - list Docker containers:

```bash
sshpass -p "$UNRAID_PSWD" ssh root@192.168.1.194 "docker ps"
```

**PowerShell examples:**

```powershell
# Simple command
$password = $env:UNRAID_PSWD
sshpass -p "$password" ssh root@192.168.1.194 "docker ps"

# Multi-line commands
$commands = @"
cd /mnt/user
ls -la
df -h
"@

sshpass -p "$password" ssh root@192.168.1.194 $commands
```

## File Transfer

### Using SCP with Password Authentication

Copy files to/from Unraid:

```bash
# Copy from local to Unraid
sshpass -p "$UNRAID_PSWD" scp /local/path/file root@<unraid-ip>:/remote/path/

# Copy from Unraid to local
sshpass -p "$UNRAID_PSWD" scp root@<unraid-ip>:/remote/path/file /local/path/
```

**PowerShell examples:**

```powershell
$password = $env:UNRAID_PSWD

# Copy to Unraid
sshpass -p "$password" scp "C:\local\file.txt" root@192.168.1.194:/mnt/user/

# Copy from Unraid
sshpass -p "$password" scp root@192.168.1.194:/mnt/user/file.txt "C:\local\"
```

### Using SFTP with Password Authentication

Interactive file transfer:

```bash
sshpass -p "$UNRAID_PSWD" sftp root@<unraid-ip>
```

## Port Forwarding

### Local Port Forwarding

Forward local port to service on Unraid:

```bash
ssh -L 8080:localhost:8080 root@<unraid-ip> -N
```

### Remote Port Forwarding

Forward Unraid service to local port (useful for reverse SSH):

```bash
ssh -R 8080:localhost:8080 root@<unraid-ip> -N
```

## SSH Configuration File

For frequent connections, add to `~/.ssh/config`:

```
Host unraid
    HostName 192.168.1.194
    User root
    Port 22
```

Then connect with:

```bash
ssh unraid
```

**Note:** Password authentication uses `$UNRAID_PSWD` environment variable when using `sshpass`

## Security Best Practices

- **Protect `$UNRAID_PSWD` environment variable** — Never commit it to version control
- **Use `.env` files locally** — Store `UNRAID_PSWD` in `.env` (add to `.gitignore`)
- **Restrict file permissions** — Ensure `.env` and scripts are not world-readable: `chmod 600`
- **Consider SSH keys** as an alternative to password authentication for production/automation
- **Update Unraid regularly** for security patches
- **Limit SSH access** via firewall rules if Unraid is exposed to internet

### Environment Variable Setup

**Linux/macOS:**

```bash
export UNRAID_PSWD="your-password-here"
```

**Windows PowerShell:**

```powershell
$env:UNRAID_PSWD = "your-password-here"
```

**Persistent setup (.bashrc/.profile):**

```bash
# Add to ~/.bashrc or ~/.profile
export UNRAID_PSWD="your-password"
```

## Common Issues

| Issue                             | Solution                                                                |
| --------------------------------- | ----------------------------------------------------------------------- |
| `Connection refused`            | SSH not enabled or running on different port                            |
| `Connection closed immediately` | Verify correct SSH port; web terminal may be on 7070                    |
| `sshpass: command not found`    | Install sshpass:`brew install sshpass` or `apt-get install sshpass` |
| `UNRAID_PSWD not recognized`    | Set environment variable:`export UNRAID_PSWD="password"`              |
| `Permission denied (password)`  | Verify username is `root` and `$UNRAID_PSWD` is correct             |
| `Connection timeout`            | Firewall blocking; verify network connectivity with `ping`            |
| `No route to host`              | Unraid IP incorrect or unreachable; verify with ping                    |

## Integration with Scripts

### Automated Backup via SSH

```bash
#!/bin/bash
UNRAID_IP="192.168.1.194"
BACKUP_DIR="/mnt/user/backups"
UNRAID_PSWD="${UNRAID_PSWD}"

sshpass -p "$UNRAID_PSWD" ssh root@$UNRAID_IP "tar czf - $BACKUP_DIR" > backup-$(date +%Y%m%d).tar.gz
```

### Executing Multiple Commands

```bash
#!/bin/bash
UNRAID_PSWD="${UNRAID_PSWD}"

sshpass -p "$UNRAID_PSWD" ssh root@192.168.1.194 << 'EOF'
cd /mnt/user
ls -la
df -h
EOF
```

### PowerShell Script Example

```powershell
$unraidIp = "192.168.1.194"
$password = $env:UNRAID_PSWD

# Execute Docker command
sshpass -p "$password" ssh root@$unraidIp "docker ps -a"

# Monitor logs
sshpass -p "$password" ssh root@$unraidIp "docker logs -f container_name"
```
