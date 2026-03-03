from voice_triage.nlu.extractor import HeuristicExtractor
from voice_triage.nlu.schemas import ExtractionResult, Intent
from voice_triage.workflows.router import Route, decide_route, route_from_transcript


def test_route_from_transcript_move_keywords() -> None:
    route = route_from_transcript("I am moving to a new address next week")
    assert route == Route.MOVE_HOME


def test_route_from_transcript_defaults_to_rag() -> None:
    route = route_from_transcript("How do I report a missed bin collection?")
    assert route == Route.RAG_QA


def test_decide_route_uses_extracted_intent() -> None:
    extraction = ExtractionResult(intent=Intent.MOVE_HOME, raw_text="I am moving")
    route = decide_route(extraction)
    assert route == Route.MOVE_HOME


def test_register_for_garden_waste_stays_rag() -> None:
    extractor = HeuristicExtractor()
    extraction = extractor.extract("How do I register for a garden waste bin?")
    route = decide_route(extraction)
    assert extraction.intent == Intent.RAG_QA
    assert route == Route.RAG_QA


def test_register_to_vote_defaults_to_rag_for_information_queries() -> None:
    extractor = HeuristicExtractor()
    extraction = extractor.extract("I need to register to vote at my new home.")
    route = decide_route(extraction)
    assert extraction.intent == Intent.ELECTORAL_REGISTER
    assert route == Route.RAG_QA


def test_register_to_vote_workflow_can_be_triggered_explicitly() -> None:
    extractor = HeuristicExtractor()
    extraction = extractor.extract("Please run workflow and submit request to register to vote.")
    route = decide_route(extraction)
    assert extraction.intent == Intent.ELECTORAL_REGISTER
    assert route == Route.ELECTORAL_REGISTER
