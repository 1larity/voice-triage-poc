"""app.orchestrator module."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from voice_triage.nlu.extractor import Extractor
from voice_triage.nlu.schemas import CallSessionRecord, ExtractionResult
from voice_triage.rag.answer import RagService
from voice_triage.workflows.move_home import MoveHomeHandler
from voice_triage.workflows.router import Route, decide_route


class Stage(StrEnum):
    """Stage."""

    ASK_ISSUE = "ASK_ISSUE"
    ASK_CURRENT_ADDRESS = "ASK_CURRENT_ADDRESS"
    ASK_NEW_ADDRESS = "ASK_NEW_ADDRESS"
    ASK_MOVE_DATE = "ASK_MOVE_DATE"
    CONFIRM = "CONFIRM"
    DONE = "DONE"


@dataclass(frozen=True)
class OrchestrationResult:
    """Orchestrationresult."""

    session: CallSessionRecord
    response_text: str


class SessionOrchestrator:
    """Coordinates extraction, route selection, and route-specific handling."""

    def __init__(
        self,
        extractor: Extractor,
        rag_service: RagService,
        move_home_handler: MoveHomeHandler | None = None,
    ) -> None:
        """init  ."""
        self.extractor = extractor
        self.rag_service = rag_service
        self.move_home_handler = move_home_handler or MoveHomeHandler()

    def process_turn(self, transcript: str) -> OrchestrationResult:
        """Process turn."""
        extraction = self.extractor.extract(transcript)
        route = decide_route(extraction)

        if route == Route.MOVE_HOME:
            updated_extraction, response, outcome = self._run_move_home_flow(extraction)
        else:
            response, rag_meta = self.rag_service.answer(transcript)
            updated_extraction = extraction
            outcome = {
                "workflow": "rag_qa",
                "stage": Stage.DONE.value,
                "stages": [Stage.ASK_ISSUE.value, Stage.DONE.value],
                "rag": rag_meta,
            }

        session = CallSessionRecord(
            started_at=datetime.now(tz=UTC),
            transcript=transcript,
            extracted=updated_extraction,
            route=route.value,
            outcome=outcome,
        )
        return OrchestrationResult(session=session, response_text=response)

    def _run_move_home_flow(
        self, extraction: ExtractionResult
    ) -> tuple[ExtractionResult, str, dict[str, Any]]:
        """run move home flow."""
        collected: dict[str, str] = {}
        stages = [
            Stage.ASK_CURRENT_ADDRESS.value,
            Stage.ASK_NEW_ADDRESS.value,
            Stage.ASK_MOVE_DATE.value,
            Stage.CONFIRM.value,
            Stage.DONE.value,
        ]

        if extraction.address_line:
            collected["current_address"] = extraction.address_line
        else:
            collected["current_address"] = input("What is your current address? ").strip()

        collected["new_address"] = input("What is your new address? ").strip()
        if extraction.move_date:
            collected["move_date"] = extraction.move_date
        else:
            collected["move_date"] = input("What is your move date? (DD/MM/YYYY) ").strip()

        confirmation = input("Confirm move details? (y/n): ").strip().lower()
        if confirmation not in {"y", "yes"}:
            outcome = {
                "workflow": "move_home",
                "stage": Stage.DONE.value,
                "status": "cancelled",
                "stages": stages,
                "collected_fields": collected,
            }
            return extraction, "Move-home request cancelled.", outcome

        response, workflow_outcome = self.move_home_handler.run(collected)
        updated_extraction = extraction.model_copy(
            update={
                "address_line": collected.get("current_address") or extraction.address_line,
                "move_date": collected.get("move_date") or extraction.move_date,
            }
        )
        outcome = {
            "workflow": "move_home",
            "stage": Stage.DONE.value,
            "status": workflow_outcome.get("status", "completed"),
            "stages": stages,
            "collected_fields": collected,
            "workflow_outcome": workflow_outcome,
        }
        return updated_extraction, response, outcome
