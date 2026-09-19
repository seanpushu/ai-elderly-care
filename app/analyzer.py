"""Deterministic demo analysis for PausePal.

This module deliberately does not call an AI service. Its small phrase list is
only a demonstration and cannot determine whether a message is safe.
"""

from __future__ import annotations

import re
from typing import Any


_DEMO_PATTERNS = (
    (
        "send me",
        "A request to send something may deserve independent verification.",
    ),
    (
        "do not tell",
        "A request for secrecy can be a reason to pause and verify the sender.",
    ),
    (
        "transfer all funds",
        "A request to transfer all funds should be independently verified.",
    ),
)


def _has_enough_context(text: str) -> bool:
    words = re.findall(r"\b[\w’'-]+\b", text, flags=re.UNICODE)
    return len(text) >= 12 and len(words) >= 3


async def analyze_message(text: str) -> dict[str, Any]:
    """Return a deterministic, non-diagnostic demo assessment."""
    if not _has_enough_context(text):
        return {
            "assessment": "insufficient_information",
            "summary": (
                "This demo does not have enough information to assess the message. "
                "That does not mean the message is safe."
            ),
            "signals": [],
            "next_steps": [
                "Consider who sent the message and what they are asking you to do.",
                "Ask someone you trust if you are unsure how to respond.",
            ],
            "mode": "demo",
        }

    signals: list[dict[str, str]] = []
    for phrase, reason in _DEMO_PATTERNS:
        match = re.search(re.escape(phrase), text, flags=re.IGNORECASE)
        if match:
            signals.append({"quote": match.group(0), "reason": reason})

    if signals:
        return {
            "assessment": "warning",
            "summary": (
                "This demo found wording that may merit a closer look. It is a "
                "limited text check and cannot determine whether the message is safe."
            ),
            "signals": signals,
            "next_steps": [
                "Pause before sending money, codes, or personal information.",
                "Verify the request using a known phone number or another trusted contact method.",
                "Talk it over with someone you trust if you are uncertain.",
            ],
            "mode": "demo",
        }

    return {
        "assessment": "no_clear_signals",
        "summary": (
            "This demo found none of its limited example phrases. That does not "
            "mean the message is safe."
        ),
        "signals": [],
        "next_steps": [
            "Check whether the sender and request are familiar and expected.",
            "Verify any unusual request through a trusted contact method.",
        ],
        "mode": "demo",
    }
