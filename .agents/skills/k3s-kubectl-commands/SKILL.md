---
name: k3s-kubectl-commands
description: 'Expert in deploying, managing, and troubleshooting Kubernetes workloads on K3s clusters using kubectl: set secrets, roll out images, check pod health, inspect events and logs (including Loki), verify services/ports, MySQL and MinIO status. USE WHEN: kubectl, K3s, deploy image, rollout, set secret, pod crashloop, pod logs, cluster health, namespace dev, infra task.'
---

# K3s Kubectl Commands Skill

**Expert in deploying, managing, and troubleshooting Kubernetes workloads on K3s clusters using kubectl command-line tool.**

## Millernest Lab Operating Rules

- Cluster: self-hosted K3s at `192.168.1.206`. Always pass `-n dev` explicitly unless told otherwise.
- Kubeconfig locations: `/appdata/kube/config` (OpenClaw/opencode container, kubectl at `/appdata/bin/kubectl`); `.github/secrets/kubeconfig.yaml` (Rancher proxy) or `kubeconfig-lan.yaml` on workstations. `.github/secrets/` must stay git-ignored.
- **Never** print, commit, persist or summarize kubeconfig contents or secret values. Redact commands and output.
- When setting secrets, update only the requested keys, idempotently: `kubectl create secret ... --dry-run=client -o yaml | kubectl apply -f -`.
- Never delete or scale down production services. Restore any `dev` resource you scaled for testing to its original replica count.
- Do not modify application code from an infra task; report actions, redacted commands, results and errors.
- Deploy order: ConfigMap -> Service -> Deployment -> `kubectl set image` -> `kubectl rollout status --timeout=600s` -> Ingress. If the rollout fails, `kubectl rollout undo`.
- From the corporate laptop, `exec`/`port-forward` fail (`Upgrade request required`) and LAN ports fail with WSAEACCES 10013. Do not retry or tunnel. Use REST-only commands plus short-lived in-cluster pods read via `kubectl logs`. See `.github/learnings/2026-09-28-corporate-workstation-network-limits.md`.

## Core Capabilities

- Configure kubectl to connect to K3s clusters
- Deploy and manage applications on K3s
- Monitor cluster health and workload status
- Troubleshoot pods, services, and deployments
- Manage configurations, secrets, and persistent volumes

## Kubeconfig Setup

### Locate K3s Kubeconfig

On the K3s server, the config is typically at:

```bash
/etc/rancher/k3s/k3s.yaml
```

### Copy to Local Machine

From K3s server to local via SCP:

```bash
scp root@<k3s-server>:/etc/rancher/k3s/k3s.yaml ~/.kube/config
```

### Verify Connection

```bash
kubectl cluster-info
kubectl get nodes
```

## Common kubectl Commands

### Cluster Information

```bash
# Get cluster info
kubectl cluster-info

# Get nodes
kubectl get nodes
kubectl get nodes -o wide

# Get node details
kubectl describe node <node-name>
```

### Pod Management

```bash
# List pods
kubectl get pods
kubectl get pods -n <namespace>
kubectl get pods -A  # all namespaces

# Pod details
kubectl describe pod <pod-name> -n <namespace>

# View pod logs
kubectl logs <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace> --tail=100 -f  # follow logs

# Execute commands in pod
kubectl exec -it <pod-name> -n <namespace> -- /bin/bash

# Copy files to/from pod
kubectl cp <namespace>/<pod-name>:/path/to/file ./local/path
```

### Deployments

```bash
# List deployments
kubectl get deployments -n <namespace>

# View deployment details
kubectl describe deployment <deployment-name> -n <namespace>

# Check rollout status
kubectl rollout status deployment/<deployment-name> -n <namespace>

# View deployment history
kubectl rollout history deployment/<deployment-name> -n <namespace>

# Rollback deployment
kubectl rollout undo deployment/<deployment-name> -n <namespace>
```

### Apply Configurations

```bash
# Apply manifest file
kubectl apply -f deployment.yaml

# Apply all files in directory
kubectl apply -f ./manifests/

# Apply with dry-run (preview)
kubectl apply -f deployment.yaml --dry-run=client -o yaml
```

### Services

```bash
# List services
kubectl get svc -n <namespace>

# Service details
kubectl describe svc <service-name> -n <namespace>

# Port forwarding
kubectl port-forward svc/<service-name> 8080:80 -n <namespace>
```

### ConfigMaps and Secrets

```bash
# List ConfigMaps
kubectl get configmaps -n <namespace>

# View ConfigMap
kubectl get configmap <config-name> -n <namespace> -o yaml

# Create ConfigMap from file
kubectl create configmap <config-name> --from-file=./config/ -n <namespace>

# List Secrets
kubectl get secrets -n <namespace>

# View Secret (base64 encoded)
kubectl get secret <secret-name> -n <namespace> -o yaml
```

