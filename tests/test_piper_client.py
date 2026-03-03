import subprocess
from pathlib import Path

import pytest

from voice_triage.tts.piper import PiperClient


def _touch(path: Path) -> None:
    path.write_text("x", encoding="utf-8")


def test_piper_synthesize_to_wav_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    bin_path = tmp_path / "piper"
    model_path = tmp_path / "voice.onnx"
    output_path = tmp_path / "speech.wav"
    _touch(bin_path)
    _touch(model_path)

    def fake_run(
        command: list[str],
        input: str,
        text: bool,
        capture_output: bool,
        check: bool,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        assert "--model" in command
        assert "--output_file" in command
        assert text is True
        assert capture_output is True
        assert check is False
        assert timeout == 30.0
        assert "hello there" in input
        output_index = command.index("--output_file") + 1
        Path(command[output_index]).write_bytes(b"RIFF....WAVE")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    client = PiperClient(str(bin_path), str(model_path))
    synthesized = client.synthesize_to_wav("hello there", output_path)

    assert synthesized == output_path
    assert synthesized.exists()


def test_piper_synthesize_to_wav_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bin_path = tmp_path / "piper"
    model_path = tmp_path / "voice.onnx"
    _touch(bin_path)
    _touch(model_path)

    def fake_run(
        command: list[str],
        input: str,
        text: bool,
        capture_output: bool,
        check: bool,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        assert timeout == 30.0
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="bad voice")

    monkeypatch.setattr(subprocess, "run", fake_run)

    client = PiperClient(str(bin_path), str(model_path))
    with pytest.raises(RuntimeError, match="Piper failed"):
        client.synthesize_to_wav("hello there", tmp_path / "speech.wav")


def test_piper_synthesize_to_wav_timeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    bin_path = tmp_path / "piper"
    model_path = tmp_path / "voice.onnx"
    _touch(bin_path)
    _touch(model_path)

    def fake_run(
        command: list[str],
        input: str,
        text: bool,
        capture_output: bool,
        check: bool,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(command, timeout)

    monkeypatch.setattr(subprocess, "run", fake_run)

    client = PiperClient(str(bin_path), str(model_path), timeout_seconds=4.0)
    with pytest.raises(RuntimeError, match="timed out"):
        client.synthesize_to_wav("hello there", tmp_path / "speech.wav")
