from typing import Any

from voice_triage.app.conversation import ConversationEngine, ConversationStage
from voice_triage.nlu.extractor import HeuristicExtractor
from voice_triage.rag.answer import LocalRagService
from voice_triage.rag.index import build_index
from voice_triage.rag.retrieve import SqliteRetriever
from voice_triage.workflows.router import Route


class FakeRagService:
    def answer(self, question: str) -> tuple[str, dict[str, Any]]:
        return (f"RAG answer for: {question}", {"used_kb": False, "hits": []})


def test_rag_turn_returns_rag_response() -> None:
    engine = ConversationEngine(extractor=HeuristicExtractor(), rag_service=FakeRagService())
    session_id, _ = engine.create_session()

    result = engine.process_turn(session_id=session_id, transcript="What are your opening times?")

    assert result.route == Route.RAG_QA
    assert result.stage == ConversationStage.DONE
    assert "RAG answer for:" in result.response_text


def test_move_home_flow_collects_fields_and_submits() -> None:
    engine = ConversationEngine(extractor=HeuristicExtractor(), rag_service=FakeRagService())
    session_id, _ = engine.create_session()

    first = engine.process_turn(session_id=session_id, transcript="I am moving house")
    assert first.route == Route.MOVE_HOME
    assert first.stage == ConversationStage.ASK_CURRENT_ADDRESS
    assert "current address" in first.response_text.lower()

    second = engine.process_turn(session_id=session_id, transcript="12 Old Street, SW1A 1AA")
    assert second.stage == ConversationStage.CONFIRM_CURRENT_ADDRESS
    assert "is that correct" in second.response_text.lower()

    third = engine.process_turn(session_id=session_id, transcript="yes")
    assert third.stage == ConversationStage.ASK_NEW_ADDRESS
    assert "new address" in third.response_text.lower()

    fourth = engine.process_turn(session_id=session_id, transcript="55 New Road, AB1 2CD")
    assert fourth.stage == ConversationStage.CONFIRM_NEW_ADDRESS
    assert "is that correct" in fourth.response_text.lower()

    fifth = engine.process_turn(session_id=session_id, transcript="yes")
    assert fifth.stage == ConversationStage.ASK_MOVE_DATE
    assert "move date" in fifth.response_text.lower()

    sixth = engine.process_turn(session_id=session_id, transcript="2026-04-20")
    assert sixth.stage == ConversationStage.CONFIRM
    assert "confirm your details" in sixth.response_text.lower()
    assert sixth.outcome["captured_data"]["current_address_verified"] is True
    assert sixth.outcome["captured_data"]["new_address_verified"] is True

    seventh = engine.process_turn(session_id=session_id, transcript="yes")
    assert seventh.stage == ConversationStage.DONE
    assert "request captured" in seventh.response_text.lower()


def test_session_opening_prompt_is_from_generic_set() -> None:
    engine = ConversationEngine(extractor=HeuristicExtractor(), rag_service=FakeRagService())
    _, greeting = engine.create_session()
    assert greeting in engine.OPENING_PROMPTS


def test_move_confirmation_accepts_yes_with_punctuation() -> None:
    engine = ConversationEngine(extractor=HeuristicExtractor(), rag_service=FakeRagService())
    session_id, _ = engine.create_session()

    engine.process_turn(session_id=session_id, transcript="I am moving house")
    engine.process_turn(session_id=session_id, transcript="12 Old Street, SW1A 1AA")
    result = engine.process_turn(session_id=session_id, transcript="Yes.")

    assert result.stage == ConversationStage.ASK_NEW_ADDRESS
    assert "new address" in result.response_text.lower()


def test_acknowledgement_returns_polite_followup() -> None:
    engine = ConversationEngine(extractor=HeuristicExtractor(), rag_service=FakeRagService())
    session_id, _ = engine.create_session()

    result = engine.process_turn(session_id=session_id, transcript="Cool.")

    assert result.route == Route.RAG_QA
    assert result.outcome["rag"]["reason"] == "acknowledgement"
    assert result.response_text.endswith("?")


def test_move_flow_prompts_for_missing_postcodes() -> None:
    engine = ConversationEngine(extractor=HeuristicExtractor(), rag_service=FakeRagService())
    session_id, _ = engine.create_session()

    engine.process_turn(session_id=session_id, transcript="I'm moving house")
    second = engine.process_turn(session_id=session_id, transcript="47 Cheltenham Place")
    assert second.stage == ConversationStage.CONFIRM_CURRENT_ADDRESS

    third = engine.process_turn(session_id=session_id, transcript="yes")
    assert third.stage == ConversationStage.ASK_CURRENT_POSTCODE
    assert "current postcode" in third.response_text.lower()

    fourth = engine.process_turn(session_id=session_id, transcript="BN1 4AB")
    assert fourth.stage == ConversationStage.ASK_NEW_ADDRESS

    fifth = engine.process_turn(session_id=session_id, transcript="11 Manor Road")
    assert fifth.stage == ConversationStage.CONFIRM_NEW_ADDRESS

    sixth = engine.process_turn(session_id=session_id, transcript="yes")
    assert sixth.stage == ConversationStage.ASK_NEW_POSTCODE
    assert "new postcode" in sixth.response_text.lower()

    seventh = engine.process_turn(session_id=session_id, transcript="BN2 1CD")
    assert seventh.stage == ConversationStage.ASK_MOVE_DATE
    assert "move date" in seventh.response_text.lower()


