---
description: 'Debugging the "New Session" button grayed out in opencode web UI, and fixing LiteLLM hostname resolution from Docker containers'
---

# opencode Web UI: New Session Button Grayed Out

## Symptoms

- Visiting `http://192.168.1.194:4096/` shows the opencode web UI, but the "New Session" button is grayed out / disabled
- Clicking it does nothing
- `POST /session` API works fine (returns 200 with a valid session)
- `GET /project` returns the workspace project correctly

## Root Cause

The web UI is a **React SPA** (v1.18.15, bundle `/assets/index-DkiM3pJJ.js`). The button's enabled state depends on a **client-side project selection** derived from the URL path:

1. `canCreateSession()` → `e.project.newSession()` → `e.project.selected()`
2. `selected()` looks up a project by matching `selection.directory` against project `worktree` paths
3. `selection.directory` comes from the **URL path**, decoded via a custom base64url function `ln()`
4. At root URL `/`, `selection.directory` is `undefined` → `selected()` returns `undefined` → button is grayed out

## Fix: Use Encoded Project Path in URL

Navigate to the project-specific URL instead of root:

```
http://192.168.1.194:4096/L3dvcmtzcGFjZQ
```

### How the Encoding Works

The `ln()` function is a custom base64url encoder (no padding, `+` → `-`, `/` → `_`):

```javascript
function ln(e) {
  const t = new TextEncoder().encode(e),
    n = Array.from(t, r => String.fromCharCode(r)).join("");
  return btoa(n).replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
}
```

- `ln("/workspace")` → `L3dvcmtzcGFjZQ`
- `ln("/some/other/path")` would produce a different base64url string

### Javascript DevTools Quick Fix

At the root URL page, run in console:

```javascript
window.history.pushState({}, '', '/L3dvcmtzcGFjZQ');
```

---

# LiteLLM Docker Hostname Resolution

## Symptom

opencode server (in `reflexia-dev` container) fails to reach LiteLLM with:

```
Could not resolve host: LiteLLM
```

## Root Cause

Both `reflexia-dev` and `LiteLLM` containers are on the **default Docker bridge network**, where Docker DNS does **not** resolve container names by default. The hostname `LiteLLM` only works if both containers are on a user-defined bridge network.

## Fix: Use Host IP Instead of Container Hostname

LiteLLM exposes port `4000` on `0.0.0.0:4000` (the Unraid host). Change `baseURL` from:

```
http://LiteLLM:4000/v1
```

to:

```
http://192.168.1.194:4000/v1
```

This is stable across container restarts because the host IP doesn't change.

### Config File Location

The config is at `opencode.json` in the workspace root (mounted into the container). For this project:

```
E:\Documents\Working\reflexia\opencode.json
```

## Debugging Commands

```powershell
# Test LiteLLM reachability from inside the container
ssh root@192.168.1.194 "docker exec reflexia-dev curl -s -H 'Authorization: Bearer t1smpspswd' http://192.168.1.194:4000/v1/models"

# Check which Docker network a container is on
ssh root@192.168.1.194 "docker inspect reflexia-dev --format '{{range .NetworkSettings.Networks}}{{.NetworkID}} {{.Aliases}} {{end}}'"

# Check LiteLLM port mapping
ssh root@192.168.1.194 "docker port LiteLLM"

# Restart the container after config change
ssh root@192.168.1.194 "docker restart reflexia-dev"
```

## Connecting the Desktop App

```powershell
opencode attach http://192.168.1.194:4096
```

The desktop app connects via the server's API/WebSocket, so it inherits the server-side config and doesn't need the encoded URL path.