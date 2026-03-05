"""Twilio TwiML response generation.

This module provides utilities for generating TwiML responses
for Twilio voice calls.
"""

from __future__ import annotations

from xml.etree import ElementTree


def twiml_to_string(element: ElementTree.Element) -> str:
    """Convert ElementTree element to XML string.

    Args:
        element: The root XML element.

    Returns:
        XML string representation.
    """
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ElementTree.tostring(
        element, encoding="unicode"
    )


def generate_say_twiml(
    message: str,
    voice: str = "alice",
    language: str = "en-GB",
) -> ElementTree.Element:
    """Generate a Say TwiML element.

    Args:
        message: The message to speak.
        voice: Voice to use (default: alice).
        language: Language code (default: en-GB).

    Returns:
        ElementTree element for the Say verb.
    """
    say = ElementTree.Element("Say")
    say.set("voice", voice)
    say.set("language", language)
    say.text = message
    return say


def generate_gather_twiml(
    action_url: str,
    prompt: str | None = None,
    speech_timeout: str = "auto",
    language: str = "en-GB",
    speech_model: str = "phone_call",
) -> ElementTree.Element:
    """Generate a Gather TwiML element for speech input.

    Args:
        action_url: URL to post gathered speech to.
        prompt: Optional prompt to speak before gathering.
        speech_timeout: Speech timeout (default: auto).
        language: Language code (default: en-GB).
        speech_model: Speech model (default: phone_call).

    Returns:
        ElementTree element for the Gather verb.
    """
    gather = ElementTree.Element("Gather")
    gather.set("input", "speech")
    gather.set("action", action_url)
    gather.set("method", "POST")
    gather.set("speechTimeout", speech_timeout)
    gather.set("speechModel", speech_model)
    gather.set("language", language)

    if prompt:
        prompt_elem = ElementTree.SubElement(gather, "Say")
        prompt_elem.set("voice", "alice")
        prompt_elem.set("language", language)
        prompt_elem.text = prompt

    return gather


def generate_full_response(
    session_id: str,
    welcome_message: str | None = None,
    gather_speech: bool = True,
    action_url: str | None = None,
) -> str:
    """Generate a full TwiML response for a voice call.

    Args:
        session_id: Session ID for this conversation.
        welcome_message: Optional welcome message to say.
        gather_speech: Whether to gather speech input.
        action_url: URL to post gathered input to.

    Returns:
        TwiML XML string.
    """
    response = ElementTree.Element("Response")

    # Add welcome message
    if welcome_message:
        say = generate_say_twiml(welcome_message)
        response.append(say)

    # Add speech input gathering
    if gather_speech and action_url:
        gather = generate_gather_twiml(
            action_url,
            prompt="How can I help you today?",
        )
        response.append(gather)

    # Add a pause and redirect if no input
    pause = ElementTree.SubElement(response, "Pause")
    pause.set("length", "5")

    redirect = ElementTree.SubElement(response, "Redirect")
    redirect.text = f"{action_url}?session={session_id}"

    return twiml_to_string(response)


def generate_hangup_response() -> str:
    """Generate a TwiML response to hang up the call.

    Returns:
        TwiML XML string.
    """
    response = ElementTree.Element("Response")
    hangup = ElementTree.SubElement(response, "Hangup")
    hangup.set("reason", "call-completed")
    return twiml_to_string(response)


def generate_play_audio_response(
    audio_url: str,
    loop: bool = False,
) -> str:
    """Generate a TwiML response to play audio.

    Args:
        audio_url: URL of the audio to play.
        loop: Whether to loop the audio.

    Returns:
        TwiML XML string.
    """
    response = ElementTree.Element("Response")
    play = ElementTree.SubElement(response, "Play")
    play.set("loop", "1" if not loop else "0")
    play.text = audio_url
    return twiml_to_string(response)


def generate_dial_response(
    to_number: str,
    caller_id: str | None = None,
    action_url: str | None = None,
    timeout: int = 30,
) -> str:
    """Generate a TwiML response to dial another number.

    Args:
        to_number: Number to dial.
        caller_id: Caller ID to display.
        action_url: URL for dial status callback.
        timeout: Timeout in seconds.

    Returns:
        TwiML XML string.
    """
    response = ElementTree.Element("Response")
    dial = ElementTree.SubElement(response, "Dial")
    dial.set("timeout", str(timeout))
    if caller_id:
        dial.set("callerId", caller_id)
    if action_url:
        dial.set("action", action_url)
    dial.text = to_number
    return twiml_to_string(response)
