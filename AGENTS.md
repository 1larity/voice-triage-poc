# AGENTS.md

Guidance for AI coding agents working in `voice-triage-poc`.

## Project Intent

This repository is a local-first voice triage POC for council-style interactions.

Core principles:
- Everything runs locally on a dev PC.
- Keep behavior deterministic and easy to debug.
- Prefer simple, swappable interfaces over deeply coupled implementations.

## Runtime Overview

- Backend: FastAPI (`voice_triage/web/server.py`)
- Frontend: static HTML/CSS/JS (`voice_triage/web/static/*`)
- ASR: `whisper.cpp` CLI wrapper (`voice_triage/asr/whispercpp.py`)
- TTS: Piper CLI wrapper (`voice_triage/tts/piper.py`)
- NLU: heuristic extractor (`voice_triage/nlu/extractor.py`)
- Routing/state machine: conversation engine (`voice_triage/app/conversation.py`)
- RAG: sqlite index/retrieval/answer (`voice_triage/rag/*`)
- Persistence: sqlite session store (`voice_triage/store/*`)

## Environment And Tooling

- Python: `3.11+`
- Dependency manager: `uv`
- Tests: `pytest`
- Lint/format: `ruff`
- Type checks: `mypy`

Use project-local virtual env only (`.venv`).

## Required Commands

```bash
# install/update deps
uv sync --dev

# lint
uv run ruff check .

# typecheck
uv run mypy voice_triage

# tests
uv run pytest -q
```

For local run:

```bash
uv run voice_triage web
```

## Configuration Conventions

Config is loaded from:
1. process environment
2. `.venv/.env`
3. `.env`

Do not hardcode machine-specific absolute paths in source.

Important env vars:
- `WHISPERCPP_BIN`, `WHISPERCPP_MODEL`
- `WHISPERCPP_USE_GPU`, `WHISPERCPP_GPU_LAYERS`, `WHISPERCPP_THREADS`
- `PIPER_BIN`, `PIPER_MODEL`, `PIPER_DEFAULT_VOICE_ID`
- `VOICE_TRIAGE_SSL_CERTFILE`, `VOICE_TRIAGE_SSL_KEYFILE`

## Behavioral Invariants

### Web Conversation Loop
- In continuous mode, do not restart microphone capture until assistant TTS playback has ended.
- Avoid assistant-audio feedback loops (self-transcription) when hands-free is enabled.
- Keep start/stop behavior predictable and recoverable after errors.

### Move-Home Workflow
- Confirm captured current/new address explicitly.
- If postcode is missing, prompt for postcode before proceeding.
- Persist captured data into `outcome.captured_data` for UI/API visibility.
- Confirmation prompts should read naturally and be easy for STT to parse.

### Date Handling
- Support ISO and common spoken UK formats (for example `4th of April 2026`).
- Normalize accepted move dates to `YYYY-MM-DD`.

### RAG Responses
- Return concise user-facing answers, not raw KB schema text dumps.
- Avoid low-relevance hallucinated matches; fail gracefully with KB-missing message.

## Coding Guidelines

- Keep changes scoped to the user’s request; avoid unrelated refactors.
- Preserve stable public interfaces unless change is required.
- Use clear typing for new/modified Python functions.
- Prefer small helper methods over large monolithic logic blocks.
- Keep web UI logic explicit; avoid hidden state transitions.
- Do not introduce network dependencies for core runtime paths.

## Testing Expectations

For behavior changes, add/update targeted tests in `tests/`:
- Router and conversation-stage regressions
- Extractor parsing (postcodes, dates, intents)
- ASR/TTS subprocess behavior via mocks
- Voice discovery/default selection behavior
- RAG retrieval/answer quality checks
- E2E HTTP tests for affected API flows (session create, turn submit, voice select, TTS fetch)

Minimum before handoff:
- `ruff`, `mypy`, and `pytest` all pass locally.
- Docstring coverage is `100%` for `voice_triage` (`uv run interrogate --config pyproject.toml voice_triage`).

## Safety And Operational Notes

- Never commit secrets, cert private keys, or machine-local credentials.
- Treat `.venv/.env` as local runtime config; do not assume it exists in CI.
- Keep Windows compatibility intact (paths, process handling, CLI behavior).
- For server shutdown/stop behavior, avoid orphan/zombie processes.

## PR/Change Checklist

- [ ] Change is scoped and directly addresses the issue.
- [ ] Updated tests cover the new/changed behavior.
- [ ] E2E HTTP tests are added/updated for any changed API behavior.
- [ ] `uv run ruff check .` passes.
- [ ] `uv run mypy voice_triage` passes.
- [ ] `uv run interrogate --config pyproject.toml voice_triage` passes.
- [ ] `uv run pytest -q` passes.
- [ ] README/docs updated if user-visible behavior or config changed.