def test_move_flow_accepts_natural_language_date() -> None:
    engine = ConversationEngine(extractor=HeuristicExtractor(), rag_service=FakeRagService())
    session_id, _ = engine.create_session()

    engine.process_turn(session_id=session_id, transcript="I'm moving house")
    engine.process_turn(session_id=session_id, transcript="47 Cheltenham Place BN1 4AB")
    engine.process_turn(session_id=session_id, transcript="yes")
    engine.process_turn(session_id=session_id, transcript="11 Manor Road BN2 1CD")
    engine.process_turn(session_id=session_id, transcript="yes")
    result = engine.process_turn(session_id=session_id, transcript="4th of April 2026")

    assert result.stage == ConversationStage.CONFIRM
    assert result.outcome["captured_data"]["move_date"] == "2026-04-04"


def test_move_flow_rejects_non_address_text_for_current_address() -> None:
    engine = ConversationEngine(extractor=HeuristicExtractor(), rag_service=FakeRagService())
    session_id, _ = engine.create_session()

    engine.process_turn(session_id=session_id, transcript="I'm moving house")
    result = engine.process_turn(session_id=session_id, transcript="not sure")

    assert result.stage == ConversationStage.ASK_CURRENT_ADDRESS
    assert "current address" in result.response_text.lower()


def test_move_flow_rejects_address_without_house_number() -> None:
    engine = ConversationEngine(extractor=HeuristicExtractor(), rag_service=FakeRagService())
    session_id, _ = engine.create_session()

    engine.process_turn(session_id=session_id, transcript="I'm moving house")
    result = engine.process_turn(session_id=session_id, transcript="Cheltenham Place")

    assert result.stage == ConversationStage.ASK_CURRENT_ADDRESS
    assert "current address" in result.response_text.lower()


def test_move_flow_accepts_spoken_house_number_without_digits() -> None:
    engine = ConversationEngine(extractor=HeuristicExtractor(), rag_service=FakeRagService())
    session_id, _ = engine.create_session()

    engine.process_turn(session_id=session_id, transcript="I'm moving house")
    confirm = engine.process_turn(session_id=session_id, transcript="twelve old street")

    assert confirm.stage == ConversationStage.CONFIRM_CURRENT_ADDRESS
    assert "is that correct" in confirm.response_text.lower()

    follow_up = engine.process_turn(session_id=session_id, transcript="yes")
    assert follow_up.stage == ConversationStage.ASK_CURRENT_POSTCODE
    assert "current postcode" in follow_up.response_text.lower()


def test_move_flow_rejects_spoken_number_without_address_structure() -> None:
    engine = ConversationEngine(extractor=HeuristicExtractor(), rag_service=FakeRagService())
    session_id, _ = engine.create_session()

    engine.process_turn(session_id=session_id, transcript="I'm moving house")
    result = engine.process_turn(session_id=session_id, transcript="one thing maybe")

    assert result.stage == ConversationStage.ASK_CURRENT_ADDRESS
    assert "current address" in result.response_text.lower()


def test_follow_up_question_keeps_previous_rag_topic(tmp_path) -> None:
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir(parents=True, exist_ok=True)
    (kb_dir / "licensing_taxi_licence.md").write_text(
        "\n".join(
            [
                "title: Taxi licence applications",
                "tags: [licensing, taxi, licence]",
                "summary:",
                "- Taxi licence applications are required before carrying passengers.",
                "key_points:",
                "- Taxi licence documents include proof of identity.",
                "- Taxi licence evidence includes right-to-work checks.",
            ]
        ),
        encoding="utf-8",
    )
    (kb_dir / "licensing_pub_licence.md").write_text(
        "\n".join(
            [
                "title: Pub alcohol premises licence",
                "tags: [licensing, alcohol, pub]",
                "summary:",
                "- Pub premises licences are for alcohol sales.",
                "key_points:",
                "- Pub licence applications need a designated premises supervisor.",
            ]
        ),
        encoding="utf-8",
    )
    index_db = tmp_path / "rag.db"
    build_index(kb_dir=kb_dir, index_db_path=index_db)
    rag_service = LocalRagService(retriever=SqliteRetriever(index_db))
    engine = ConversationEngine(extractor=HeuristicExtractor(), rag_service=rag_service)
    session_id, _ = engine.create_session()

    first = engine.process_turn(session_id=session_id, transcript="How do I get a taxi licence?")
    assert "taxi" in first.response_text.lower()

    second = engine.process_turn(session_id=session_id, transcript="What documents do I need?")
    assert "taxi" in second.response_text.lower()
    assert "pub" not in second.response_text.lower()
