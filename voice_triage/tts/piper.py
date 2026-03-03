"""tts.piper module."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class PiperUnavailable(RuntimeError):
    """Raised when Piper binary/model is missing."""


class PiperClient:
    """Subprocess wrapper around Piper CLI TTS."""

    def __init__(self, bin_path: str | None, model_path: str | None) -> None:
        """init  ."""
        self.bin_path = bin_path
        self.model_path = Path(model_path).expanduser() if model_path else None

    def ensure_ready(self, model_path: Path | None = None) -> None:
        """Ensure ready."""
        if not self.bin_path:
            raise PiperUnavailable("PIPER_BIN must be configured.")
        resolved_model = model_path or self.model_path
        if resolved_model is None:
            raise PiperUnavailable("PIPER_MODEL must be configured.")

        resolved = shutil.which(self.bin_path)
        if resolved is None and not Path(self.bin_path).exists():
            raise PiperUnavailable(f"Piper binary not found: {self.bin_path}")
        if not resolved_model.exists():
            raise PiperUnavailable(f"Piper model not found: {resolved_model}")

    def synthesize_to_wav(
        self, text: str, output_path: Path, model_path: Path | None = None
    ) -> Path:
        """Synthesize to wav."""
        selected_model = model_path or self.model_path
        self.ensure_ready(model_path=selected_model)
        if selected_model is None:
            raise PiperUnavailable("PIPER_MODEL must be configured.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            self.bin_path or "piper",
            "--model",
            str(selected_model),
            "--output_file",
            str(output_path),
        ]

        process = subprocess.run(
            command,
            input=text,
            text=True,
            capture_output=True,
            check=False,
        )
        if process.returncode != 0:
            raise RuntimeError(
                f"Piper failed with code {process.returncode}: {process.stderr.strip()}"
            )
        if not output_path.exists():
            raise RuntimeError("Piper did not generate output audio.")
        return output_path
