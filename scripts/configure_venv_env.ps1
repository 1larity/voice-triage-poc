param(
    [string]$WhisperBin = "",
    [string]$WhisperModel = "",
    [bool]$WhisperUseGpu = $false,
    [int]$WhisperGpuLayers = 60,
    [int]$WhisperThreads = 0,
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

if (-not $WhisperBin) {
    $whisperCli = Join-Path $venvDir "tools\\whispercpp\\whisper-cli.exe"
    if (Test-Path $whisperCli) {
        $WhisperBin = $whisperCli
    }
    else {
        $WhisperBin = Join-Path $venvDir "tools\\whispercpp\\main.exe"
    }
}
if (-not $WhisperModel) {
    $WhisperModel = Join-Path $venvDir "tools\\whispercpp\\models\\ggml-base.en.bin"
}
if (-not $PiperBin) {
    $PiperBin = Join-Path $venvDir "tools\\piper\\piper.exe"
}
if (-not $PiperModel) {
    $PiperModel = Join-Path $venvDir "tools\\piper\\models\\voice.onnx"
}
if (-not $SslCertFile) {
    $SslCertFile = Join-Path $venvDir "certs\\dev-cert.pem"
}
if (-not $SslKeyFile) {
    $SslKeyFile = Join-Path $venvDir "certs\\dev-key.pem"
}

$content = @(
    "# Local venv-bound config for voice-triage-poc"
    "WHISPERCPP_BIN=$WhisperBin"
    "WHISPERCPP_MODEL=$WhisperModel"
    "WHISPERCPP_USE_GPU=$([int]$WhisperUseGpu)"
    "WHISPERCPP_GPU_LAYERS=$WhisperGpuLayers"
    "WHISPERCPP_THREADS=$WhisperThreads"
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
    "VOICE_TRIAGE_SSL_CERTFILE=$SslCertFile"
    "VOICE_TRIAGE_SSL_KEYFILE=$SslKeyFile"
    "VOICE_TRIAGE_WEB_HOST=$WebHost"
    "VOICE_TRIAGE_WEB_PORT=$WebPort"
)

Set-Content -Path $envPath -Value $content -Encoding utf8
Write-Output "Wrote $envPath"
