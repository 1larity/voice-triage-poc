"""asr.whispercpp module."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Protocol

from voice_triage.asr.types import AsrMetadata, AsrResult


class WhisperCppUnavailable(RuntimeError):
    """Raised when whisper.cpp binary/model are missing."""


class AsrClient(Protocol):
    """Asrclient."""

    def transcribe(self, wav_path: Path) -> AsrResult:
        """Transcribe a WAV audio file and return text plus metadata."""


class WhisperCppClient:
    """Simple subprocess wrapper for whisper.cpp CLI."""

    def __init__(
        self,
        bin_path: str | None,
        model_path: str | None,
        *,
        use_gpu: bool = False,
        gpu_layers: int = 60,
        threads: int | None = None,
        extra_args: tuple[str, ...] = (),
        timeout_seconds: float = 45.0,
    ) -> None:
        """init  ."""
        self.bin_path = Path(bin_path).expanduser() if bin_path else None
        self.model_path = Path(model_path).expanduser() if model_path else None
        self.use_gpu = use_gpu
        self.gpu_layers = max(0, gpu_layers)
        self.threads = threads
        self.extra_args = extra_args
        self.timeout_seconds = max(1.0, timeout_seconds)

    def transcribe(self, wav_path: Path) -> AsrResult:
        """Transcribe."""
        self._validate_environment()
        assert self.bin_path is not None
        assert self.model_path is not None

        if not wav_path.exists():
            raise FileNotFoundError(f"Audio file does not exist: {wav_path}")

        command = [
            str(self.bin_path),
            "-m",
            str(self.model_path),
            "-f",
            str(wav_path),
            "-nt",
        ]
        if self.threads is not None and self.threads > 0:
            command.extend(["-t", str(self.threads)])
        if self.use_gpu and self.gpu_layers > 0:
            command.extend(["-ngl", str(self.gpu_layers)])
        if self.extra_args:
            command.extend(self.extra_args)

        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                "whisper.cpp timed out after "
                f"{self.timeout_seconds:.1f}s while processing audio."
            ) from exc
        if process.returncode != 0:
            stderr = process.stderr.strip()
            raise RuntimeError(f"whisper.cpp failed with code {process.returncode}: {stderr}")

        transcript = self._extract_text(process.stdout)
        return AsrResult(text=transcript, metadata=AsrMetadata(model=self.model_path.name))

    def ensure_ready(self) -> None:
        """Validate configured binary/model paths before recording starts."""
        self._validate_environment()

    def _validate_environment(self) -> None:
        """validate environment."""
        if self.bin_path is None or self.model_path is None:
            raise WhisperCppUnavailable(
                "WHISPERCPP_BIN and WHISPERCPP_MODEL must be configured to use whisper.cpp."
            )
        if not self.bin_path.exists():
            raise WhisperCppUnavailable(f"whisper.cpp binary not found at: {self.bin_path}")
        if not self.model_path.exists():
            raise WhisperCppUnavailable(f"whisper.cpp model not found at: {self.model_path}")

    @staticmethod
    def _extract_text(stdout: str) -> str:
        """extract text."""
        lines = []
        for line in stdout.splitlines():
            clean = line.strip()
            if not clean:
                continue
            if clean.startswith("[") and clean.endswith("]"):
                continue
            lines.append(clean)
        return " ".join(lines).strip()
