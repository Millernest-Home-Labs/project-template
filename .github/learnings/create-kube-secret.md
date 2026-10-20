# Create Secrets In Kubectl

```
kubectl -n default create secret generic rancher-login --from-literal=username="YOUR_USERNAME" --from-literal=password="YOUR_PASSWORD"
```

```plaintext
kubectl -n default create secret generic github-token --from-literal=GH_TOKEN="YOUR_GITHUB_TOKEN"

```
