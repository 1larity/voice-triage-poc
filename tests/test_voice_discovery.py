from pathlib import Path

from voice_triage.web.server import _discover_piper_voices


def test_discover_piper_voices_from_model_directory(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    default_model = models_dir / "en_GB-voice-medium.onnx"
    other_model = models_dir / "en_US-voice-low.onnx"
    default_model.write_text("x", encoding="utf-8")
    other_model.write_text("x", encoding="utf-8")

    voices, default_voice_id = _discover_piper_voices(default_model)

    assert default_voice_id == "en_GB-voice-medium"
    assert "en_GB-voice-medium" in voices
    assert "en_US-voice-low" in voices


def test_discover_piper_voices_prefers_requested_default(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    configured_model = models_dir / "en_US-voice-low.onnx"
    alba_model = models_dir / "en_GB-alba-medium.onnx"
    configured_model.write_text("x", encoding="utf-8")
    alba_model.write_text("x", encoding="utf-8")

    voices, default_voice_id = _discover_piper_voices(
        configured_model, preferred_default_voice_id="en_GB-alba-medium"
    )

    assert "en_GB-alba-medium" in voices
    assert default_voice_id == "en_GB-alba-medium"


def test_discover_piper_voices_empty_when_missing_model(tmp_path: Path) -> None:
    missing_model = tmp_path / "missing.onnx"
    voices, default_voice_id = _discover_piper_voices(missing_model)

    assert voices == {}
    assert default_voice_id is None
