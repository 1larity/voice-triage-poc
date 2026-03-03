"""store.db module."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from voice_triage.nlu.schemas import CallSessionRecord, ExtractionResult
from voice_triage.store.models import StoredSession

DBTarget = sqlite3.Connection | str | Path


def _open_connection(target: DBTarget) -> tuple[sqlite3.Connection, bool]:
    """open connection."""
    if isinstance(target, sqlite3.Connection):
        target.row_factory = sqlite3.Row
        return target, False

    db_path = Path(target)
    if str(db_path) != ":memory:":
        db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection, True


def init_db(target: DBTarget) -> None:
    """Init db."""
    connection, should_close = _open_connection(target)
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                transcript TEXT NOT NULL,
                extracted_json TEXT NOT NULL,
                route TEXT NOT NULL,
                outcome_json TEXT NOT NULL
            )
            """
        )
        connection.commit()
    finally:
        if should_close:
            connection.close()


def save_session(target: DBTarget, record: CallSessionRecord) -> int:
    """Save session."""
    connection, should_close = _open_connection(target)
    try:
        cursor = connection.execute(
            """
            INSERT INTO sessions (started_at, transcript, extracted_json, route, outcome_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                record.started_at.isoformat(),
                record.transcript,
                record.extracted.model_dump_json(),
                record.route,
                json.dumps(record.outcome),
            ),
        )
        connection.commit()
        if cursor.lastrowid is None:
            raise RuntimeError("Failed to persist session; sqlite did not return a row id.")
        return int(cursor.lastrowid)
    finally:
        if should_close:
            connection.close()


def fetch_session(target: DBTarget, session_id: int) -> StoredSession | None:
    """Fetch session."""
    connection, should_close = _open_connection(target)
    try:
        row = connection.execute(
            (
                "SELECT id, started_at, transcript, extracted_json, route, outcome_json "
                "FROM sessions WHERE id = ?"
            ),
            (session_id,),
        ).fetchone()
        if row is None:
            return None

        return StoredSession(
            session_id=int(row["id"]),
            started_at=datetime.fromisoformat(row["started_at"]),
            transcript=str(row["transcript"]),
            extracted=ExtractionResult.model_validate_json(row["extracted_json"]),
            route=str(row["route"]),
            outcome=json.loads(row["outcome_json"]),
        )
    finally:
        if should_close:
            connection.close()
