param(
    [string[]]$Hosts = @(),
    [string]$CertFile = "",
    [string]$KeyFile = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvDir = Join-Path $repoRoot ".venv"
$certDir = Join-Path $venvDir "certs"
New-Item -ItemType Directory -Path $certDir -Force | Out-Null

if (-not $CertFile) {
    $CertFile = Join-Path $certDir "dev-cert.pem"
}
if (-not $KeyFile) {
    $KeyFile = Join-Path $certDir "dev-key.pem"
}

if ($Hosts.Count -eq 0) {
    $Hosts = @("localhost", "127.0.0.1")
    $lanIps = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -ne "127.0.0.1" -and
            $_.PrefixOrigin -ne "WellKnown" -and
            $_.AddressState -eq "Preferred"
        } |
        Select-Object -ExpandProperty IPAddress -Unique
    if ($lanIps) {
        $Hosts += $lanIps
    }
}

$mkcert = Get-Command mkcert -ErrorAction SilentlyContinue
if ($mkcert) {
    Write-Output "Using mkcert..."
    & $mkcert.Source -cert-file $CertFile -key-file $KeyFile @Hosts
    Write-Output "Generated:"
    Write-Output "  $CertFile"
    Write-Output "  $KeyFile"
    exit 0
}

$openssl = Get-Command openssl -ErrorAction SilentlyContinue
if ($openssl) {
    Write-Output "Using openssl (self-signed)."

    $sanEntries = @()
    foreach ($dnsOrIp in $Hosts) {
        if ($dnsOrIp -match '^\d+\.\d+\.\d+\.\d+$') {
            $sanEntries += "IP:$dnsOrIp"
        }
        else {
            $sanEntries += "DNS:$dnsOrIp"
        }
    }
    $san = $sanEntries -join ","

    & $openssl.Source req `
        -x509 `
        -newkey rsa:2048 `
        -sha256 `
        -days 365 `
        -nodes `
        -keyout $KeyFile `
        -out $CertFile `
        -subj "/CN=localhost" `
        -addext "subjectAltName=$san"

    Write-Output "Generated:"
    Write-Output "  $CertFile"
    Write-Output "  $KeyFile"
    exit 0
}

Write-Error "Neither mkcert nor openssl is installed. Install mkcert (preferred) or openssl."
