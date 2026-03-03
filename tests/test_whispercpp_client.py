import subprocess
from pathlib import Path

import pytest

from voice_triage.asr.whispercpp import WhisperCppClient


def _touch(path: Path) -> None:
    path.write_text("x", encoding="utf-8")


def test_whispercpp_transcribe_parses_stdout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bin_path = tmp_path / "main"
    model_path = tmp_path / "ggml-base.en.bin"
    wav_path = tmp_path / "turn.wav"
    _touch(bin_path)
    _touch(model_path)
    _touch(wav_path)

    def fake_run(
        command: list[str],
        capture_output: bool,
        text: bool,
        check: bool,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        assert capture_output is True
        assert text is True
        assert check is False
        assert timeout == 45.0
        return subprocess.CompletedProcess(command, 0, stdout="hello from whisper\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    client = WhisperCppClient(str(bin_path), str(model_path))
    result = client.transcribe(wav_path)

    assert result.text == "hello from whisper"


def test_whispercpp_transcribe_raises_on_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bin_path = tmp_path / "main"
    model_path = tmp_path / "ggml-base.en.bin"
    wav_path = tmp_path / "turn.wav"
    _touch(bin_path)
    _touch(model_path)
    _touch(wav_path)

    def fake_run(
        command: list[str],
        capture_output: bool,
        text: bool,
        check: bool,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        assert timeout == 45.0
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="bad model")

    monkeypatch.setattr(subprocess, "run", fake_run)

    client = WhisperCppClient(str(bin_path), str(model_path))
    with pytest.raises(RuntimeError, match=r"whisper\.cpp failed"):
        client.transcribe(wav_path)


def test_whispercpp_transcribe_adds_cuda_and_runtime_flags(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bin_path = tmp_path / "main"
    model_path = tmp_path / "ggml-base.en.bin"
    wav_path = tmp_path / "turn.wav"
    _touch(bin_path)
    _touch(model_path)
    _touch(wav_path)

    def fake_run(
        command: list[str],
        capture_output: bool,
        text: bool,
        check: bool,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        assert "-t" in command
        assert "6" in command
        assert "-ngl" in command
        assert "30" in command
        assert "--language" in command
        assert "en" in command
        assert timeout == 12.5
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    client = WhisperCppClient(
        str(bin_path),
        str(model_path),
        use_gpu=True,
        gpu_layers=30,
        threads=6,
        extra_args=("--language", "en"),
        timeout_seconds=12.5,
    )
    result = client.transcribe(wav_path)

    assert result.text == "ok"


def test_whispercpp_transcribe_raises_on_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bin_path = tmp_path / "main"
    model_path = tmp_path / "ggml-base.en.bin"
    wav_path = tmp_path / "turn.wav"
    _touch(bin_path)
    _touch(model_path)
    _touch(wav_path)

    def fake_run(
        command: list[str],
        capture_output: bool,
        text: bool,
        check: bool,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(command, timeout)

    monkeypatch.setattr(subprocess, "run", fake_run)

    client = WhisperCppClient(str(bin_path), str(model_path), timeout_seconds=3.0)
    with pytest.raises(RuntimeError, match=r"timed out"):
        client.transcribe(wav_path)
