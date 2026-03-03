# Voice Triage POC

Local-first voice triage scaffold for a dev PC. You can run either:

- a local web app (`voice_triage web`) with start/stop mic controls and chat-style transcript/response display
- a terminal demo (`voice_triage demo`) for quick CLI checks

## What is implemented

- Python 3.11+ project managed with `uv`
- Local web server + UI: `uv run voice_triage web`
- REST API server (UI-independent): `uv run voice_triage api`
- Browser microphone capture with Start/Stop controls (no push-to-talk prompt)
- Per-turn ASR using local `whisper.cpp`
- Multi-turn conversation engine with routing and move-home state progression
- Heuristic extractor (intent + UK postcode + basic fields)
- Minimal RAG with sqlite-backed chunk index from `./kb`
- Optional BYO inference backend via REST (`VOICE_TRIAGE_INFERENCE_BACKEND=byo`)
- Workflow handlers (`move_home`, `electoral_register`, `council_tax` stubs)
- SQLite persistence for turns (`./data/voice_triage.db`)
- Tests with `pytest`
- Lint/type tooling (`ruff`, `mypy`) + pre-commit + GitHub Actions CI
- Developer references for REST API, BYO inference, and MCP under `docs/`

## Quickstart

1. Install Python 3.11+ and `uv`.
2. Create and activate a project-local virtual environment.

PowerShell:

```powershell
uv venv .venv
.\.venv\Scripts\Activate.ps1
```

Bash:

```bash
uv venv .venv
source .venv/bin/activate
```

3. Sync dependencies into `.venv`:

```bash
uv sync --dev
```

4. Bake runtime paths into `.venv/.env` (recommended):

```powershell
.\scripts\configure_venv_env.ps1 `
  -WhisperBin ".venv/tools/whispercpp/whisper-cli.exe" `
  -WhisperModel ".venv/tools/whispercpp/models/ggml-base.en.bin" `
  -WhisperUseGpu $true `
  -WhisperGpuLayers 60 `
  -WhisperThreads 6 `
  -WhisperTimeoutSeconds 45 `
  -InferenceBackend "local" `
  -ByoInferenceUrl "" `
  -ByoApiStyle "generic" `
  -ByoModel "" `
  -ByoApiKey "" `
  -ByoSystemPrompt "" `
  -PiperBin ".venv/tools/piper/piper.exe" `
  -PiperModel ".venv/tools/piper/models/en_GB-alba-medium.onnx" `
  -PiperDefaultVoiceId "en_GB-alba-medium" `
  -WebHost "0.0.0.0" `
  -WebPort 8443 `
  -SslCertFile ".venv/certs/dev-cert.pem" `
  -SslKeyFile ".venv/certs/dev-key.pem"
