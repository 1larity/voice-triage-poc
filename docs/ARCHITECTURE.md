# Architecture

## Overview

The POC can run as either a CLI loop or a local web app. The primary interaction path is now the web app:

1. Browser captures microphone audio (Start/Stop) and uploads WAV.
2. `asr.whispercpp` calls local `whisper.cpp` and returns transcript text.
3. `app.conversation` extracts intent/fields and advances session state.
4. Route is handled by either:
   - RAG QA (`rag.answer` + sqlite retriever)
   - Move-home workflow state machine
   - Stub workflow handlers for electoral register / council tax
5. Assistant response text is synthesized to WAV via local Piper CLI (`tts.piper`).
6. Turn is persisted in sqlite via `store.db`.
7. UI displays transcript + assistant response in a chat-like timeline and auto-plays TTS audio.

## Web stack

- FastAPI app: `voice_triage.web.server`
- Static UI assets: `voice_triage/web/static/`
- Launch command: `uv run voice_triage web --host 127.0.0.1 --port 8000`

## Conversation state machine

Move-home route stages:

- `ASK_CURRENT_ADDRESS`
- `ASK_NEW_ADDRESS`
- `ASK_MOVE_DATE`
- `CONFIRM`
- `DONE`

RAG route stage:

- `ASK_ISSUE` (per turn)

## Data persistence

SQLite file: `./data/voice_triage.db`

Table `sessions`:

- `id`
- `started_at`
- `transcript`
- `extracted_json`
- `route`
- `outcome_json`

Each web turn writes one session-row record including route metadata and assistant response details.

## RAG storage

RAG chunks/embeddings are stored in sqlite (`./data/rag_index.db`) with deterministic stub embeddings for stable retrieval behavior while keeping API boundaries intact.
