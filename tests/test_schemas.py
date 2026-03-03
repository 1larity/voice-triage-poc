from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from voice_triage.nlu.schemas import CallSessionRecord, ExtractionResult, Intent


def test_extraction_schema_accepts_expected_fields() -> None:
    result = ExtractionResult(
        intent=Intent.MOVE_HOME,
        raw_text="I am moving to SW1A 1AA",
        postcode="SW1A 1AA",
    )
    assert result.postcode == "SW1A 1AA"


def test_extraction_schema_requires_raw_text() -> None:
    with pytest.raises(ValidationError):
        ExtractionResult(intent=Intent.RAG_QA)


def test_call_session_record_validates() -> None:
    extracted = ExtractionResult(intent=Intent.RAG_QA, raw_text="What are your opening times?")
    record = CallSessionRecord(
        started_at=datetime.now(tz=UTC),
        transcript="What are your opening times?",
        extracted=extracted,
        route="RAG_QA",
        outcome={"status": "ok"},
    )
    assert record.route == "RAG_QA"