```

This writes `.venv/.env` (project-local), and the app auto-loads it.

5. Generate TLS certs (required for LAN browser mic access):

```powershell
.\scripts\generate_dev_tls_cert.ps1
```

By default this includes `localhost`, `127.0.0.1`, and detected LAN IPv4 addresses.

6. (Optional) Keep tools inside `.venv` for fully self-contained local runtime:

- whisper.cpp binary: `.venv/tools/whispercpp/whisper-cli.exe` (or `.venv/tools/whispercpp/main.exe`)
- whisper model: `.venv/tools/whispercpp/models/ggml-base.en.bin`
- piper binary: `.venv/tools/piper/piper.exe`
- piper model: `.venv/tools/piper/models/en_GB-northern_english_male-medium.onnx`
  - any additional `*.onnx` files in `.venv/tools/piper/models` appear in the web voice dropdown
  - default web voice can be set with `PIPER_DEFAULT_VOICE_ID` (defaults to `en_GB-alba-medium`)

7. (Optional) Add local KB files under `./kb/*.md` or `./kb/*.txt`.

## Run local website

Start server:

```bash
uv run voice_triage web --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

The web UI now uses the versioned REST surface under `/api/v1/*`.

For LAN access:

```bash
uv run voice_triage web --host 0.0.0.0 --port 8443 --ssl-certfile .venv/certs/dev-cert.pem --ssl-keyfile .venv/certs/dev-key.pem
```

Then browse from another device on your LAN:

```text
https://<your-pc-lan-ip>:8443
```

## Run REST API only

```bash
uv run voice_triage api --host 127.0.0.1 --port 8000 --no-ssl
```

Useful endpoints:

- `POST /api/v1/session`
- `POST /api/v1/session/{session_id}/turn` (audio upload)
- `POST /api/v1/session/{session_id}/turn/text` (pre-transcribed text)
- `GET /api/v1/voices`
- `POST /api/v1/session/{session_id}/voice`
- `GET /api/v1/tts/{audio_id}`

Important for browser microphone access:

- Many browsers block `getUserMedia` on plain `http://<lan-ip>`.
- `localhost` is usually allowed without HTTPS, but LAN IPs usually require HTTPS.
- For LAN clients, use HTTPS with a cert that includes your LAN IP in SANs.

Web flow:

1. Click `Start Listening`
2. Speak naturally
3. The browser VAD auto-detects end-of-turn silence and sends the turn
4. See:
   - user transcript (what ASR heard)
   - assistant response
   - assistant audio playback (Piper)
   - selectable Piper voice (dropdown)
5. The app keeps listening for the next turn; click `Stop Listening` to end hands-free mode

## CLI demo (legacy)

```bash
uv run voice_triage demo
```

## Optional MCP server

Run MCP stdio server:

```bash
uv run voice_triage mcp
```

If MCP SDK is missing, install optional dependency:

```bash
uv add --optional mcp "mcp>=1.0.0"
```

## Common commands

```bash
make sync
make format
make lint
make typecheck
make docstrings
make test
make demo
make web
make api
make web-lan
make stop-web
make cert-dev
make web-ssl
```

## Developer references

- REST API reference: `docs/API_REFERENCE.md`
- BYO inference reference: `docs/BYO_INFERENCE_REFERENCE.md`
- MCP reference: `docs/MCP_REFERENCE.md`

## Audio prerequisites (brief)

- Ubuntu/Debian: `sudo apt-get install -y portaudio19-dev`
- macOS: `brew install portaudio`
- Windows: no extra package is usually needed when using standard Python wheels.

## CUDA acceleration for whisper.cpp

For faster STT turn latency on NVIDIA GPUs, use a CUDA-enabled `whisper.cpp` build and set:

```text
WHISPERCPP_USE_GPU=1
WHISPERCPP_GPU_LAYERS=60
WHISPERCPP_THREADS=6
WHISPERCPP_TIMEOUT_SECONDS=45
```

Notes:

- Increase `WHISPERCPP_GPU_LAYERS` toward `99` if VRAM allows.
- If your build fails with GPU flags, set `WHISPERCPP_USE_GPU=0`.
- You can pass additional whisper CLI flags via `WHISPERCPP_EXTRA_ARGS` in `.venv/.env`.

## BYO inference backend

Set:

```text
VOICE_TRIAGE_INFERENCE_BACKEND=byo
VOICE_TRIAGE_BYO_INFERENCE_URL=http://localhost:9000/infer
VOICE_TRIAGE_BYO_INFERENCE_TIMEOUT_SECONDS=12
VOICE_TRIAGE_BYO_API_STYLE=generic
```

Expected BYO endpoint request payload:

```json
{"query":"How do I order a garden waste bin?"}
```

Expected response payload:

```json
{"answer":"...", "metadata":{"provider":"my-model"}}
```

Ollama (OpenAI-compatible) example:

```text
VOICE_TRIAGE_INFERENCE_BACKEND=byo
VOICE_TRIAGE_BYO_API_STYLE=openai
VOICE_TRIAGE_BYO_INFERENCE_URL=http://127.0.0.1:11434/v1/chat/completions
VOICE_TRIAGE_BYO_MODEL=llama3.1:8b
VOICE_TRIAGE_BYO_INFERENCE_TIMEOUT_SECONDS=20
VOICE_TRIAGE_BYO_API_KEY=
```

When BYO is unavailable, local RAG fallback is used automatically.

## Notes

- If `./kb` has no indexed chunks, RAG answers with: `I don't have that information in the KB yet.`
- Browser mic recording requires microphone permission for `localhost`.
- If Piper is not configured, text responses still work and UI shows a TTS error message.
- If LAN clients cannot connect, allow inbound TCP `8443` in Windows Firewall.
- If Ctrl+C fails in one terminal, run `uv run voice_triage stop-web` from another terminal.
