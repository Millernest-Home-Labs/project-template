#!/usr/bin/env bash
# namecheap.sh — call the Namecheap API using credentials from the k3s cluster.
#
# Usage:
#   ./namecheap.sh namecheap.domains.dns.custom sld=millernest tdn=com
#   ./namecheap.sh namecheap.domains.dns.host.create sld=millernest tdn=com \
#       host=api.reflexia ip=99.129.41.20 type=A ttl=600
#
# Reads username, password, api_user, api_key from the k3s secret `namecheap-login`
# (namespace default), computes the API hash, calls the API, and prints the raw XML
# response. Never prints the credential values.
#
# Dependencies: kubectl, jq, python3, curl.
# On OpenClaw: KUBECONFIG=/appdata/kube/config, kubectl at /appdata/bin/kubectl.
set -euo pipefail

COMMAND="$1"; shift

secret_json=$(kubectl get secret namecheap-login -n default -o json)
jget() { echo "$secret_json" | jq -r ".data.$1" | base64 -d; }
username=$(jget username)
password=$(jget password)
api_user=$(jget api_user)
api_key=$(jget api_key)

timestamp=$(date +%s)

declare -A params
for kv in "$@"; do
  k="${kv%%=*}"; v="${kv#*=}"
  params["$k"]="$v"
done

# Sorted param string (name+value concatenated, sorted by name).
param_str=""
sorted_keys=()
if [ ${#params[@]} -gt 0 ]; then
  while IFS= read -r k; do sorted_keys+=("$k"); done < <(printf '%s\n' "${!params[@]}" | sort)
  for k in "${sorted_keys[@]}"; do param_str+="${k}${params[$k]}"; done
fi

# Hash = md5( username + command + apikey + apiuser + sortedParams + timestamp ), lowercased.
hash_input="${username}${COMMAND}${api_key}${api_user}${param_str}${timestamp}"
hash_input=$(printf '%s' "$hash_input" | tr '[:upper:]' '[:lower:]')
hash=$(printf '%s' "$hash_input" | md5sum | awk '{print $1}')

urlencode() { python3 -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$1"; }

qs="api_user=$(urlencode "$api_user")&api_key=$(urlencode "$api_key")&username=$(urlencode "$username")&password=$(urlencode "$password")&command=$(urlencode "$COMMAND")&hash=$(urlencode "$hash")&timestamp=$(urlencode "$timestamp")"
for k in "${sorted_keys[@]}"; do
  qs+="&$(urlencode "$k")=$(urlencode "${params[$k]}")"
done

curl -s "https://api.namecheap.com/xml.response?${qs}"
