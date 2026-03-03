"""app.conversation module."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4

from voice_triage.nlu.extractor import Extractor
from voice_triage.nlu.schemas import ExtractionResult
from voice_triage.rag.answer import RagService
from voice_triage.workflows.council_tax import CouncilTaxHandler
from voice_triage.workflows.electoral_register import ElectoralRegisterHandler
from voice_triage.workflows.move_home import MoveHomeHandler
from voice_triage.workflows.router import Route, decide_route


class ConversationStage(StrEnum):
    """Conversationstage."""

    ASK_ISSUE = "ASK_ISSUE"
    ASK_CURRENT_ADDRESS = "ASK_CURRENT_ADDRESS"
    CONFIRM_CURRENT_ADDRESS = "CONFIRM_CURRENT_ADDRESS"
    ASK_CURRENT_POSTCODE = "ASK_CURRENT_POSTCODE"
    ASK_NEW_ADDRESS = "ASK_NEW_ADDRESS"
    CONFIRM_NEW_ADDRESS = "CONFIRM_NEW_ADDRESS"
    ASK_NEW_POSTCODE = "ASK_NEW_POSTCODE"
    ASK_MOVE_DATE = "ASK_MOVE_DATE"
    CONFIRM = "CONFIRM"
    DONE = "DONE"


@dataclass
class ConversationState:
    """Conversationstate."""

    session_id: str
    route: Route = Route.RAG_QA
    stage: ConversationStage = ConversationStage.ASK_ISSUE
    move_fields: dict[str, str] = field(default_factory=dict)
    pending_address_kind: str | None = None
    pending_address_value: str | None = None
    pending_postcode_value: str | None = None
    current_address_verified: bool = False
    new_address_verified: bool = False
    turn_count: int = 0


@dataclass(frozen=True)
class ConversationTurnResult:
    """Conversationturnresult."""

    extraction: ExtractionResult
    route: Route
    stage: ConversationStage
    response_text: str
    outcome: dict[str, Any]


class ConversationEngine:
    """Stateful multi-turn router for web chat-like conversations."""

    OPENING_PROMPTS: tuple[str, ...] = (
        "Hello, how can I help you today?",
        "Hi there, what would you like to talk about?",
        "Good to speak with you. What can I do for you?",
        "Hello, I'm listening. What do you need help with?",
        "Hi, tell me what you need and we can take it step by step.",
    )
    ACKNOWLEDGEMENT_RESPONSES: tuple[str, ...] = (
        "You're welcome. What else can I help with?",
        "No problem. What would you like to ask next?",
        "Glad that helped. Anything else I can help with?",
    )
    SPOKEN_NUMBER_TOKENS: frozenset[str] = frozenset(
        {
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
            "eleven",
            "twelve",
            "thirteen",
            "fourteen",
            "fifteen",
            "sixteen",
            "seventeen",
            "eighteen",
            "nineteen",
            "twenty",
            "thirty",
            "forty",
            "fifty",
            "sixty",
            "seventy",
            "eighty",
            "ninety",
            "hundred",
        }
    )
    ADDRESS_STREET_TOKENS: frozenset[str] = frozenset(
        {
            "street",
            "st",
            "road",
            "rd",
            "avenue",
            "ave",
            "lane",
            "ln",
            "close",
            "cl",
            "drive",
            "dr",
            "place",
            "pl",
            "court",
            "ct",
            "way",
            "terrace",
            "crescent",
            "grove",
            "gardens",
            "parade",
            "hill",
        }
    )

    def __init__(
        self,
        extractor: Extractor,
        rag_service: RagService,
        move_home_handler: MoveHomeHandler | None = None,
        electoral_handler: ElectoralRegisterHandler | None = None,
        council_tax_handler: CouncilTaxHandler | None = None,
    ) -> None:
        """init  ."""
        self.extractor = extractor
        self.rag_service = rag_service
        self.move_home_handler = move_home_handler or MoveHomeHandler()
        self.electoral_handler = electoral_handler or ElectoralRegisterHandler()
        self.council_tax_handler = council_tax_handler or CouncilTaxHandler()
        self.sessions: dict[str, ConversationState] = {}

    def create_session(self) -> tuple[str, str]:
        """Create session."""
        session_id = str(uuid4())
        self.sessions[session_id] = ConversationState(session_id=session_id)
        greeting = random.choice(self.OPENING_PROMPTS)
        return session_id, greeting

    def process_turn(self, session_id: str, transcript: str) -> ConversationTurnResult:
        """Process turn."""
        state = self.sessions.get(session_id)
        if state is None:
            raise KeyError(f"Unknown session_id: {session_id}")

        state.turn_count += 1
        extraction = self.extractor.extract(transcript)
        route_hint = decide_route(extraction)

        if route_hint == Route.MOVE_HOME and (
            state.route != Route.MOVE_HOME or state.stage == ConversationStage.DONE
        ):
            state.route = Route.MOVE_HOME
            state.stage = ConversationStage.ASK_CURRENT_ADDRESS
            state.move_fields.clear()
            state.pending_address_kind = None
            state.pending_address_value = None
            state.pending_postcode_value = None
            state.current_address_verified = False
            state.new_address_verified = False
        elif state.route == Route.MOVE_HOME and state.stage == ConversationStage.DONE:
            state.route = Route.RAG_QA
            state.stage = ConversationStage.ASK_ISSUE
            state.move_fields.clear()
            state.pending_address_kind = None
            state.pending_address_value = None
            state.pending_postcode_value = None
            state.current_address_verified = False
            state.new_address_verified = False
        elif state.route != Route.MOVE_HOME:
            state.route = route_hint

        if state.route == Route.MOVE_HOME:
            return self._handle_move_home_turn(state, extraction)
        if state.route == Route.ELECTORAL_REGISTER:
            return self._handle_stub_turn(state, extraction, workflow="electoral_register")
        if state.route == Route.COUNCIL_TAX:
            return self._handle_stub_turn(state, extraction, workflow="council_tax")
        return self._handle_rag_turn(state, extraction)

    def _handle_rag_turn(
        self, state: ConversationState, extraction: ExtractionResult
    ) -> ConversationTurnResult:
        """handle rag turn."""
        state.stage = ConversationStage.ASK_ISSUE
        if self._is_acknowledgement(extraction.raw_text):
            answer_text = random.choice(self.ACKNOWLEDGEMENT_RESPONSES)
            rag_meta = {"used_kb": False, "reason": "acknowledgement"}
        else:
            answer_text, rag_meta = self.rag_service.answer(extraction.raw_text)
        outcome = {
            "workflow": "rag_qa",
            "stage": ConversationStage.DONE.value,
            "stages": [ConversationStage.ASK_ISSUE.value, ConversationStage.DONE.value],
            "rag": rag_meta,
            "turn_count": state.turn_count,
        }
        return ConversationTurnResult(
            extraction=extraction,
            route=state.route,
            stage=ConversationStage.DONE,
            response_text=answer_text,
            outcome=outcome,
        )

    def _handle_stub_turn(
        self, state: ConversationState, extraction: ExtractionResult, workflow: str
    ) -> ConversationTurnResult:
        """handle stub turn."""
        if workflow == "electoral_register":
            response_text, workflow_outcome = self.electoral_handler.run({})
        else:
            response_text, workflow_outcome = self.council_tax_handler.run({})

        state.route = Route.RAG_QA
        state.stage = ConversationStage.ASK_ISSUE
        outcome = {
            "workflow": workflow,
            "stage": ConversationStage.DONE.value,
            "workflow_outcome": workflow_outcome,
            "turn_count": state.turn_count,
        }
        return ConversationTurnResult(
            extraction=extraction,
            route=Route.RAG_QA,
            stage=ConversationStage.DONE,
            response_text=response_text,
            outcome=outcome,
        )

    def _handle_move_home_turn(
        self, state: ConversationState, extraction: ExtractionResult
    ) -> ConversationTurnResult:
        """handle move home turn."""
        raw_text = extraction.raw_text.strip()

        if state.stage == ConversationStage.ASK_CURRENT_ADDRESS:
            address = self._extract_address_candidate(raw_text, extraction)
            if not address:
                return self._move_result(
                    state,
                    extraction,
                    "Please tell me your current address.",
                    status="awaiting_current_address",
                )
            state.pending_address_kind = "current_address"
            state.pending_address_value = address
            state.pending_postcode_value = extraction.postcode
            state.stage = ConversationStage.CONFIRM_CURRENT_ADDRESS
            return self._move_result(
                state,
                extraction,
                f"I heard your current address as {address}, is that correct, yes or no?",
                status="confirming_current_address",
            )

        if state.stage == ConversationStage.CONFIRM_CURRENT_ADDRESS:
            if self._is_affirmative(raw_text):
                confirmed = state.pending_address_value
                if confirmed:
                    state.move_fields["current_address"] = confirmed
                    state.current_address_verified = True
                if state.pending_postcode_value:
                    state.move_fields["current_postcode"] = state.pending_postcode_value
                state.pending_address_kind = None
                state.pending_address_value = None
                state.pending_postcode_value = None
                if state.move_fields.get("current_postcode"):
                    state.stage = ConversationStage.ASK_NEW_ADDRESS
                    next_prompt = "Thanks. What is your new address?"
                    next_status = "collecting_new_address"
                else:
                    state.stage = ConversationStage.ASK_CURRENT_POSTCODE
                    next_prompt = "Thanks. Please tell me your current postcode."
                    next_status = "awaiting_current_postcode"
                return self._move_result(
                    state,
                    extraction,
                    next_prompt,
                    status=next_status,
                )
            if self._is_negative(raw_text):
                state.pending_address_kind = None
                state.pending_address_value = None
                state.pending_postcode_value = None
                state.current_address_verified = False
                state.stage = ConversationStage.ASK_CURRENT_ADDRESS
                return self._move_result(
                    state,
                    extraction,
                    "No problem. Please say your current address again.",
                    status="awaiting_current_address",
                )
            return self._move_result(
                state,
                extraction,
                "I just need a yes or no, is the current address correct?",
                status="confirming_current_address",
            )

        if state.stage == ConversationStage.ASK_CURRENT_POSTCODE:
            postcode = extraction.postcode
            if not postcode:
                return self._move_result(
                    state,
                    extraction,
                    "Please provide your current postcode, for example BN1 4AB.",
                    status="awaiting_current_postcode",
                )
            state.move_fields["current_postcode"] = postcode
            state.stage = ConversationStage.ASK_NEW_ADDRESS
            return self._move_result(
                state,
                extraction,
                "Great, now tell me your new address.",
                status="collecting_new_address",
            )

        if state.stage == ConversationStage.ASK_NEW_ADDRESS:
            address = self._extract_address_candidate(raw_text, extraction)
            if not address:
                return self._move_result(
                    state,
                    extraction,
                    "Please tell me your new address.",
                    status="awaiting_new_address",
                )
            state.pending_address_kind = "new_address"
            state.pending_address_value = address
            state.pending_postcode_value = extraction.postcode
            state.stage = ConversationStage.CONFIRM_NEW_ADDRESS
            return self._move_result(
                state,
                extraction,
                f"I heard your new address as {address}, is that correct, yes or no?",
                status="confirming_new_address",
            )

        if state.stage == ConversationStage.CONFIRM_NEW_ADDRESS:
            if self._is_affirmative(raw_text):
                confirmed = state.pending_address_value
                if confirmed:
                    state.move_fields["new_address"] = confirmed
                    state.new_address_verified = True
                if state.pending_postcode_value:
                    state.move_fields["new_postcode"] = state.pending_postcode_value
                state.pending_address_kind = None
                state.pending_address_value = None
                state.pending_postcode_value = None
                if state.move_fields.get("new_postcode"):
                    state.stage = ConversationStage.ASK_MOVE_DATE
                    next_prompt = "Great. What is your move date? You can say it like 2026-04-20."
                    next_status = "collecting_move_date"
                else:
                    state.stage = ConversationStage.ASK_NEW_POSTCODE
                    next_prompt = "Great. Please tell me your new postcode."
                    next_status = "awaiting_new_postcode"
                return self._move_result(
                    state,
                    extraction,
                    next_prompt,
                    status=next_status,
                )
            if self._is_negative(raw_text):
                state.pending_address_kind = None
                state.pending_address_value = None
                state.pending_postcode_value = None
                state.new_address_verified = False
                state.stage = ConversationStage.ASK_NEW_ADDRESS
                return self._move_result(
                    state,
                    extraction,
                    "No problem. Please say your new address again.",
                    status="awaiting_new_address",
                )
            return self._move_result(
                state,
                extraction,
                "I just need a yes or no, is the new address correct?",
                status="confirming_new_address",
            )

        if state.stage == ConversationStage.ASK_NEW_POSTCODE:
            postcode = extraction.postcode
            if not postcode:
                return self._move_result(
                    state,
                    extraction,
                    "Please provide your new postcode, for example BN1 4AB.",
                    status="awaiting_new_postcode",
                )
            state.move_fields["new_postcode"] = postcode
            state.stage = ConversationStage.ASK_MOVE_DATE
            return self._move_result(
                state,
                extraction,
                "Great. What is your move date? You can say it like 2026-04-20.",
                status="collecting_move_date",
            )

        if state.stage == ConversationStage.ASK_MOVE_DATE:
            move_date = extraction.move_date
            if not move_date:
                return self._move_result(
                    state,
                    extraction,
                    "I did not catch the move date. Please say it again.",
                    status="awaiting_move_date",
                )
            state.move_fields["move_date"] = move_date
            state.stage = ConversationStage.CONFIRM
            summary = (
                "Please confirm your details: "
                f"current address {state.move_fields.get('current_address')} "
                f"{state.move_fields.get('current_postcode')}, "
                f"new address {state.move_fields.get('new_address')} "
                f"{state.move_fields.get('new_postcode')}, "
                f"move date {state.move_fields.get('move_date')}. "
                "Say yes to submit or no to restart."
            )
            return self._move_result(
                state,
                extraction,
                summary,
                status="awaiting_confirmation",
            )

        if state.stage == ConversationStage.CONFIRM:
            if self._is_affirmative(raw_text):
                response_text, workflow_outcome = self.move_home_handler.run(state.move_fields)
                state.stage = ConversationStage.DONE
                return self._move_result(
                    state,
                    extraction,
                    response_text,
                    status=workflow_outcome.get("status", "submitted"),
                    workflow_outcome=workflow_outcome,
                )
            if self._is_negative(raw_text):
                state.move_fields.clear()
                state.pending_address_kind = None
                state.pending_address_value = None
                state.pending_postcode_value = None
                state.current_address_verified = False
                state.new_address_verified = False
                state.stage = ConversationStage.ASK_CURRENT_ADDRESS
                return self._move_result(
                    state,
                    extraction,
                    "No problem. Let's restart. What is your current address?",
                    status="restarted",
                )
            return self._move_result(
                state,
                extraction,
                "Please say yes to submit or no to restart.",
                status="awaiting_confirmation",
            )

        state.route = Route.RAG_QA
        state.stage = ConversationStage.ASK_ISSUE
        return self._handle_rag_turn(state, extraction)

    def _move_result(
        self,
        state: ConversationState,
        extraction: ExtractionResult,
        response_text: str,
        status: str,
        workflow_outcome: dict[str, Any] | None = None,
    ) -> ConversationTurnResult:
        """move result."""
        outcome = {
            "workflow": "move_home",
            "status": status,
            "stage": state.stage.value,
            "stages": [
                ConversationStage.ASK_CURRENT_ADDRESS.value,
                ConversationStage.CONFIRM_CURRENT_ADDRESS.value,
                ConversationStage.ASK_CURRENT_POSTCODE.value,
                ConversationStage.ASK_NEW_ADDRESS.value,
                ConversationStage.CONFIRM_NEW_ADDRESS.value,
                ConversationStage.ASK_NEW_POSTCODE.value,
                ConversationStage.ASK_MOVE_DATE.value,
                ConversationStage.CONFIRM.value,
                ConversationStage.DONE.value,
            ],
            "collected_fields": dict(state.move_fields),
            "captured_data": {
                "current_address": state.move_fields.get("current_address"),
                "current_postcode": state.move_fields.get("current_postcode"),
                "new_address": state.move_fields.get("new_address"),
                "new_postcode": state.move_fields.get("new_postcode"),
                "move_date": state.move_fields.get("move_date"),
                "current_address_verified": state.current_address_verified,
                "new_address_verified": state.new_address_verified,
            },
            "turn_count": state.turn_count,
        }
        if workflow_outcome is not None:
            outcome["workflow_outcome"] = workflow_outcome

        return ConversationTurnResult(
            extraction=extraction,
            route=state.route,
            stage=state.stage,
            response_text=response_text,
            outcome=outcome,
        )

    @classmethod
    def _extract_address_candidate(cls, text: str, extraction: ExtractionResult) -> str | None:
        """extract address candidate."""
        candidate = extraction.address_line or text
        normalized = " ".join(candidate.split()).strip(" ,.-")
        if len(normalized) < 8:
            return None

        has_number = any(char.isdigit() for char in normalized)
        has_alpha = any(char.isalpha() for char in normalized)
        has_postcode = extraction.postcode is not None
        tokens = cls._normalized_tokens(normalized)
        has_spoken_number = any(token in cls.SPOKEN_NUMBER_TOKENS for token in tokens)
        has_street_hint = any(token in cls.ADDRESS_STREET_TOKENS for token in tokens)
        has_spoken_number_address = has_spoken_number and has_street_hint
        lowered = normalized.lower()
        invalid_phrases = {
            "not sure",
            "no idea",
            "unknown",
            "none",
            "n a",
            "na",
            "idk",
        }
        if lowered in invalid_phrases:
            return None

        if not (
            (has_alpha and has_number) or has_postcode or (has_alpha and has_spoken_number_address)
        ):
            return None
        return normalized

    @staticmethod
    def _normalized_tokens(text: str) -> list[str]:
        """normalized tokens."""
        normalized = re.sub(r"[^a-z0-9\s']", " ", text.lower())
        return [token for token in normalized.split() if token]

    @classmethod
    def _is_affirmative(cls, text: str) -> bool:
        """is affirmative."""
        tokens = cls._normalized_tokens(text)
        if not tokens:
            return False
        phrase = " ".join(tokens)
        positives = {
            "yes",
            "yeah",
            "yep",
            "y",
            "correct",
            "confirm",
            "confirmed",
            "that's right",
            "thats right",
            "that is right",
        }
        if phrase in positives:
            return True
        return tokens[0] in {"yes", "yeah", "yep", "correct", "confirm", "confirmed", "y"}

    @classmethod
    def _is_negative(cls, text: str) -> bool:
        """is negative."""
        tokens = cls._normalized_tokens(text)
        if not tokens:
            return False
        phrase = " ".join(tokens)
        negatives = {
            "no",
            "n",
            "nope",
            "wrong",
            "incorrect",
            "restart",
            "start again",
            "that's wrong",
            "thats wrong",
            "not correct",
        }
        if phrase in negatives:
            return True
        return tokens[0] in {"no", "nope", "wrong", "incorrect", "restart", "n"}

    @classmethod
    def _is_acknowledgement(cls, text: str) -> bool:
        """is acknowledgement."""
        tokens = cls._normalized_tokens(text)
        if not tokens:
            return False
        phrase = " ".join(tokens)
        acknowledgements = {
            "ok",
            "okay",
            "cool",
            "great",
            "nice",
            "thanks",
            "thank you",
            "cheers",
            "got it",
            "understood",
        }
        return phrase in acknowledgements
