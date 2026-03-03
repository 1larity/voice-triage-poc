from __future__ import annotations

import os
from pathlib import Path

import pytest

from voice_triage.http.rest import _cleanup_temp_directory


def _touch_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")


def test_cleanup_temp_directory_removes_old_files(tmp_path: Path) -> None:
    temp_dir = tmp_path / "tmp_audio"
    old_file = temp_dir / "old.wav"
    new_file = temp_dir / "new.wav"
    _touch_file(old_file)
    _touch_file(new_file)

    old_epoch = 1_577_836_800  # 2020-01-01T00:00:00Z
    new_epoch = 2_524_608_000  # 2050-01-01T00:00:00Z
    os.utime(old_file, (old_epoch, old_epoch))
    os.utime(new_file, (new_epoch, new_epoch))

    _cleanup_temp_directory(temp_dir, retention_seconds=60 * 60, max_count=10)

    assert not old_file.exists()
    assert new_file.exists()


def test_cleanup_temp_directory_enforces_max_count(tmp_path: Path) -> None:
    temp_dir = tmp_path / "tmp_tts"
    files = []
    for idx in range(5):
        file_path = temp_dir / f"tts_{idx}.wav"
        _touch_file(file_path)
        timestamp = 2_000_000_000 + idx
        os.utime(file_path, (timestamp, timestamp))
        files.append(file_path)

    _cleanup_temp_directory(temp_dir, retention_seconds=60 * 60 * 24 * 365, max_count=2)

    remaining = sorted(temp_dir.glob("*.wav"))
    assert len(remaining) == 2
    assert remaining == [files[3], files[4]]


def test_cleanup_temp_directory_ignores_stat_race_during_sort(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    temp_dir = tmp_path / "tmp_audio"
    for idx in range(3):
        file_path = temp_dir / f"tts_{idx}.wav"
        _touch_file(file_path)
        timestamp = 2_100_000_000 + idx
        os.utime(file_path, (timestamp, timestamp))

    real_stat = Path.stat

    def flaky_stat(path: Path) -> os.stat_result:
        if path.name == "tts_2.wav":
            raise FileNotFoundError("simulated concurrent delete")
        return real_stat(path)

    monkeypatch.setattr(Path, "stat", flaky_stat)

    _cleanup_temp_directory(temp_dir, retention_seconds=60 * 60 * 24 * 365, max_count=1)

    remaining = sorted(temp_dir.glob("*.wav"))
    assert remaining
