"""audio.capture module."""

from __future__ import annotations

import wave
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd


def record_push_to_talk(
    sample_rate: int = 16_000,
    channels: int = 1,
    temp_dir: Path | None = None,
) -> Path:
    """Record mic input between two ENTER presses and save a WAV file."""
    output_dir = temp_dir or Path("data") / "tmp_audio"
    output_dir.mkdir(parents=True, exist_ok=True)

    frames: list[np.ndarray] = []

    def callback(indata: np.ndarray, _frames: int, _time: object, _status: object) -> None:
        """Callback."""
        frames.append(indata.copy())

    input("Press ENTER to start recording...")
    with sd.InputStream(
        samplerate=sample_rate, channels=channels, dtype="int16", callback=callback
    ):
        input("Recording... press ENTER to stop.\n")

    if not frames:
        raise RuntimeError("No audio was captured from the microphone.")

    audio = np.concatenate(frames, axis=0).astype(np.int16)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    wav_path = output_dir / f"turn_{timestamp}.wav"

    with wave.open(str(wav_path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio.tobytes())

    return wav_path
