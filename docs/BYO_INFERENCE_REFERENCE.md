# BYO Inference Reference

This project supports a Bring-Your-Own (BYO) inference backend for RAG answer generation.

## Purpose

BYO inference lets teams plug in their own model service without changing:
- routing/state logic
- session storage
- web and REST API contracts

If BYO inference fails, the app automatically falls back to local RAG.

## Configuration

Set environment variables:

```text
VOICE_TRIAGE_INFERENCE_BACKEND=byo
VOICE_TRIAGE_BYO_INFERENCE_URL=http://127.0.0.1:9000/infer
VOICE_TRIAGE_BYO_INFERENCE_TIMEOUT_SECONDS=12
VOICE_TRIAGE_BYO_API_STYLE=generic
```

To keep these values in the project-local venv, write them to `.venv/.env`.

Supported API styles:
- `generic` (default): custom `{"query":"..."}` request with `{"answer":"..."}` response
- `openai`: OpenAI-compatible chat completions (works with Ollama OpenAI mode)

## Generic BYO Contract

Request (`POST`):

```json
{"query":"How do I order a garden waste bin?"}
```

Response:

```json
{
  "answer":"Garden waste is a paid subscription service.",
  "metadata":{"provider":"my-inference-service","model":"my-model-v1"}
}
```

Required fields:
- `answer` (string, non-empty)

Optional fields:
- `metadata` (object)

## OpenAI-Compatible (Ollama) Contract

Configuration example:

```text
VOICE_TRIAGE_INFERENCE_BACKEND=byo
VOICE_TRIAGE_BYO_API_STYLE=openai
VOICE_TRIAGE_BYO_INFERENCE_URL=http://127.0.0.1:11434/v1/chat/completions
VOICE_TRIAGE_BYO_MODEL=llama3.1:8b
VOICE_TRIAGE_BYO_API_KEY=
VOICE_TRIAGE_BYO_SYSTEM_PROMPT=You are a concise UK council support assistant.
```

Validation note:
- `VOICE_TRIAGE_BYO_INFERENCE_URL` must be an `http://` or `https://` URL with a host.

Request (`POST`):

```json
{
  "model":"llama3.1:8b",
  "messages":[
    {"role":"system","content":"You are a concise UK council support assistant."},
    {"role":"user","content":"How do I order a garden waste bin?"}
  ],
  "stream":false
}
```

Response (OpenAI-compatible):

```json
{
  "model":"llama3.1:8b",
  "choices":[
    {"message":{"role":"assistant","content":"Garden waste is a paid subscription service."}}
  ]
}
```

## Fallback Semantics

When BYO inference is unavailable or returns invalid payloads:
- local `SqliteRetriever + LocalRagService` is used
- response metadata includes:
  - `used_byo_inference: false`
  - `backend: "byo_with_local_fallback"`
  - `fallback_reason: <reason>`

## Integration Notes

- BYO endpoint should be low-latency to preserve conversational responsiveness.
- Keep response text concise; the same text is used for TTS playback.
- Do not return raw internal model traces to end users.

## Quick Smoke Test

1. Start your inference service on `http://127.0.0.1:9000/infer`.
2. Set env vars above.
3. Run:

```bash
uv run voice_triage api
```

4. Send a text turn through:
- `POST /api/v1/session/{session_id}/turn/text`

5. Verify response metadata indicates BYO backend usage.
