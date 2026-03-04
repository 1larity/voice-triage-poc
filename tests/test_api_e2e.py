from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from voice_triage.http.rest import create_rest_app


def _configure_test_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    kb_dir = tmp_path / "kb"
    models_dir = tmp_path / "models"
    data_dir.mkdir(parents=True, exist_ok=True)
    kb_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)
    piper_model = models_dir / "en_GB-alba-medium.onnx"
    piper_model.write_text("x", encoding="utf-8")
    (kb_dir / "bins.md").write_text(
        "Garden waste collection is a paid subscription service.", encoding="utf-8"
    )

    monkeypatch.setenv("VOICE_TRIAGE_DATA_DIR", str(data_dir))
    monkeypatch.setenv("VOICE_TRIAGE_DB", str(data_dir / "voice_triage.db"))
    monkeypatch.setenv("VOICE_TRIAGE_RAG_INDEX", str(data_dir / "rag_index.db"))
    monkeypatch.setenv("VOICE_TRIAGE_KB_DIR", str(kb_dir))
    monkeypatch.setenv("PIPER_MODEL", str(piper_model))
    monkeypatch.setenv("PIPER_DEFAULT_VOICE_ID", "en_GB-alba-medium")
    monkeypatch.setenv("PIPER_BIN", str(tmp_path / "missing_piper.exe"))
    monkeypatch.setenv("VOICE_TRIAGE_INFERENCE_BACKEND", "local")
    return data_dir


def test_rest_api_session_text_turn_voice_and_tts_routes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    data_dir = _configure_test_env(monkeypatch, tmp_path)
    client = TestClient(create_rest_app())

    reindex_response = client.post("/api/v1/reindex")
    assert reindex_response.status_code == 200
    reindex_payload = reindex_response.json()
    assert reindex_payload["chunk_count"] > 0
    assert reindex_payload["kb_file_count"] > 0
    assert reindex_payload["index_path"].endswith("rag_index.db")

    config_response = client.get("/api/v1/config")
    assert config_response.status_code == 200
    config_payload = config_response.json()
    assert config_payload["vad_rms_threshold"] > 0
    assert config_payload["vad_max_turn_ms"] >= 1000

    create_response = client.post("/api/v1/session")
    assert create_response.status_code == 200
    create_payload = create_response.json()
    session_id = create_payload["session_id"]
    assert create_payload["selected_voice_id"] == "en_GB-alba-medium"

    voices_response = client.get("/api/v1/voices")
    assert voices_response.status_code == 200
    voices_payload = voices_response.json()
    assert voices_payload["default_voice_id"] == "en_GB-alba-medium"
    assert any(item["voice_id"] == "en_GB-alba-medium" for item in voices_payload["voices"])

    select_voice_response = client.post(
        f"/api/v1/session/{session_id}/voice", json={"voice_id": "en_GB-alba-medium"}
    )
    assert select_voice_response.status_code == 200
    assert select_voice_response.json()["voice_id"] == "en_GB-alba-medium"

    turn_response = client.post(
        f"/api/v1/session/{session_id}/turn/text",
        json={"transcript": "How do I order a garden waste bin?"},
    )
    assert turn_response.status_code == 200
    turn_payload = turn_response.json()
    assert turn_payload["session_id"] == session_id
    assert turn_payload["assistant_response"]
    assert turn_payload["route"] in {"RAG_QA", "MOVE_HOME", "ELECTORAL_REGISTER", "COUNCIL_TAX"}

    tts_dir = data_dir / "tmp_tts"
    tts_dir.mkdir(parents=True, exist_ok=True)
    audio_id = "manual_e2e_audio"
    (tts_dir / f"{audio_id}.wav").write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")

    tts_fetch_response = client.get(f"/api/v1/tts/{audio_id}")
    assert tts_fetch_response.status_code == 200
    assert tts_fetch_response.headers["content-type"] == "audio/wav"


