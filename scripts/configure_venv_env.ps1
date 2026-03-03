param(
    [string]$WhisperBin = "",
    [string]$WhisperModel = "",
    [bool]$WhisperUseGpu = $false,
    [int]$WhisperGpuLayers = 60,
    [int]$WhisperThreads = 0,
    [double]$WhisperTimeoutSeconds = 45.0,
    [string]$WhisperExtraArgs = "",
    [ValidateSet("local", "byo")]
    [string]$InferenceBackend = "local",
    [string]$ByoInferenceUrl = "",
    [double]$ByoInferenceTimeoutSeconds = 12.0,
    [ValidateSet("generic", "openai")]
    [string]$ByoApiStyle = "generic",
    [string]$ByoModel = "",
    [string]$ByoApiKey = "",
    [string]$ByoSystemPrompt = "",
    [string]$PiperBin = "",
    [string]$PiperModel = "",
    [string]$PiperDefaultVoiceId = "en_GB-alba-medium",
    [double]$PiperTimeoutSeconds = 30.0,
    [string]$SslCertFile = "",
    [string]$SslKeyFile = "",
    [string]$WebHost = "0.0.0.0",
    [int]$WebPort = 8443
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvDir = Join-Path $repoRoot ".venv"
$envPath = Join-Path $venvDir ".env"

if (-not (Test-Path $venvDir)) {
    Write-Error ".venv not found. Run 'uv venv .venv' first."
}

function Convert-ToRepoRelative {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathValue
    )
    if (-not $PathValue) {
        return $PathValue
    }

    $candidate = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $PathValue))
    $rootFull = [System.IO.Path]::GetFullPath($repoRoot)

    if ($candidate.StartsWith($rootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        $rootUri = New-Object System.Uri(($rootFull.TrimEnd("\") + "\"))
        $candidateUri = New-Object System.Uri($candidate)
        $relativeUri = $rootUri.MakeRelativeUri($candidateUri)
        $relative = [System.Uri]::UnescapeDataString($relativeUri.ToString())
        return ($relative -replace "\\", "/")
    }

    return ($PathValue -replace "\\", "/")
}

if (-not $WhisperBin) {
    $whisperCandidates = @(
        ".venv/tools/whispercpp/Release/whisper-cli.exe",
        ".venv/tools/whispercpp/Release/main.exe",
        ".venv/tools/whispercpp/build/bin/whisper-cli.exe",
        ".venv/tools/whispercpp/build/bin/main.exe",
        ".venv/tools/whispercpp/whisper-cli.exe",
        ".venv/tools/whispercpp/main.exe"
    )
    foreach ($candidate in $whisperCandidates) {
        if (Test-Path (Join-Path $repoRoot $candidate)) {
            $WhisperBin = $candidate
            break
        }
    }
    if (-not $WhisperBin) {
        $WhisperBin = ".venv/tools/whispercpp/whisper-cli.exe"
    }
}
if (-not $WhisperModel) {
    $WhisperModel = ".venv/tools/whispercpp/models/ggml-base.en.bin"
}
if (-not $PiperBin) {
    $venvPiperScript = ".venv/Scripts/piper.exe"
    if (Test-Path (Join-Path $repoRoot $venvPiperScript)) {
        $PiperBin = $venvPiperScript
    }
    else {
        $PiperBin = ".venv/tools/piper/piper.exe"
    }
}
if (-not $PiperModel) {
    $PiperModel = ".venv/tools/piper/models/voice.onnx"
}
if (-not $SslCertFile) {
    $SslCertFile = ".venv/certs/dev-cert.pem"
}
if (-not $SslKeyFile) {
    $SslKeyFile = ".venv/certs/dev-key.pem"
}

$WhisperBin = Convert-ToRepoRelative -PathValue $WhisperBin
$WhisperModel = Convert-ToRepoRelative -PathValue $WhisperModel
$PiperBin = Convert-ToRepoRelative -PathValue $PiperBin
$PiperModel = Convert-ToRepoRelative -PathValue $PiperModel
$SslCertFile = Convert-ToRepoRelative -PathValue $SslCertFile
$SslKeyFile = Convert-ToRepoRelative -PathValue $SslKeyFile

$content = @(
    "# Local venv-bound config for voice-triage-poc"
    "WHISPERCPP_BIN=$WhisperBin"
    "WHISPERCPP_MODEL=$WhisperModel"
    "WHISPERCPP_USE_GPU=$([int]$WhisperUseGpu)"
    "WHISPERCPP_GPU_LAYERS=$WhisperGpuLayers"
    "WHISPERCPP_THREADS=$WhisperThreads"
    "WHISPERCPP_TIMEOUT_SECONDS=$WhisperTimeoutSeconds"
    "WHISPERCPP_EXTRA_ARGS=$WhisperExtraArgs"
    "VOICE_TRIAGE_INFERENCE_BACKEND=$InferenceBackend"
    "VOICE_TRIAGE_BYO_INFERENCE_URL=$ByoInferenceUrl"
    "VOICE_TRIAGE_BYO_INFERENCE_TIMEOUT_SECONDS=$ByoInferenceTimeoutSeconds"
    "VOICE_TRIAGE_BYO_API_STYLE=$ByoApiStyle"
    "VOICE_TRIAGE_BYO_MODEL=$ByoModel"
    "VOICE_TRIAGE_BYO_API_KEY=$ByoApiKey"
    "VOICE_TRIAGE_BYO_SYSTEM_PROMPT=$ByoSystemPrompt"
    "PIPER_BIN=$PiperBin"
    "PIPER_MODEL=$PiperModel"
    "PIPER_DEFAULT_VOICE_ID=$PiperDefaultVoiceId"
    "PIPER_TIMEOUT_SECONDS=$PiperTimeoutSeconds"
    "VOICE_TRIAGE_SSL_CERTFILE=$SslCertFile"
    "VOICE_TRIAGE_SSL_KEYFILE=$SslKeyFile"
    "VOICE_TRIAGE_WEB_HOST=$WebHost"
    "VOICE_TRIAGE_WEB_PORT=$WebPort"
)

Set-Content -Path $envPath -Value $content -Encoding utf8
Write-Output "Wrote $envPath"
