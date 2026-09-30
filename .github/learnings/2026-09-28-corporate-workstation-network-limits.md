# Corporate Workstation Network Limits (Read Before Touching the Home Lab)

Date: 2026-09-28  
Applies to: any agent session running on the **corporate-managed Windows laptop** (host IP `192.168.1.177` on home Wi-Fi).  
Status: **Known limitation. Do not retry the blocked paths below.**

## TL;DR for Agents

- This laptop **cannot open most TCP connections to home-lab LAN hosts**. The OS refuses them locally with **WSAEACCES 10013**.
- This is a **deliberate corporate security control** (Cisco Secure Client / managed endpoint policy), not a lab misconfiguration.
- **Do not bypass it** (no SSH tunnels, proxies, or port hopping, and no disabling or reconfiguring Cisco software). Bypassing a corporate security control violates policy.
- Use only the working paths listed below, or stop and tell the user the task needs a non-corporate machine or in-cluster execution.

## How to Recognize It

```
connectex: An attempt was made to access a socket in a way forbidden by its access permissions.
cannot connect to 192.168.1.206:30185: ... forbidden by its access permissions. (10013)
Test-NetConnection 192.168.1.206 -Port <port>  ->  TcpTestSucceeded : False
```

| Error               | Meaning                                                 | Cause                                     |
| ------------------- | ------------------------------------------------------- | ----------------------------------------- |
| **10013 WSAEACCES** | Local OS refused the connect; no packet left the laptop | **Corporate endpoint filter (this doc)**  |
| 10061 refused       | The remote host answered, but nothing is listening      | A real service/port problem on the target |
| 10060 timeout       | Packets left, no reply                                  | Routing / remote firewall                 |

If you see **10013**, stop. It is not a cluster, NGINX, or Traefik problem, and changing lab infrastructure will not fix it.

## Observed Facts (2026-09-28)

- The laptop is on the same subnet as the lab (`192.168.1.0/24`, gateway `192.168.1.254`). The VPN tunnel is **not** connected (the Cisco virtual adapter is Disabled).
- Running: **Cisco Secure Client - AnyConnect VPN Agent** and **Cisco Secure Client - ISE Posture Agent**.
- No visible Windows Firewall outbound block rules. The filter comes from the managed agent through the Windows Filtering Platform. The exact rule requires admin rights (`netsh wfp show filters`) and was not inspected.

Reachability from this laptop to K3s node `192.168.1.206`:

| Port     | Purpose                                      | Result              |
| -------- | -------------------------------------------- | ------------------- |
| 22       | SSH                                          | Allowed             |
| 80 / 443 | HTTP(S)                                      | **Blocked (10013)** |
| 6443     | K3s API                                      | **Blocked (10013)** |
| 30185    | Emulator ADB NodePort                        | **Blocked (10013)** |
| 31046    | Rancher LAN NodePort (`kubeconfig-lan.yaml`) | **Blocked (10013)** |

Assume **any** other LAN port is blocked unless tested and proven otherwise.

## What Works From This Laptop

| Path                                                                                                 | Works?                 | Notes                                                                                                                                                                                                |
| ---------------------------------------------------------------------------------------------------- | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `kubeconfig.yaml` -> `https://rancher.millernest.com/k8s/clusters/local` (public DNS, internet path) | **Yes, REST only**     | `get`, `describe`, `logs`, `apply`, `scale`, `delete`, `run`, `auth can-i`                                                                                                                           |
| Same, streaming APIs (`exec`, `port-forward`, `attach`, `cp`)                                        | **No**                 | `Upgrade request required`. WebSockets are already enabled on the NGINX proxy host, so the suspected cause is the corporate web/security layer stripping the upgrade handshake (unverified).         |
| `kubeconfig-lan.yaml` -> `https://192.168.1.206:31046`                                               | **No**                 | 10013                                                                                                                                                                                                |
| `adb connect 192.168.1.206:30185`                                                                    | **No**                 | 10013 (and ADB is loopback-only inside the pod anyway)                                                                                                                                               |
| SSH to `192.168.1.206` on port 22                                                                    | Reachable              | **Do not use it to tunnel other ports.** That bypasses the control.                                                                                                                                  |
| `gh` CLI                                                                                             | **No (for lab repos)** | Authenticated as corporate EMU account `ethan-miller_gmf` via `GH_TOKEN`; `Millernest-Home-Labs/*` returns 404. Do not swap in a personal token on this device without the user's explicit decision. |