def test_rest_api_rejects_oversized_audio_upload(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_test_env(monkeypatch, tmp_path)
    monkeypatch.setenv("VOICE_TRIAGE_MAX_AUDIO_UPLOAD_BYTES", "128")

    client = TestClient(create_rest_app())
    create_response = client.post("/api/v1/session")
    session_id = create_response.json()["session_id"]

    audio_bytes = b"RIFF" + (b"\x00" * 2048)
    turn_response = client.post(
        f"/api/v1/session/{session_id}/turn",
        files={"audio": ("turn.wav", audio_bytes, "audio/wav")},
    )

    assert turn_response.status_code == 413
    assert "exceeds max allowed size" in turn_response.text


def test_rest_api_rejects_too_long_transcript(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_test_env(monkeypatch, tmp_path)
    monkeypatch.setenv("VOICE_TRIAGE_MAX_TRANSCRIPT_CHARS", "32")

    client = TestClient(create_rest_app())
    create_response = client.post("/api/v1/session")
    session_id = create_response.json()["session_id"]

    long_text = "a" * 100
    turn_response = client.post(
        f"/api/v1/session/{session_id}/turn/text",
        json={"transcript": long_text},
    )

    assert turn_response.status_code == 422
    assert "exceeds max length" in turn_response.text


def test_rest_api_rejects_whitespace_padded_raw_transcript(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_test_env(monkeypatch, tmp_path)
    monkeypatch.setenv("VOICE_TRIAGE_MAX_TRANSCRIPT_CHARS", "32")

    client = TestClient(create_rest_app())
    create_response = client.post("/api/v1/session")
    session_id = create_response.json()["session_id"]

    padded_text = "a" + (" " * 200)
    turn_response = client.post(
        f"/api/v1/session/{session_id}/turn/text",
        json={"transcript": padded_text},
    )

    assert turn_response.status_code == 422
    assert "exceeds max length" in turn_response.text


def test_rest_api_rejects_non_alphanumeric_transcript(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_test_env(monkeypatch, tmp_path)

    client = TestClient(create_rest_app())
    create_response = client.post("/api/v1/session")
    session_id = create_response.json()["session_id"]

    turn_response = client.post(
        f"/api/v1/session/{session_id}/turn/text",
        json={"transcript": ".... !!! ???"},
    )

    assert turn_response.status_code == 422
    assert "alphanumeric" in turn_response.text


def test_rest_api_reindex_rate_limit_returns_429(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_test_env(monkeypatch, tmp_path)
    monkeypatch.setenv("VOICE_TRIAGE_REINDEX_MIN_INTERVAL_SECONDS", "60")

    client = TestClient(create_rest_app())
    first = client.post("/api/v1/reindex")
    assert first.status_code == 200

    second = client.post("/api/v1/reindex")
    assert second.status_code == 429
    assert "Retry-After" in second.headers


def test_rest_api_reindex_runtime_conflict_maps_to_409(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_test_env(monkeypatch, tmp_path)
    monkeypatch.setenv("VOICE_TRIAGE_REINDEX_MIN_INTERVAL_SECONDS", "60")

    client = TestClient(create_rest_app())

    import voice_triage.rag.index as rag_index

    original_build_index = rag_index.build_index

    def _raise_in_progress(*args: object, **kwargs: object) -> int:
        raise RuntimeError("Reindex already in progress. Please wait and retry.")

    monkeypatch.setattr(rag_index, "build_index", _raise_in_progress)
    conflict = client.post("/api/v1/reindex")
    assert conflict.status_code == 409
    assert "already in progress" in conflict.text.lower()

    monkeypatch.setattr(rag_index, "build_index", original_build_index)
    success = client.post("/api/v1/reindex")
    assert success.status_code == 200


def test_rest_api_reindex_first_call_not_limited_when_monotonic_low(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_test_env(monkeypatch, tmp_path)
    monkeypatch.setenv("VOICE_TRIAGE_REINDEX_MIN_INTERVAL_SECONDS", "60")

    import voice_triage.http.rest as rest_module

    monkeypatch.setattr(rest_module.time, "monotonic", lambda: 5.0)
    client = TestClient(create_rest_app())
    first = client.post("/api/v1/reindex")

    assert first.status_code == 200
