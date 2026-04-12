"""Spoken-clarity transforms for TTS output.

Booking codes, IST date-times, and long messages are reformatted so they
sound natural when read aloud by Google Cloud TTS.  No domain or
orchestration logic lives here — pure string transforms.
"""

from __future__ import annotations

import re
from datetime import datetime

_BOOKING_CODE_RE = re.compile(r"\b([A-Z]{2})-([A-Z0-9]{3,5})\b")


def spell_booking_code(code: str) -> str:
    """Convert a booking code like ``NL-A742`` to a TTS-friendly spelling.

    Each letter/digit gets a trailing period; hyphens become the word "dash".
    The trailing period on the very last character is stripped for natural speech.

    >>> spell_booking_code("NL-A742")
    'N. L. dash A. 7. 4. 2'
    """
    tokens: list[str] = []
    for ch in code:
        if ch == "-":
            tokens.append("dash")
        elif ch.isalpha():
            tokens.append(f"{ch.upper()}.")
        elif ch.isdigit():
            tokens.append(f"{ch}.")
    return " ".join(tokens).rstrip(".")


def format_ist_datetime_spoken(label_ist: str) -> str:
    """Make an IST slot label more TTS-friendly.

    Handles labels like ``"Mon 14 Apr 2025 10:00 – 10:30 IST"`` or free-form
    date strings.  Falls back to the original label unchanged.
    """
    label = label_ist.strip()
    label = label.replace(" – ", " to ").replace("–", " to ")
    label = label.replace(" - ", " to ", 1) if "IST" in label else label
    label = label.replace("IST", "I.S.T.")
    return label


def _replace_booking_codes(text: str) -> str:
    """Spell out every booking code found in *text*."""

    def _repl(m: re.Match) -> str:
        return spell_booking_code(m.group(0))

    return _BOOKING_CODE_RE.sub(_repl, text)


def format_for_speech(text: str) -> str:
    """Apply all TTS-friendly transforms to an assistant message.

    - Spells out booking codes character-by-character.
    - Rewrites IST labels for clarity.
    - Strips markdown-style bullets for cleaner speech.
    """
    text = _replace_booking_codes(text)
    if "IST" in text:
        text = text.replace("IST", "I.S.T.")
    text = re.sub(r"^- ", "", text, flags=re.MULTILINE)
    text = text.replace("\n", " ... ")
    return text.strip()


def chunk_text(text: str, max_chars: int = 500) -> list[str]:
    """Split *text* into chunks of at most *max_chars* on sentence boundaries.

    Returns the full text as a single chunk when it fits.
    """
    if len(text) <= max_chars:
        return [text]

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current: list[str] = []
    length = 0

    for sentence in sentences:
        addition = len(sentence) + (1 if current else 0)
        if length + addition > max_chars and current:
            chunks.append(" ".join(current))
            current = [sentence]
            length = len(sentence)
        else:
            current.append(sentence)
            length += addition

    if current:
        chunks.append(" ".join(current))
    return chunks
