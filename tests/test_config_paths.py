import os
from pathlib import Path

import pytest

from voice_triage.util.config import (
    _default_piper_bin,
    _default_whisper_bin,
    _resolve_config_path,
    _should_override_stale_path_env,
    _validate_byo_inference_url,
)


def test_resolve_config_path_uses_project_root_for_relative_values(tmp_path: Path) -> None:
    project_root = tmp_path
    default_path = project_root / ".venv" / "tools" / "piper" / "piper.exe"
    resolved = _resolve_config_path(
        raw_value=".venv/tools/piper/piper.exe",
        default_path=default_path,
        project_root=project_root,
    )

    assert resolved == default_path.resolve(strict=False)


def test_resolve_config_path_falls_back_to_default_for_missing_stale_values(tmp_path: Path) -> None:
    project_root = tmp_path
    default_path = project_root / ".venv" / "tools" / "piper" / "piper.exe"
    default_path.parent.mkdir(parents=True, exist_ok=True)
    default_path.write_text("binary", encoding="utf-8")

    resolved = _resolve_config_path(
        raw_value="K:/old-machine/voice-triage-poc/.venv/tools/piper/piper.exe",
        default_path=default_path,
        project_root=project_root,
        fallback_to_existing_default=True,
    )

    assert resolved == default_path.resolve(strict=False)


def test_resolve_config_path_preserves_missing_value_when_no_fallback(tmp_path: Path) -> None:
    project_root = tmp_path
    default_path = project_root / ".venv" / "tools" / "piper" / "piper.exe"

    resolved = _resolve_config_path(
        raw_value=".venv/tools/piper/custom-missing.exe",
        default_path=default_path,
        project_root=project_root,
        fallback_to_existing_default=False,
    )

    assert resolved == (project_root / ".venv/tools/piper/custom-missing.exe").resolve(strict=False)


def test_should_override_stale_path_env_for_missing_current_and_existing_new(
    tmp_path: Path,
) -> None:
    project_root = tmp_path
    new_path = project_root / ".venv/tools/piper/piper.exe"
    new_path.parent.mkdir(parents=True, exist_ok=True)
    new_path.write_text("binary", encoding="utf-8")

    should_override = _should_override_stale_path_env(
        key="PIPER_BIN",
        current_value="K:/old-machine/voice-triage-poc/.venv/tools/piper/piper.exe",
        new_value=".venv/tools/piper/piper.exe",
        project_root=project_root,
    )

    assert should_override is True


def test_should_not_override_non_path_env_keys(tmp_path: Path) -> None:
    project_root = tmp_path
    should_override = _should_override_stale_path_env(
        key="VOICE_TRIAGE_INFERENCE_BACKEND",
        current_value="byo",
        new_value="local",
        project_root=project_root,
    )

    assert should_override is False


def test_default_piper_bin_prefers_venv_local_script_when_present(tmp_path: Path) -> None:
    venv_dir = tmp_path / ".venv"
    if os.name == "nt":
        preferred = venv_dir / "Scripts" / "piper.exe"
        fallback = venv_dir / "tools" / "piper" / "piper.exe"
    else:
        preferred = venv_dir / "bin" / "piper"
        fallback = venv_dir / "tools" / "piper" / "piper"

    preferred.parent.mkdir(parents=True, exist_ok=True)
    fallback.parent.mkdir(parents=True, exist_ok=True)
    preferred.write_text("bin", encoding="utf-8")
    fallback.write_text("bin", encoding="utf-8")

    selected = _default_piper_bin(venv_dir)

    assert selected == preferred


def test_default_whisper_bin_prefers_release_or_build_layout(tmp_path: Path) -> None:
    venv_dir = tmp_path / ".venv"
    if os.name == "nt":
        preferred = venv_dir / "tools" / "whispercpp" / "Release" / "whisper-cli.exe"
        fallback = venv_dir / "tools" / "whispercpp" / "main.exe"
    else:
        preferred = venv_dir / "tools" / "whispercpp" / "build" / "bin" / "whisper-cli"
        fallback = venv_dir / "tools" / "whispercpp" / "main"

    preferred.parent.mkdir(parents=True, exist_ok=True)
    fallback.parent.mkdir(parents=True, exist_ok=True)
    preferred.write_text("bin", encoding="utf-8")
    fallback.write_text("bin", encoding="utf-8")

    selected = _default_whisper_bin(venv_dir)

    assert selected == preferred


def test_validate_byo_inference_url_allows_http_and_https() -> None:
    assert _validate_byo_inference_url("http://127.0.0.1:11434/v1/chat/completions")
    assert _validate_byo_inference_url("https://example.com/infer")


def test_validate_byo_inference_url_rejects_non_http_scheme() -> None:
    with pytest.raises(ValueError, match="http:// or https://"):
        _validate_byo_inference_url("file:///tmp/infer")


def test_validate_byo_inference_url_rejects_missing_host() -> None:
    with pytest.raises(ValueError, match="include a host"):
        _validate_byo_inference_url("http:///infer")


def test_validate_byo_inference_url_rejects_empty_hostname_with_port() -> None:
    with pytest.raises(ValueError, match="include a host"):
        _validate_byo_inference_url("http://:11434/v1")


def test_validate_byo_inference_url_rejects_userinfo_without_host() -> None:
    with pytest.raises(ValueError, match="include a host"):
        _validate_byo_inference_url("http://user@/path")
