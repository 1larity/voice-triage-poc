"""SIP call control response generation.

This module provides functions for generating SIP gateway call control
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
) -> str:
    """Generate a SIP gateway call control response.

    For SIP trunking, this generates a JSON response that the
    SIP gateway can interpret for call control.

    Args:
        session_id: Session ID for this conversation.
        welcome_message: Optional welcome message to play.
        gather_speech: Whether to gather speech input.
        action_url: URL to post gathered input to.
        language: Language code for TTS and speech recognition.

    Returns:
        JSON response string for SIP gateway call control.
    """
    response: dict[str, Any] = {
        "session_id": session_id,
        "actions": [],
    }

    if welcome_message:
        response["actions"].append({
            "type": "play_tts",
            "text": welcome_message,
            "language": language,
            "voice": "female",
        })

    if gather_speech and action_url:
        response["actions"].append({
            "type": "gather_speech",
            "action_url": action_url,
            "language": language,
            "timeout": 5,
            "silence_threshold": 2,
        })

    return json.dumps(response)


def generate_say_action(
    text: str,
    language: str = "en-GB",
    voice: str = "female",
) -> dict[str, Any]:
    """Generate a say/TTS action for SIP gateway.

    Args:
        text: Text to speak.
        language: Language code.
        voice: Voice identifier.

    Returns:
        Say action dictionary.
    """
    return {
        "type": "play_tts",
        "text": text,
        "language": language,
        "voice": voice,
    }


def generate_play_action(
    audio_url: str,
    loop: bool = False,
) -> dict[str, Any]:
    """Generate a play action for SIP gateway.

    Args:
        audio_url: URL of the audio to play.
        loop: Whether to loop the audio.

    Returns:
        Play action dictionary.
    """
    action: dict[str, Any] = {
        "type": "play_audio",
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
    """Generate a gather action for SIP gateway.

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
        "type": "gather",
        "action_url": action_url,
        "input": input_types,
        "timeout": timeout,
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
    """Generate a hangup action for SIP gateway.

    Returns:
        Hangup action dictionary.
    """
    return {"type": "hangup"}


def generate_transfer_action(
    transfer_to: str,
    transfer_type: str = "blind",
    callback_url: str | None = None,
) -> dict[str, Any]:
    """Generate a transfer action for SIP gateway.

    Args:
        transfer_to: Destination number or SIP URI.
        transfer_type: Type of transfer (blind, attended).
        callback_url: URL for transfer status callbacks.

    Returns:
        Transfer action dictionary.
    """
    action: dict[str, Any] = {
        "type": "transfer",
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
