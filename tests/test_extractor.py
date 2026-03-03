from voice_triage.nlu.extractor import HeuristicExtractor
from voice_triage.nlu.schemas import Intent


def test_extractor_parses_natural_day_month_year_date() -> None:
    extractor = HeuristicExtractor()
    result = extractor.extract("My move date is 4th of April 2026.")
    assert result.move_date == "2026-04-04"


def test_extractor_parses_numeric_day_first_date() -> None:
    extractor = HeuristicExtractor()
    result = extractor.extract("Move date: 04/04/2026")
    assert result.move_date == "2026-04-04"


def test_extractor_keeps_garden_waste_as_rag_intent() -> None:
    extractor = HeuristicExtractor()
    result = extractor.extract("How do I order a garden waste bin?")
    assert result.intent == Intent.RAG_QA
