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


def test_extractor_parses_two_digit_year_in_current_century_window() -> None:
    extractor = HeuristicExtractor()
    result = extractor.extract("Move date: 04/04/26")
    assert result.move_date == "2026-04-04"


def test_extractor_parses_two_digit_year_in_previous_century_when_far_future() -> None:
    extractor = HeuristicExtractor()
    result = extractor.extract("Move date: 04/04/99")
    assert result.move_date == "1999-04-04"


def test_extractor_keeps_garden_waste_as_rag_intent() -> None:
    extractor = HeuristicExtractor()
    result = extractor.extract("How do I order a garden waste bin?")
    assert result.intent == Intent.RAG_QA
