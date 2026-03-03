# Contributing To Voice Triage POC

Thanks for contributing.

This repository is a local-first voice triage proof of concept. Contributions should favor:
- small, testable changes
- predictable behavior
- easy review and rollback

## Project Scope

Primary stack:
- Python 3.11+
- `uv` for env/dependencies
- FastAPI web server + static frontend
- `whisper.cpp` (ASR) and Piper (TTS) via subprocess
- sqlite for persistence and RAG index

Please avoid assumptions from other projects or hardware stacks.

## Development Setup

```bash
uv venv .venv
uv sync --dev
```

Run locally:

```bash
uv run voice_triage web
```

## Contribution Principles

1. Keep PRs focused
- One bug/feature per PR.
- Do not mix behavior changes with broad refactors.

2. Minimize blast radius
- Touch only required files/functions.
- Avoid unrelated formatting or cleanup churn.

3. Preserve established behavior
- Do not alter unrelated routes/flows.
- Keep existing APIs stable unless change is required and documented.

4. Be explicit about risk
- Call out behavior changes, limitations, and follow-ups in PR notes.

## Code Quality Requirements

Before opening a PR, all must pass:

```bash
uv run ruff check .
uv run mypy voice_triage
uv run interrogate --config pyproject.toml voice_triage
uv run pytest -q
```

## Testing Requirements

Update/add targeted tests for changed behavior.

Expected test coverage by change type:
- Conversation/routing/state changes: `tests/test_conversation_engine.py`, `tests/test_router.py`
- Extractor parsing changes: `tests/test_extractor.py`
- RAG behavior changes: `tests/test_rag_retrieval.py`
- ASR/TTS subprocess changes: `tests/test_whispercpp_client.py`, `tests/test_piper_client.py`
- Voice discovery/default changes: `tests/test_voice_discovery.py`
- Store/schema changes: `tests/test_store.py`, `tests/test_schemas.py`

Required for API-facing changes:
- Add/update E2E HTTP tests that exercise affected endpoints end-to-end.
- Include at minimum relevant flows across:
  - session creation
  - turn submission
  - voice selection
  - TTS audio fetch (when applicable)

## Docs Requirements

If behavior/configuration changes, update docs in the same PR:
- `README.md`
- `AGENTS.md`
- any script usage examples affected by env var defaults

## PR Checklist

- [ ] PR scope is focused and intentional.
- [ ] Changed behavior is covered by targeted tests.
- [ ] E2E HTTP tests are added/updated for changed API behavior.
- [ ] `uv run ruff check .` passes.
- [ ] `uv run mypy voice_triage` passes.
- [ ] `uv run interrogate --config pyproject.toml voice_triage` passes.
- [ ] `uv run pytest -q` passes.
- [ ] Relevant docs (`README.md`, `AGENTS.md`) are updated.
