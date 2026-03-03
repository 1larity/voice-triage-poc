import sqlite3
from datetime import UTC, datetime

from voice_triage.nlu.schemas import CallSessionRecord, ExtractionResult, Intent
from voice_triage.store.db import fetch_session, init_db, save_session


def test_store_roundtrip_in_memory_sqlite() -> None:
    connection = sqlite3.connect(":memory:")
    init_db(connection)

    record = CallSessionRecord(
        started_at=datetime.now(tz=UTC),
        transcript="I am moving next month",
        extracted=ExtractionResult(intent=Intent.MOVE_HOME, raw_text="I am moving next month"),
        route="MOVE_HOME",
        outcome={"status": "submitted"},
    )

    session_id = save_session(connection, record)
    stored = fetch_session(connection, session_id)

    assert stored is not None
    assert stored.route == "MOVE_HOME"
    assert stored.extracted.intent == Intent.MOVE_HOME
    assert stored.outcome["status"] == "submitted"
