"""util.config module."""

from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Settings."""

    project_root: Path
    kb_dir: Path
    data_dir: Path
    db_path: Path
    rag_index_path: Path
    whispercpp_bin: str | None
    whispercpp_model: str | None
    whispercpp_use_gpu: bool
    whispercpp_gpu_layers: int
    whispercpp_threads: int | None
    whispercpp_extra_args: tuple[str, ...]
    inference_backend: str
    byo_inference_url: str | None
    byo_inference_timeout_seconds: float
    byo_inference_api_style: str
    byo_inference_model: str | None
    byo_inference_api_key: str | None
    byo_inference_system_prompt: str | None
    piper_bin: str | None
    piper_model: str | None
    piper_default_voice_id: str | None
    web_ssl_certfile: str | None
    web_ssl_keyfile: str | None
    sample_rate: int = 16_000
    channels: int = 1


def load_settings() -> Settings:
    """Load configuration from environment variables with local defaults."""
    project_root = Path(__file__).resolve().parents[2]
    _load_local_env(project_root)
    data_dir = project_root / "data"
    kb_dir = project_root / "kb"
    venv_dir = project_root / ".venv"

    db_path = Path(os.getenv("VOICE_TRIAGE_DB", data_dir / "voice_triage.db"))
    rag_index_path = Path(os.getenv("VOICE_TRIAGE_RAG_INDEX", data_dir / "rag_index.db"))
    whisper_bin_default = _default_whisper_bin(venv_dir)
    whisper_model_default = venv_dir / "tools" / "whispercpp" / "models" / "ggml-base.en.bin"
    piper_bin_default = _default_piper_bin(venv_dir)
    piper_model_default = venv_dir / "tools" / "piper" / "models" / "voice.onnx"
    ssl_cert_default = venv_dir / "certs" / "dev-cert.pem"
    ssl_key_default = venv_dir / "certs" / "dev-key.pem"
    whisper_threads_raw = os.getenv("WHISPERCPP_THREADS", "").strip()
    whisper_extra_args_raw = os.getenv("WHISPERCPP_EXTRA_ARGS", "").strip()

    return Settings(
        project_root=project_root,
        kb_dir=Path(os.getenv("VOICE_TRIAGE_KB_DIR", kb_dir)),
        data_dir=Path(os.getenv("VOICE_TRIAGE_DATA_DIR", data_dir)),
        db_path=db_path,
        rag_index_path=rag_index_path,
        whispercpp_bin=os.getenv("WHISPERCPP_BIN", str(whisper_bin_default)),
        whispercpp_model=os.getenv("WHISPERCPP_MODEL", str(whisper_model_default)),
        whispercpp_use_gpu=_env_bool("WHISPERCPP_USE_GPU", default=False),
        whispercpp_gpu_layers=_env_int("WHISPERCPP_GPU_LAYERS", default=60, minimum=0),
        whispercpp_threads=_optional_positive_int(whisper_threads_raw),
        whispercpp_extra_args=tuple(
            shlex.split(whisper_extra_args_raw, posix=os.name != "nt")
            if whisper_extra_args_raw
            else []
        ),
        inference_backend=os.getenv("VOICE_TRIAGE_INFERENCE_BACKEND", "local"),
        byo_inference_url=os.getenv("VOICE_TRIAGE_BYO_INFERENCE_URL"),
        byo_inference_timeout_seconds=_env_float(
            "VOICE_TRIAGE_BYO_INFERENCE_TIMEOUT_SECONDS", default=12.0, minimum=0.1
        ),
        byo_inference_api_style=os.getenv("VOICE_TRIAGE_BYO_API_STYLE", "generic"),
        byo_inference_model=os.getenv("VOICE_TRIAGE_BYO_MODEL"),
        byo_inference_api_key=os.getenv("VOICE_TRIAGE_BYO_API_KEY"),
        byo_inference_system_prompt=os.getenv("VOICE_TRIAGE_BYO_SYSTEM_PROMPT"),
        piper_bin=os.getenv("PIPER_BIN", str(piper_bin_default)),
        piper_model=os.getenv("PIPER_MODEL", str(piper_model_default)),
        piper_default_voice_id=os.getenv("PIPER_DEFAULT_VOICE_ID", "en_GB-alba-medium"),
        web_ssl_certfile=os.getenv("VOICE_TRIAGE_SSL_CERTFILE", str(ssl_cert_default)),
        web_ssl_keyfile=os.getenv("VOICE_TRIAGE_SSL_KEYFILE", str(ssl_key_default)),
    )


def _load_local_env(project_root: Path) -> None:
    """Load optional key=value files without overriding existing process env vars."""
    candidates = [project_root / ".venv" / ".env", project_root / ".env"]
    for env_path in candidates:
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, raw_value = stripped.split("=", 1)
            key = key.strip()
            value = raw_value.strip().strip("'\"")
            if key:
                os.environ.setdefault(key, value)


def _default_whisper_bin(venv_dir: Path) -> Path:
    """default whisper bin."""
    if os.name == "nt":
        candidates = (
            venv_dir / "tools" / "whispercpp" / "whisper-cli.exe",
            venv_dir / "tools" / "whispercpp" / "main.exe",
        )
    else:
        candidates = (
            venv_dir / "tools" / "whispercpp" / "whisper-cli",
            venv_dir / "tools" / "whispercpp" / "main",
        )

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _default_piper_bin(venv_dir: Path) -> Path:
    """default piper bin."""
    if os.name == "nt":
        return venv_dir / "tools" / "piper" / "piper.exe"
    return venv_dir / "tools" / "piper" / "piper"


def _env_bool(name: str, default: bool) -> bool:
    """env bool."""
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int) -> int:
    """env int."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return _env_int_from_string(raw, minimum=minimum)


def _env_int_from_string(raw: str, minimum: int) -> int:
    """env int from string."""
    try:
        value = int(raw.strip())
    except ValueError as exc:
        raise ValueError(f"Expected integer value, got: {raw!r}") from exc
    if value < minimum:
        raise ValueError(f"Expected integer >= {minimum}, got: {value}")
    return value


def _optional_positive_int(raw: str) -> int | None:
    """optional positive int."""
    if not raw:
        return None
    value = _env_int_from_string(raw, minimum=0)
    if value == 0:
        return None
    return value


def _env_float(name: str, default: float, minimum: float) -> float:
    """env float."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw.strip())
    except ValueError as exc:
        raise ValueError(f"Expected float value, got: {raw!r}") from exc
    if value < minimum:
        raise ValueError(f"Expected float >= {minimum}, got: {value}")
    return value
