# Codex Prompt: Create repo + project scaffolding for Local Voice Triage POC (whisper.cpp + RAG + workflows)

You are Codex acting as a senior engineer. Create a NEW repository with a clean, testable scaffolding for a local POC that uses PC mic/speakers (no telecoms). The system captures speech, transcribes via whisper.cpp, extracts identifiers/address/intent, then routes to either a local RAG answer flow or one of a few workflow stubs (move-of-house, electoral register, council tax manage).

## Non-negotiable goals
- Professional repo layout, clear separation of concerns, runnable on a dev PC.
- Fast to iterate: good defaults, scripts, tests, and a simple demo UI/CLI.
- Minimal vertical slices: RAG Q&A + Move-of-house workflow.
- Everything must run locally (LLM can be stubbed initially; RAG can use local docs).
- Provide a “happy path” demo that works end-to-end even with stubs.

## Tech choices (use these unless there is a strong reason not to)
- Language: Python 3.11+.
- Dependency manager: `uv` (preferred) with `pyproject.toml`.
- Tests: `pytest`.
- Formatting/lint/type-check: `ruff` + `mypy` (basic).
- Pre-commit: configured.
- Local storage: SQLite (sessions, cases).
- Audio capture: `sounddevice` (PortAudio) OR `pyaudio` (pick one, prefer `sounddevice`).
- VAD: simple energy-based or `webrtcvad` (optional, can be a stub).
- whisper.cpp integration: start with subprocess invocation of a local `whisper.cpp` binary (CLI).
- RAG: minimal vector store (FAISS or sqlite-based) + embeddings stub if needed; keep interface stable.
- TTS: optional; for POC just print responses. Provide an interface for later.

## Deliverables in this scaffold
1. Repo structure with modules, tests, docs, scripts.
2. A runnable demo command:
   - `uv run voice_triage demo`
   - Prompts user, records mic for a turn (push-to-talk or fixed duration), transcribes, extracts, routes to RAG or Move workflow, prints response + writes session to SQLite.
3. Stubs that are cleanly swappable:
   - `Extractor` (intent + field extraction)
   - `RagService`
   - `WorkflowHandlers`
   - `AsrClient` (whisper.cpp)
4. A clear README with setup steps and “how to run demo”.
5. A `Makefile` or `justfile` with common commands (format, lint, test, run).
6. CI config (GitHub Actions) running tests + lint.

## Repo name
- Create repository directory named: `voice-triage-poc`

## Directory layout (target)
- `voice_triage/`
  - `__init__.py`
  - `app/`
    - `demo.py`                 # CLI demo entrypoint
    - `orchestrator.py`         # state machine / routing
  - `audio/`
    - `capture.py`              # mic capture + segmentation
    - `vad.py`                  # optional / simple
  - `asr/`
    - `whispercpp.py`           # subprocess client
    - `types.py`
  - `nlu/`
    - `extractor.py`            # stub extractor interface + basic impl
    - `schemas.py`              # pydantic models or dataclasses
  - `rag/`
    - `index.py`                # index builder for local docs
    - `retrieve.py`
    - `answer.py`
    - `types.py`
  - `workflows/`
    - `move_home.py`
    - `electoral_register.py`   # stub
    - `council_tax.py`          # stub
    - `router.py`
  - `store/`
    - `db.py`                   # sqlite init + persistence
    - `models.py`
  - `util/`
    - `logging.py`
    - `config.py`
- `tests/`
  - `test_router.py`
  - `test_schemas.py`
  - `test_store.py`
  - `test_whispercpp_client.py` (mock subprocess)
- `docs/`
  - `ARCHITECTURE.md`
  - `DECISIONS.md`
- `scripts/`
  - `bootstrap_whispercpp.sh`   # optional helper notes; can be placeholder
- Root:
  - `pyproject.toml`
  - `.python-version` (optional)
  - `.gitignore`
  - `README.md`
  - `Makefile` (or `justfile`)
  - `.pre-commit-config.yaml`
  - `.github/workflows/ci.yml`

## Implementation details to include (scaffold-level, not full product)
### Orchestrator state machine (simple)
- Stages:
  - `ASK_ISSUE` (for RAG Q&A)
  - `ASK_CURRENT_ADDRESS` / `ASK_NEW_ADDRESS` / `ASK_MOVE_DATE` (for Move)
  - `CONFIRM` then `DONE`
- Routing rule:
  - If transcript contains “move”/“moving”/“new address” => Move workflow
  - Else => RAG_QA
- All extracted structured data goes into a single `CallSessionRecord`.

### ASR whisper.cpp client
- Config expects env var or config entry:
  - `WHISPERCPP_BIN=/path/to/main`
  - `WHISPERCPP_MODEL=/path/to/ggml-*.bin`
- Accept WAV path; return transcript text + minimal metadata.
- For tests, mock subprocess output.

### Audio capture
- Provide push-to-talk mode:
  - press ENTER to start recording, press ENTER to stop
  - save WAV to temp folder
- Keep it robust and minimal.

### NLU extractor stub
- Start with simple heuristic extraction:
  - UK postcode regex
  - detect intent keywords
  - address line as remainder text
- Provide interface to swap in LLM later (same output schema).

### RAG stub
- Provide an index builder:
  - reads `./kb/` folder (create empty with `.gitkeep`)
  - tokenizes into chunks
  - stores embeddings (can be random/stub) but keep retrieval API stable
- For demo, if KB empty, answer with “I don’t have that information in the KB yet.”

### Storage
- SQLite file: `./data/voice_triage.db` (auto-created)
- Tables:
  - `sessions` (id, started_at, transcript, extracted_json, route, outcome_json)

## Coding standards
- Keep files reasonably small, clear docstrings.
- Use typing everywhere; mypy should pass at least on core modules.
- Use `ruff` for formatting/lint.
- Provide a `logging` setup with structured-ish logs.

## Step-by-step tasks
1. Initialize git repo and scaffold directories/files above.
2. Create `pyproject.toml` with dependencies and tool configs:
   - ruff, mypy, pytest, sounddevice (or chosen audio lib), numpy, pydantic (optional), rich (optional)
3. Create CLI entry point:
   - `voice_triage` console script or `python -m voice_triage.app.demo`
4. Implement minimal working code path for demo:
   - record -> wav -> whisper.cpp -> extract -> route -> respond -> persist
   - If whisper.cpp missing, show a clear error message with setup instructions.
5. Add tests for:
   - router decisions
   - schema validation
   - db persistence (in-memory sqlite)
   - whisper client subprocess mocking
6. Add docs and README with exact commands.
7. Add CI workflow.

## Output requirements
- Write all new files with full contents.
- After writing files, provide:
  - file tree
  - exact run commands
  - any OS packages needed for audio library (brief)
- Do NOT implement a full production system; only scaffolding + working demo.

Begin now.