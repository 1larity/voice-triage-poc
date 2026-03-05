"""Twilio client wrapper.

This module provides a lazy-loaded Twilio client wrapper.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class TwilioClient:
    """Lazy-loaded Twilio client wrapper.

    This class wraps the Twilio client to provide lazy loading
    and error handling for the Twilio SDK.
    """

    def __init__(self, account_sid: str, auth_token: str) -> None:
        """Initialize the Twilio client wrapper.

        Args:
            account_sid: Twilio Account SID.
            auth_token: Twilio Auth Token.
        """
        self._account_sid = account_sid
        self._auth_token = auth_token
        self._client: Any = None

    def _get_client(self) -> Any:
        """Get or create the Twilio client lazily.

        Returns:
            The Twilio Client instance.

        Raises:
            RuntimeError: If the twilio package is not installed.
        """
        if self._client is None:
            try:
                from twilio.rest import Client

                self._client = Client(
                    self._account_sid,
                    self._auth_token,
                )
            except ImportError as exc:
                raise RuntimeError(
                    "twilio package is required for Twilio integration. "
                    "Install it with: pip install twilio"
                ) from exc
        return self._client

    @property
    def calls(self) -> Any:
        """Access the Twilio calls API.

        Returns:
            Twilio calls API.
        """
        return self._get_client().calls

    def get_call(self, call_sid: str) -> Any:
        """Get a specific call by SID.

        Args:
            call_sid: The Twilio Call SID.

        Returns:
            The call object.
        """
        return self._get_client().calls(call_sid)

    def create_call(
        self,
        to: str,
        from_: str,
        url: str | None = None,
        status_callback: str | None = None,
        status_callback_event: list[str] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Create an outbound call.

        Args:
            to: Destination phone number.
            from_: Source phone number.
            url: URL for TwiML.
            status_callback: URL for status callbacks.
            status_callback_event: Events to trigger callback.
            **kwargs: Additional parameters.

        Returns:
            The created call object.
        """
        params: dict[str, Any] = {
            "to": to,
            "from_": from_,
        }
        if url:
            params["url"] = url
        if status_callback:
            params["status_callback"] = status_callback
        if status_callback_event:
            params["status_callback_event"] = status_callback_event
        params.update(kwargs)
        return self._get_client().calls.create(**params)

    def update_call(
        self,
        call_sid: str,
        status: str | None = None,
        twiml: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Update a call.

        Args:
            call_sid: The Twilio Call SID.
            status: New status for the call.
            twiml: TwiML to execute.
            **kwargs: Additional parameters.

        Returns:
            The updated call object.
        """
        params: dict[str, Any] = {}
        if status:
            params["status"] = status
        if twiml:
            params["twiml"] = twiml
        params.update(kwargs)
        return self._get_client().calls(call_sid).update(**params)

    def hangup_call(self, call_sid: str) -> Any:
        """Hang up a call.

        Args:
            call_sid: The Twilio Call SID.

        Returns:
            The updated call object.
        """
        return self.update_call(call_sid, status="completed")

    def play_audio(
        self,
        call_sid: str,
        audio_url: str,
        loop: bool = False,
    ) -> Any:
        """Play audio into a call.

        Args:
            call_sid: The Twilio Call SID.
            audio_url: URL of the audio to play.
            loop: Whether to loop the audio.

        Returns:
            The updated call object.
        """
        loop_attr = "1" if not loop else "0"
        twiml = f'<Response><Play loop="{loop_attr}">{audio_url}</Play></Response>'
        return self.update_call(call_sid, twiml=twiml)

    def send_digits(self, call_sid: str, digits: str) -> Any:
        """Send DTMF digits into a call.

        Args:
            call_sid: The Twilio Call SID.
            digits: DTMF digits to send.

        Returns:
            The updated call object.
        """
        twiml = f'<Response><Play digits="{digits}"/></Response>'
        return self.update_call(call_sid, twiml=twiml)