### Namespaces

```bash
# List namespaces
kubectl get namespaces

# Create namespace
kubectl create namespace <namespace-name>

# Set default namespace
kubectl config set-context --current --namespace=<namespace-name>

# Delete namespace
kubectl delete namespace <namespace-name>
```

### Deleting Resources

```bash
# Delete pod
kubectl delete pod <pod-name> -n <namespace>

# Delete deployment
kubectl delete deployment <deployment-name> -n <namespace>

# Delete all resources matching label
kubectl delete pods -l app=myapp -n <namespace>

# Force delete stuck pod
kubectl delete pod <pod-name> -n <namespace> --grace-period=0 --force
```

## Troubleshooting

### Check Cluster Health

```bash
# Node status
kubectl get nodes
kubectl describe node <node-name>

# Pod status
kubectl get pods -A
kubectl describe pod <pod-name> -n <namespace>

# Check ready status
kubectl get pods -o wide -n <namespace>
```

### View Events

```bash
# Recent cluster events
kubectl get events -A --sort-by='.lastTimestamp'

# Events for specific namespace
kubectl get events -n <namespace>

# Namespace events sorted
kubectl get events -n <namespace> --sort-by='.metadata.creationTimestamp'
```

### Inspect Pod Issues

```bash
# Get pod description
kubectl describe pod <pod-name> -n <namespace>

# View pod logs
kubectl logs <pod-name> -n <namespace>

# View previous container logs (if crashed)
kubectl logs <pod-name> -n <namespace> --previous

# Execute bash in pod
kubectl exec -it <pod-name> -n <namespace> -- /bin/bash

# Check pod resource usage
kubectl top pods -n <namespace>
```

### Resource Status

```bash
# Check persistent volumes
kubectl get pv
kubectl get pvc -n <namespace>

# Describe PVC
kubectl describe pvc <pvc-name> -n <namespace>

# Storage classes
kubectl get storageclass
```

## Advanced Options

### Context Management

```bash
# List contexts
kubectl config get-contexts

# Switch context
kubectl config use-context <context-name>

# Rename context
kubectl config rename-context <old-name> <new-name>
```

### Resource Watching

```bash
# Watch pod status changes
kubectl get pods -n <namespace> -w

# Watch specific pod
kubectl get pod <pod-name> -n <namespace> -w
```

### Patching Resources

```bash
# Patch deployment image
kubectl set image deployment/<deployment-name> <container-name>=<new-image> -n <namespace>

# Patch resource using JSON
kubectl patch pod <pod-name> -p '{"spec":{"terminationGracePeriodSeconds":0}}' -n <namespace>
```

### Label Management

```bash
# Label pod
kubectl label pod <pod-name> app=myapp -n <namespace>

# Remove label
kubectl label pod <pod-name> app- -n <namespace>

# Get resources by label
kubectl get pods -l app=myapp -n <namespace>
```

## K3s-Specific Notes

### K3s Cluster Access

If using K3s on Unraid via Docker or VM:

```bash
# SSH into Unraid
ssh root@unraid

# Access K3s cluster
kubectl --kubeconfig=/etc/rancher/k3s/k3s.yaml get nodes
```

### K3s Service Access

K3s services on NATed/internal networks require port-forwarding:

```bash
# Forward K3s API server
ssh -L 6443:localhost:6443 root@<k3s-server> -N

# Then use kubeconfig with localhost
kubectl --kubeconfig=~/.kube/config get nodes
```

### Lightweight and Quick

K3s is optimized for resource efficiency:

```bash
# Check resource usage on nodes
kubectl top nodes

# Monitor pod resource consumption
kubectl describe node <node-name> | grep -A 5 "Allocated resources"
```

## Useful Aliases

Add to shell profile for faster commands:

```bash
alias k='kubectl'
alias kgp='kubectl get pods'
alias kgd='kubectl get deployments'
alias kgs='kubectl get svc'
alias kdp='kubectl describe pod'
alias kl='kubectl logs'
alias kex='kubectl exec -it'
alias kaf='kubectl apply -f'
```

## Integration with Scripts

### Deploy and Monitor

```bash
#!/bin/bash

# Deploy application
kubectl apply -f deployment.yaml

# Wait for rollout
kubectl rollout status deployment/myapp -n default

# Port-forward for testing
kubectl port-forward svc/myapp 8080:80 &
```

### Health Check

```bash
#!/bin/bash
# Check cluster health
kubectl get nodes
echo "---"
kubectl get pods -A | grep -E "CrashLoop|Pending|Error"
```
