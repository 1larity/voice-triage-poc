"""workflows.router module."""

from __future__ import annotations

from enum import StrEnum

from voice_triage.nlu.schemas import ExtractionResult, Intent


class Route(StrEnum):
    """Route."""

    RAG_QA = "RAG_QA"
    MOVE_HOME = "MOVE_HOME"
    ELECTORAL_REGISTER = "ELECTORAL_REGISTER"
    COUNCIL_TAX = "COUNCIL_TAX"


def route_from_transcript(transcript: str) -> Route:
    """Route from transcript."""
    lowered = transcript.lower()
    if any(keyword in lowered for keyword in ("move", "moving", "new address")):
        return Route.MOVE_HOME
    return Route.RAG_QA


def _should_use_stub_workflow(text: str) -> bool:
    """should use stub workflow."""
    lowered = text.lower()
    workflow_triggers = (
        "start workflow",
        "open case",
        "submit request",
        "action this",
        "process this",
        "run workflow",
    )
    return any(trigger in lowered for trigger in workflow_triggers)


def decide_route(extraction: ExtractionResult) -> Route:
    """Decide route."""
    if extraction.intent == Intent.MOVE_HOME:
        return Route.MOVE_HOME
    if extraction.intent == Intent.ELECTORAL_REGISTER:
        if _should_use_stub_workflow(extraction.raw_text):
            return Route.ELECTORAL_REGISTER
        return Route.RAG_QA
    if extraction.intent == Intent.COUNCIL_TAX:
        if _should_use_stub_workflow(extraction.raw_text):
            return Route.COUNCIL_TAX
        return Route.RAG_QA
    return route_from_transcript(extraction.raw_text)