## Do NOT Retry (Known Dead Ends)

1. `adb connect 192.168.1.206:<nodeport>`: 10013.
2. `kubectl --kubeconfig kubeconfig-lan.yaml ...`: 10013.
3. `kubectl exec` / `kubectl port-forward` through `rancher.millernest.com`: `Upgrade request required`. `KUBECTL_PORT_FORWARD_WEBSOCKETS=false` (SPDY) fails the same way.
4. Adding PATH entries, reinstalling kubectl/adb, or changing kubectl versions: the tooling is fine.
5. Changing NGINX Proxy Manager WebSocket settings: already enabled.
6. `ssh -L` / `ssh -D` / socat / ngrok / any tunnel to reach blocked ports: **policy violation. Forbidden.**
7. Stopping, disabling, or reconfiguring Cisco Secure Client or Windows Filtering Platform rules: **policy violation. Forbidden.**

## Approved Ways Forward

1. **In-cluster execution with REST only (works today).** Create a short-lived `restartPolicy: Never` pod in the cluster that does the network work (adb, Maestro, curl), then read results via `kubectl logs` and delete the pod. Put scripts in a YAML block scalar applied from a file; PowerShell 5.1 mangles quotes in `bash -c "..."`. See `2026-09-28-amminox-android-emulator-first-pass.md`.
2. **Non-corporate machine.** Run the interactive agent loop (adb, Maestro, LAN kubeconfig) from a personal PC or a lab-hosted devcontainer/VM. All LAN paths work there.
3. **IT exception.** The user may request a sanctioned exception from their IT/security team for `192.168.1.0/24`. Agents never make or assume this change.

If a task strictly requires interactive streaming access (live adb shell, port-forward, Maestro Studio) and neither option 1 nor 2 is available, **stop and report the limitation**. Do not improvise workarounds.

## Security Hygiene Reminders

- Kubeconfigs live in `.github/secrets/` (git-ignored as `.github/secrets/`; the old `.github\secrets` rule matched nothing). Never print, echo, or paste token values.
- `kubeconfig-lan.yaml` uses `insecure-skip-tls-verify: true`. Replace it with `certificate-authority-data` before relying on it from a trusted machine.
- The LAN kubeconfig token was shared in a chat session on 2026-09-28. Rotate it.
- Holding cluster-admin credentials for a personal lab on a corporate device may itself fall under the employer's acceptable-use policy. That is the user's decision, not the agent's.

## Working Around Missing CI Visibility (policy-compliant)

`gh` cannot see the lab repos from this laptop, but `git push` works (credentials in the remote URL). To follow a workflow run without GitHub access:

- **Job results**: `kubectl -n ci logs github-runner-<N> -c runner --since=30m | Select-String "Running job|completed with result"`. Ordinal N = line in the `runner-repos` ConfigMap (0 reflexia, 1 unbound-preaching, 2 labs-infra, 3 amminox once registered).
- **Step output is NOT in pod logs.** To see why a Docker build failed, reproduce it in-cluster with a throwaway Kaniko pod (`gcr.io/kaniko-project/executor`, `--no-push`, context from a ConfigMap), read `kubectl logs`, then delete the pod and ConfigMap. Caveat: ConfigMap files mount as symlinks, so `COPY` of them yields dangling links in Kaniko; errors after that point are a diagnostic artifact, not a real failure.
- **Cluster outcome**: check the resources the workflow creates (e.g. `ci/android-emulator-config`, lease Deployments labelled `app.kubernetes.io/name=android-emulator`).
