---
description: 'Never modify Docker containers in ways that would cause Unraid to lose UI management'
applyTo: '**'
---

## Unraid Docker Management Rule (NON-NEGOTIABLE)

**Never perform any Docker operation that would cause Unraid to treat a managed container as a third-party/unmanaged container.**

### Forbidden Actions

1. **Never change Docker image tags** on Unraid-managed containers. If a container needs a newer image, the user must change it through the Unraid UI (Docker tab → container → Edit → change tag → Apply).

2. **Never create docker-compose files** for containers managed by Unraid's Docker template system. Creating a compose file will cause Unraid to see the container as third-party and lose UI management.

3. **Never recreate containers** with different parameters (volumes, ports, env vars) outside of Unraid's management interface.

4. **Never modify container configurations** directly through Docker commands if they were originally created via Unraid templates.

### What IS Allowed

- Reading container inspect data: docker inspect <container>
- Reading logs: docker logs <container>
- Executing commands inside containers: docker exec <container> <command>
- Removing plugin/config files inside containers (preserving the container identity)
- Pulling new images for later use (without changing which image the container uses)

### How to Safely Update Unraid Container Images

If a container needs updating:

1. **Check if the new image tag exists:**
   `ash
   ssh root@192.168.1.194 "docker pull ghcr.io/openclaw/openclaw:2026.7.1"
   `

2. **Report to user** that they need to update via Unraid UI:
   - Go to Unraid Docker tab
   - Click on the container name
   - Click "Edit"
   - Change the repository tag from latest to 2026.7.1
   - Click "Apply"

3. **Do NOT** manually recreate the container or change its image tag via Docker commands.

### Exception

The only exception is if the container was explicitly created via docker-compose or manual docker run commands documented in this repository. In that case, document the management method and follow the same pattern.

### Verification

After any Docker operation on Unraid, verify the container is still managed:

`ash
ssh root@192.168.1.194 "docker ps --filter name=<container> --format '{{.Names}}\t{{.Image}}\t{{.Status}}'"
`

If the container disappears from docker ps or shows as "exited" unexpectedly, it may have been unlinked from Unraid's management. Report this to the user immediately.
