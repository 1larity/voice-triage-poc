"""Zoom Phone call control response generation.

This module provides functions for generating Zoom Phone call control
responses in JSON format.
"""

from __future__ import annotations

import json
from typing import Any


def generate_call_control_response(
    session_id: str,
    welcome_message: str | None = None,
    gather_speech: bool = True,
    action_url: str | None = None,
    language: str = "en-GB",
    voice: str = "en-GB-Standard-A",
    speech_timeout: int = 5,
) -> str:
    """Generate a Zoom Phone call control response.

    Zoom Phone uses a JSON-based call control format.

    Args:
        session_id: Session ID for this conversation.
        welcome_message: Optional welcome message to play.
        gather_speech: Whether to gather speech input.
        action_url: URL to post gathered input to.
        language: Language code for TTS and speech recognition.
        voice: Voice identifier for TTS.
        speech_timeout: Timeout for speech gathering in seconds.

    Returns:
        JSON response for Zoom Phone call control.
    """
    actions: list[dict[str, Any]] = []

    # Add welcome message using text-to-speech
    if welcome_message:
        actions.append(generate_say_action(welcome_message, voice, language))

    # Add speech gathering
    if gather_speech and action_url:
        actions.append(generate_gather_action(
            action_url=action_url,
            language=language,
            timeout=speech_timeout,
        ))

    return json.dumps({"session_id": session_id, "actions": actions})


def generate_say_action(
    text: str,
    voice: str = "en-GB-Standard-A",
    language: str = "en-GB",
) -> dict[str, Any]:
    """Generate a say/TTS action for Zoom Phone.

    Args:
        text: Text to speak.
        voice: Voice identifier.
        language: Language code.

    Returns:
        Say action dictionary.
    """
    return {
        "action": "say",
        "text": text,
        "voice": voice,
        "language": language,
    }


def generate_play_action(
    audio_url: str,
    loop: bool = False,
) -> dict[str, Any]:
    """Generate a play action for Zoom Phone.

    Args:
        audio_url: URL of the audio to play.
        loop: Whether to loop the audio.

    Returns:
        Play action dictionary.
    """
    action: dict[str, Any] = {
        "action": "play",
        "url": audio_url,
    }
    if loop:
        action["loop"] = True
    return action


def generate_gather_action(
    action_url: str,
    input_types: list[str] | None = None,
    language: str = "en-GB",
    timeout: int = 5,
    num_digits: int | None = None,
    finish_on_key: str | None = None,
) -> dict[str, Any]:
    """Generate a gather action for Zoom Phone.

    Args:
        action_url: URL to post gathered input to.
        input_types: List of input types (speech, dtmf).
        language: Language code for speech recognition.
        timeout: Timeout in seconds.
        num_digits: Number of digits to gather (for DTMF).
        finish_on_key: Key to finish gathering (for DTMF).

    Returns:
        Gather action dictionary.
    """
    if input_types is None:
        input_types = ["speech"]

    action: dict[str, Any] = {
        "action": "gather",
        "url": action_url,
        "method": "POST",
        "input": input_types,
    }

    if "speech" in input_types:
        action["speech"] = {
            "language": language,
            "timeout": timeout,
        }

    if "dtmf" in input_types:
        if num_digits:
            action["num_digits"] = num_digits
        if finish_on_key:
            action["finish_on_key"] = finish_on_key

    return action


def generate_hangup_action() -> dict[str, Any]:
    """Generate a hangup action for Zoom Phone.

    Returns:
        Hangup action dictionary.
    """
    return {"action": "hangup"}


def generate_transfer_action(
    transfer_to: str,
    transfer_type: str = "blind",
    callback_url: str | None = None,
) -> dict[str, Any]:
    """Generate a transfer action for Zoom Phone.

    Args:
        transfer_to: Destination number or extension.
        transfer_type: Type of transfer (blind, attended).
        callback_url: URL for transfer status callbacks.

    Returns:
        Transfer action dictionary.
    """
    action: dict[str, Any] = {
        "action": "transfer",
        "to": transfer_to,
        "transfer_type": transfer_type,
    }
    if callback_url:
        action["callback_url"] = callback_url
    return action


def response_to_json(response: dict[str, Any]) -> str:
    """Convert a response dictionary to JSON string.

    Args:
        response: Response dictionary.

    Returns:
        JSON string.
    """
    return json.dumps(response)
