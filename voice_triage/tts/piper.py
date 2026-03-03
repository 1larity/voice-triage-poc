"""tts.piper module."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


class PiperUnavailable(RuntimeError):
    """Raised when Piper binary/model is missing."""


_UK_CURRENCY_PATTERN = re.compile(r"£\s*([0-9][0-9,]*)(?:\.([0-9]{1,2}))?")


def normalize_tts_text(text: str) -> str:
    """Normalize user-facing response text for clearer UK TTS pronunciation."""
    return _UK_CURRENCY_PATTERN.sub(_replace_uk_currency_match, text)


def _replace_uk_currency_match(match: re.Match[str]) -> str:
    """Render UK currency values in natural spoken order for TTS."""
    pounds_raw = match.group(1).replace(",", "")
    pence_raw = match.group(2)

    pounds = int(pounds_raw)
    pence = int(pence_raw.ljust(2, "0")) if pence_raw else 0

    pound_part = "1 pound" if pounds == 1 else f"{pounds} pounds"
    if pence == 0:
        return pound_part
    if pounds == 0:
        return "1 penny" if pence == 1 else f"{pence} pence"

    pence_part = "1 penny" if pence == 1 else f"{pence} pence"
    return f"{pound_part} and {pence_part}"


class PiperClient:
    """Subprocess wrapper around Piper CLI TTS."""

    def __init__(
        self, bin_path: str | None, model_path: str | None, timeout_seconds: float = 30.0
    ) -> None:
        """init  ."""
        self.bin_path = bin_path
        self.model_path = Path(model_path).expanduser() if model_path else None
        self.timeout_seconds = max(1.0, timeout_seconds)

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
        normalized_text = normalize_tts_text(text)

        try:
            process = subprocess.run(
                command,
                input=normalized_text,
                text=True,
                capture_output=True,
                check=False,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"Piper timed out after {self.timeout_seconds:.1f}s while synthesizing audio."
            ) from exc
        if process.returncode != 0:
            raise RuntimeError(
                f"Piper failed with code {process.returncode}: {process.stderr.strip()}"
            )
        if not output_path.exists():
            raise RuntimeError("Piper did not generate output audio.")
        return output_path
