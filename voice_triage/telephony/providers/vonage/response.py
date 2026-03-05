"""NCCO response generation utilities for Vonage.

This module provides functions for generating NCCO (Nexmo Call Control Object)
responses for various call scenarios.
"""

from __future__ import annotations

import json
from typing import Any


def generate_talk_ncco(
    text: str,
    voice_name: str = "Amy",
    language: str = "en-GB",
) -> dict[str, Any]:
    """Generate a talk action NCCO.

    Args:
        text: Text to speak.
        voice_name: Voice to use (default: Amy, British English).
        language: Language code (default: en-GB).

    Returns:
        NCCO action dictionary.
    """
    return {
        "action": "talk",
        "text": text,
        "voiceName": voice_name,
        "language": language,
    }


def generate_stream_ncco(
    stream_url: str | list[str],
    loop: int = 1,
) -> dict[str, Any]:
    """Generate a stream action NCCO for audio playback.

    Args:
        stream_url: URL(s) of audio to stream.
        loop: Number of times to loop (0 = infinite).

    Returns:
        NCCO action dictionary.
    """
    urls = [stream_url] if isinstance(stream_url, str) else stream_url
    return {
        "action": "stream",
        "streamUrl": urls,
        "loop": loop,
    }


def generate_input_ncco(
    event_url: str,
    uuid: str | list[str] | None = None,
    speech_timeout: int = 5,
    end_on_silence: int = 2,
    language: str = "en-GB",
) -> dict[str, Any]:
    """Generate an input action NCCO for speech gathering.

    Args:
        event_url: URL to post speech results to.
        uuid: Call UUID(s) for speech recognition.
        speech_timeout: Seconds to wait for speech.
        end_on_silence: Seconds of silence to end recording.
        language: Speech recognition language.

    Returns:
        NCCO action dictionary.
    """
    ncco: dict[str, Any] = {
        "action": "input",
        "eventUrl": [event_url],
        "type": ["speech"],
        "speech": {
            "language": language,
            "endOnSilence": end_on_silence,
            "speechTimeout": speech_timeout,
        },
    }
    if uuid:
        ncco["speech"]["uuid"] = [uuid] if isinstance(uuid, str) else uuid
    return ncco


def generate_connect_ncco(
    endpoint: dict[str, Any] | list[dict[str, Any]],
    from_number: str | None = None,
) -> dict[str, Any]:
    """Generate a connect action NCCO.

    Args:
        endpoint: Endpoint configuration(s).
        from_number: Optional from number for the call.

    Returns:
        NCCO action dictionary.
    """
    ncco: dict[str, Any] = {
        "action": "connect",
        "endpoint": [endpoint] if isinstance(endpoint, dict) else endpoint,
    }
    if from_number:
        ncco["from"] = from_number
    return ncco


def generate_answer_ncco(
    welcome_message: str | None = None,
    gather_speech: bool = True,
    action_url: str | None = None,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    """Generate NCCO for answering an inbound call.

    Args:
        welcome_message: Optional welcome message to speak.
        gather_speech: Whether to gather speech input.
        action_url: URL to post gathered input to.
        session_id: Session ID for speech recognition.

    Returns:
        List of NCCO actions.
    """
    ncco: list[dict[str, Any]] = []

    # Add welcome message
    if welcome_message:
        ncco.append(generate_talk_ncco(welcome_message))

    # Add speech input gathering
    if gather_speech and action_url:
        ncco.append(generate_input_ncco(
            event_url=action_url,
            uuid=session_id,
        ))

    return ncco


def generate_transfer_ncco(
    destination: str,
    from_number: str | None = None,
) -> dict[str, Any]:
    """Generate a connect action NCCO for phone transfer.

    Args:
        destination: Phone number to transfer to.
        from_number: Optional from number for the call.

    Returns:
        NCCO action dictionary.
    """
    return generate_connect_ncco(
        endpoint={"type": "phone", "number": destination.lstrip("+")},
        from_number=from_number,
    )


def generate_websocket_ncco(
    websocket_url: str,
    sample_rate: int = 8000,
    from_number: str | None = None,
) -> dict[str, Any]:
    """Generate a connect action NCCO for WebSocket streaming.

    Args:
        websocket_url: WebSocket URL to connect to.
        sample_rate: Audio sample rate.
        from_number: Optional from number for the call.

    Returns:
        NCCO action dictionary.
    """
    return generate_connect_ncco(
        endpoint={
            "type": "websocket",
            "uri": websocket_url,
            "contentType": f"audio/l16;rate={sample_rate}",
        },
        from_number=from_number,
    )


def generate_gather_ncco(
    prompt: str,
    action_url: str,
    timeout: int = 5,
    language: str = "en-GB",
    voice_name: str = "Amy",
) -> list[dict[str, Any]]:
    """Generate NCCO sequence for prompting and gathering speech.

    Args:
        prompt: Text to speak before gathering.
        action_url: URL to post speech results to.
        timeout: Seconds to wait for speech.
        language: Speech recognition language.
        voice_name: Voice to use for prompt.

    Returns:
        List of NCCO actions.
    """
    return [
        generate_talk_ncco(prompt, voice_name=voice_name, language=language),
        generate_input_ncco(
            event_url=action_url,
            speech_timeout=timeout,
            language=language,
        ),
    ]


def ncco_to_json(ncco: list[dict[str, Any]]) -> str:
    """Convert NCCO list to JSON string.

    Args:
        ncco: List of NCCO action dictionaries.

    Returns:
        JSON string representation.
    """
    return json.dumps(ncco)
