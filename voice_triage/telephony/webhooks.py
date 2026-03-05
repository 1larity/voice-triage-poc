"""Telephony webhook endpoints for FastAPI integration.

This module provides FastAPI router endpoints for handling webhooks
from various telephony providers (Twilio, Vonage, SIP).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse

from voice_triage.telephony.base import PhoneCall
from voice_triage.telephony.registry import TelephonyRegistry

logger = logging.getLogger(__name__)

# Default welcome message for inbound calls
DEFAULT_WELCOME_MESSAGE = (
    "Hello, and welcome to the council services helpline. How can I help you today?"
)


class TelephonyWebhookHandler:
    """Handler for telephony webhooks.

    This class processes incoming webhooks from telephony providers
    and integrates with the conversation engine.
    """

    def __init__(
        self,
        registry: TelephonyRegistry,
        conversation_handler: Any | None = None,
    ) -> None:
        """Initialize the webhook handler.

        Args:
            registry: Telephony provider registry.
            conversation_handler: Handler for processing conversations.
        """
        self.registry = registry
        self.conversation_handler = conversation_handler
        self._call_sessions: dict[str, str] = {}  # call_id -> session_id

    async def handle_inbound_call(
        self,
        provider_name: str,
        request: Request,
        background_tasks: BackgroundTasks,
    ) -> Response:
        """Handle an inbound call webhook.

        Args:
            provider_name: Name of the telephony provider.
            request: FastAPI request object.
            background_tasks: Background task queue.

        Returns:
            Response with call control markup (TwiML/NCCO/etc).
        """
        provider = self.registry.get(provider_name)
        if not provider:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_name}")

        # Get request body and headers
        body = await request.body()
        headers = dict(request.headers)
        path = request.url.path

        # Validate webhook
        if not await provider.validate_webhook(headers, body, path):
            logger.warning(f"Invalid webhook signature from {provider_name}")
            raise HTTPException(status_code=403, detail="Invalid webhook signature")

        # Parse form data
        content_type = headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                form_data = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                form_data = {}
        else:
            form_data = dict(request.query_params)

        # Parse the inbound call
        call = await provider.parse_inbound_call(headers, body, form_data)

        logger.info(
            f"Inbound call from {call.from_number} to {call.to_number} "
            f"(provider: {provider_name}, call_id: {call.call_id})"
        )

        # Create a new conversation session
        session_id = await self._create_session(call)
        self._call_sessions[call.call_id] = session_id

        # Generate response
        action_url = f"/telephony/{provider_name}/voice/{call.call_id}"
        response_markup = await provider.generate_twiml_response(
            session_id=session_id,
            welcome_message=DEFAULT_WELCOME_MESSAGE,
            gather_speech=True,
            action_url=action_url,
        )

        # Use provider's content type
        return Response(
            content=response_markup,
            media_type=provider.get_response_content_type(),
        )

    async def handle_speech_input(
        self,
        provider_name: str,
        call_id: str,
        request: Request,
    ) -> Response:
        """Handle speech input from a call.

        Args:
            provider_name: Name of the telephony provider.
            call_id: The call ID.
            request: FastAPI request object.

        Returns:
            Response with next action markup.
        """
        provider = self.registry.get(provider_name)
        if not provider:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_name}")

        # Get request body
        body = await request.body()
        headers = dict(request.headers)

        # Validate webhook
        if not await provider.validate_webhook(headers, body, request.url.path):
            raise HTTPException(status_code=403, detail="Invalid webhook signature")

        # Parse speech input based on provider
        content_type = headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                data = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                data = {}
        else:
            data = dict(request.query_params)

        # Extract transcript using provider's method
        transcript = provider.extract_transcript(data)

        if not transcript:
            # No speech detected, prompt again
            session_id = self._call_sessions.get(call_id, "")
            response_markup = await provider.generate_twiml_response(
                session_id=session_id,
                welcome_message="I didn't catch that. Could you please repeat?",
                gather_speech=True,
                action_url=f"/telephony/{provider_name}/voice/{call_id}",
            )
            return Response(
                content=response_markup,
                media_type=provider.get_response_content_type(),
            )

        logger.info(f"Speech input from call {call_id}: {transcript}")

        # Get session ID
        session_id = self._call_sessions.get(call_id) or call_id

        # Process the transcript through conversation engine
        response_text = await self._process_conversation(session_id, transcript)

        # Generate response with next action
        response_markup = await provider.generate_twiml_response(
            session_id=session_id,
            welcome_message=response_text,
            gather_speech=True,
            action_url=f"/telephony/{provider_name}/voice/{call_id}",
        )

        return Response(
            content=response_markup,
            media_type=provider.get_response_content_type(),
        )

    async def handle_call_status(
        self,
        provider_name: str,
        call_id: str,
        request: Request,
    ) -> Response:
        """Handle call status updates.

        Args:
            provider_name: Name of the telephony provider.
            call_id: The call ID.
            request: FastAPI request object.

        Returns:
            Acknowledgment response.
        """
        provider = self.registry.get(provider_name)
        if not provider:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_name}")

        body = await request.body()
        headers = dict(request.headers)

        # Parse status data
        content_type = headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                data = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                data = {}
        else:
            data = dict(request.query_params)

        status = data.get("CallStatus", data.get("status", "unknown"))
        logger.info(f"Call {call_id} status update: {status}")

        # Clean up session if call ended
        if status in ("completed", "failed", "no-answer", "canceled", "busy"):
            if call_id in self._call_sessions:
                del self._call_sessions[call_id]

        return PlainTextResponse("OK")

    async def _create_session(self, call: PhoneCall) -> str:
        """Create a new conversation session for a call.

        Args:
            call: The inbound phone call.

        Returns:
            Session ID.
        """
        if self.conversation_handler:
            # Use the conversation handler to create a session
            session_id = await self.conversation_handler.create_session(
                metadata={
                    "call_id": call.call_id,
                    "from_number": call.from_number,
                    "to_number": call.to_number,
                    "provider": call.provider,
                }
            )
            return session_id
        else:
            # Generate a simple session ID
            import uuid
            return str(uuid.uuid4())

    async def _process_conversation(self, session_id: str, transcript: str) -> str:
        """Process a conversation turn.

        Args:
            session_id: Session ID.
            transcript: User's speech transcript.

        Returns:
            Assistant response text.
        """
        if self.conversation_handler:
            return await self.conversation_handler.process_turn(
                session_id=session_id,
                transcript=transcript,
            )
        else:
            # Default response if no handler configured
            return "Thank you for your message. How else can I help you today?"


def create_telephony_router(
    handler: TelephonyWebhookHandler,
    prefix: str = "/telephony",
) -> APIRouter:
    """Create a FastAPI router for telephony webhooks.

    Args:
        handler: The webhook handler instance.
        prefix: URL prefix for all routes.

    Returns:
        FastAPI router.
    """
    router = APIRouter(prefix=prefix, tags=["telephony"])

    # Twilio endpoints
    @router.post("/twilio/voice")
    async def twilio_voice(
        request: Request,
        background_tasks: BackgroundTasks,
    ) -> Response:
        """Handle Twilio voice webhook."""
        return await handler.handle_inbound_call("twilio", request, background_tasks)

    @router.post("/twilio/voice/{call_id}")
    async def twilio_voice_input(call_id: str, request: Request) -> Response:
        """Handle Twilio speech input."""
        return await handler.handle_speech_input("twilio", call_id, request)

    @router.post("/twilio/status/{call_id}")
    async def twilio_status(call_id: str, request: Request) -> Response:
        """Handle Twilio status callback."""
        return await handler.handle_call_status("twilio", call_id, request)

    # Vonage/Nexmo endpoints
    @router.post("/vonage/voice")
    async def vonage_voice(
        request: Request,
        background_tasks: BackgroundTasks,
    ) -> Response:
        """Handle Vonage voice webhook."""
        return await handler.handle_inbound_call("vonage", request, background_tasks)

    @router.post("/vonage/voice/{call_id}")
    async def vonage_voice_input(call_id: str, request: Request) -> Response:
        """Handle Vonage speech input."""
        return await handler.handle_speech_input("vonage", call_id, request)

    @router.post("/vonage/event/{call_id}")
    async def vonage_event(call_id: str, request: Request) -> Response:
        """Handle Vonage event callback."""
        return await handler.handle_call_status("vonage", call_id, request)

    @router.post("/nexmo/voice")
    async def nexmo_voice(
        request: Request,
        background_tasks: BackgroundTasks,
    ) -> Response:
        """Handle Nexmo voice webhook (alias for Vonage)."""
        return await handler.handle_inbound_call("nexmo", request, background_tasks)

    # SIP/Gamma endpoints
    @router.post("/sip/voice")
    async def sip_voice(
        request: Request,
        background_tasks: BackgroundTasks,
    ) -> Response:
        """Handle SIP gateway voice webhook."""
        return await handler.handle_inbound_call("sip", request, background_tasks)

    @router.post("/sip/voice/{call_id}")
    async def sip_voice_input(call_id: str, request: Request) -> Response:
        """Handle SIP gateway speech input."""
        return await handler.handle_speech_input("sip", call_id, request)

    @router.post("/sip/status/{call_id}")
    async def sip_status(call_id: str, request: Request) -> Response:
        """Handle SIP gateway status callback."""
        return await handler.handle_call_status("sip", call_id, request)

    @router.post("/gamma/voice")
    async def gamma_voice(
        request: Request,
        background_tasks: BackgroundTasks,
    ) -> Response:
        """Handle Gamma Telecom voice webhook."""
        return await handler.handle_inbound_call("gamma", request, background_tasks)

    @router.post("/bt/voice")
    async def bt_voice(
        request: Request,
        background_tasks: BackgroundTasks,
    ) -> Response:
        """Handle BT voice webhook."""
        return await handler.handle_inbound_call("bt", request, background_tasks)

    # Health check
    @router.get("/health")
    async def telephony_health() -> dict[str, Any]:
        """Health check for telephony endpoints."""
        return {
            "status": "ok",
            "providers": handler.registry.list_registered(),
        }

    # List available providers
    @router.get("/providers")
    async def list_providers() -> dict[str, list[str]]:
        """List available telephony providers."""
        from voice_triage.telephony.registry import list_providers as get_all_providers
        return {"providers": get_all_providers()}

    return router


async def create_telephony_handler(
    conversation_handler: Any | None = None,
    provider_configs: dict[str, dict[str, Any]] | None = None,
) -> TelephonyWebhookHandler:
    """Create and configure a telephony webhook handler.

    Args:
        conversation_handler: Handler for processing conversations.
        provider_configs: Optional provider configurations.

    Returns:
        Configured TelephonyWebhookHandler instance.
    """
    from voice_triage.telephony.base import TelephonyConfig
    from voice_triage.telephony.registry import get_provider

    registry = TelephonyRegistry()

    # Register configured providers
    if provider_configs:
        for provider_name, config_dict in provider_configs.items():
            try:
                config = TelephonyConfig(provider_name=provider_name, **config_dict)
                provider = get_provider(config)
                registry.register(provider)
                logger.info(f"Registered telephony provider: {provider_name}")
            except Exception as exc:
                logger.warning(f"Failed to register provider {provider_name}: {exc}")

    return TelephonyWebhookHandler(
        registry=registry,
        conversation_handler=conversation_handler,
    )
