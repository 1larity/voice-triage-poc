"""audio.vad module."""

from __future__ import annotations

import numpy as np


def is_voice_present(samples: np.ndarray, threshold: float = 500.0) -> bool:
    """Very simple RMS energy check for voice activity."""
    if samples.size == 0:
        return False
    rms = float(np.sqrt(np.mean(np.square(samples.astype(np.float64)))))
    return rms >= threshold
