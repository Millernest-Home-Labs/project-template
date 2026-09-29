# namecheap.ps1 — call the Namecheap API using credentials from the k3s cluster.
#
# Usage:
#   .\namecheap.ps1 -Command namecheap.domains.dns.custom -Params @{ sld='millernest'; tdn='com' }
#   .\namecheap.ps1 -Command namecheap.domains.dns.host.create -Params @{
#       sld='millernest'; tdn='com'; host='api.reflexia'; ip='99.129.41.20'; type='A'; ttl='600' }
#
# Reads username, password, api_user, api_key from the k3s secret `namecheap-login`
# (namespace default), computes the API hash, calls the API, and prints the raw XML
# response plus a status line. Never prints the credential values.
param(
    [Parameter(Mandatory)][string]$Command,
    [hashtable]$Params = @{}
)
$ErrorActionPreference = 'Stop'

$secret = kubectl get secret namecheap-login -n default -o json | ConvertFrom-Json
function Dec([string]$b64) { [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b64)) }
$username = Dec $secret.data.username
$password = Dec $secret.data.password
$apiUser  = Dec $secret.data.api_user
$apiKey   = Dec $secret.data.api_key

$timestamp = [DateTimeOffset]::Now.ToUnixTimeSeconds()

# Hash = md5( username + command + apikey + apiuser + sortedParams + timestamp ), lowercased.
$paramStr = (($Params.GetEnumerator() | Sort-Object Name) | ForEach-Object { $_.Name + $_.Value }) -join ''
$hashInput = ($username + $Command + $apiKey + $apiUser + $paramStr + $timestamp).ToLower()
$md5 = [System.Security.Cryptography.MD5]::Create()
$hash = -join ($md5.ComputeHash([Text.Encoding]::UTF8.GetBytes($hashInput)) | ForEach-Object { $_.ToString('x2') })

$q = [ordered]@{
    api_user  = $apiUser
    api_key   = $apiKey
    username  = $username
    password  = $password
    command   = $Command
    hash      = $hash
    timestamp = $timestamp
}
foreach ($k in ($Params.Keys | Sort-Object)) { $q[$k] = [string]$Params[$k] }
$qs = (($q.GetEnumerator() | ForEach-Object {
    [uri]::EscapeDataString($_.Name) + '=' + [uri]::EscapeDataString([string]$_.Value)
}) -join '&')

$resp = Invoke-WebRequest -Uri ("https://api.namecheap.com/xml.response?" + $qs) -Method Get
$xml = [xml]$resp.Content
$apiStatus = $xml.NamecheapApiResponse.Status
$cmdStatus = $xml.NamecheapApiResponse.Commands.Command.Status
Write-Output "API_STATUS=$apiStatus COMMAND_STATUS=$cmdStatus"
Write-Output $resp.Content
