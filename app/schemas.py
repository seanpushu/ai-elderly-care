"""Shared request/response contract for PausePal analysis.

Every analysis result, whatever model produced it, must pass through
``validate_analysis`` before it is returned to a client. The validation is
deliberately strict: it enforces the assessment vocabulary, keeps every quote an
exact substring of the submitted text, requires English output, and rejects the
kinds of claims PausePal must never make (probabilities, authenticity verdicts,
safety guarantees, or endorsements of contact details supplied by the message).
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


MAX_TEXT_LENGTH = 4000
MAX_SUMMARY_LENGTH = 700
MAX_SIGNALS = 8
MAX_QUOTE_LENGTH = 300
MAX_REASON_LENGTH = 400
MAX_NEXT_STEPS = 6
MAX_STEP_LENGTH = 300

Assessment = Literal["warning", "no_clear_signals", "insufficient_information"]
ASSESSMENT_VALUES: tuple[str, ...] = ("warning", "no_clear_signals", "insufficient_information")


class AnalyzeRequest(BaseModel):
    """Inbound request: a single bounded text field."""

    text: str

    @field_validator("text", mode="before")
    @classmethod
    def trim_and_validate_text(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("Text must be a string.")
        value = value.strip()
        if not value:
            raise ValueError("Text must not be empty after trimming.")
        if len(value) > MAX_TEXT_LENGTH:
            raise ValueError(f"Text must be {MAX_TEXT_LENGTH} characters or fewer after trimming.")
        return value


class Signal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quote: str = Field(min_length=1, max_length=MAX_QUOTE_LENGTH)
    reason: str = Field(min_length=1, max_length=MAX_REASON_LENGTH)


class AnalysisResponse(BaseModel):
    """The single response shape shared by the API and the frontend."""

    model_config = ConfigDict(extra="forbid")

    assessment: Assessment
    summary: str = Field(min_length=1, max_length=MAX_SUMMARY_LENGTH)
    signals: list[Signal] = Field(max_length=MAX_SIGNALS)
    next_steps: list[str] = Field(min_length=1, max_length=MAX_NEXT_STEPS)
    mode: Literal["live"]

    @field_validator("next_steps")
    @classmethod
    def steps_are_bounded(cls, steps: list[str]) -> list[str]:
        for step in steps:
            if not step.strip():
                raise ValueError("Next steps must not be blank.")
            if len(step) > MAX_STEP_LENGTH:
                raise ValueError("Next steps must be short.")
        return steps


class InvalidAnalysis(ValueError):
    """Raised when model output does not satisfy the PausePal contract."""


_LATIN_LETTER = re.compile(r"[A-Za-z]")
_ANY_LETTER = re.compile(r"[^\W\d_]", re.UNICODE)

# Claims the service must never make. Matched case-insensitively against the
# generated summary, reasons, and next steps (never against the user's quotes).
#
# Absolute claims are rejected wherever they appear.
_ABSOLUTE_CLAIMS = (
    re.compile(r"\b\d{1,3}(?:\.\d+)?\s?%"),
    re.compile(r"\b(?:percent|probability|likelihood|odds|chance)\b", re.IGNORECASE),
    re.compile(r"\b(?:definitely|for sure|100 ?percent|without (?:a )?doubt)\b", re.IGNORECASE),
    re.compile(r"\b(?:is|are|will be|it's|that's)\s+guaranteed\b|\b(?:i|we)\s+guarantee\b", re.IGNORECASE),
    re.compile(r"\bguaranteed\s+(?:to be\s+)?(?:safe|secure|legitimate|genuine)\b", re.IGNORECASE),
)

# Verdict claims (authenticity, truth, safety) are rejected unless the same
# sentence hedges them first, e.g. "that does not mean it is safe" or
# "PausePal cannot tell whether the caller is really your grandson".
_VERDICT_CLAIMS = (
    re.compile(r"\b(?:is|are|was|were)\s+(?:a|an)\s+(?:scam|fraud|hoax)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:this|it|that|the message|the sender|the caller|the request|the offer)\s+"
        r"(?:is|was|are|were)\s+(?:not\s+)?(?:legitimate|genuine|real|authentic|fake|safe|true|false)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:voice|caller|speaker|identity|person|sender)\b[^.!?]{0,40}?"
        r"\b(?:real|genuine|authentic|fake|cloned|impostor|imposter|ai[- ]generated)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:is|are|was|were|isn't|aren't|wasn't|weren't)\s+(?:not\s+)?(?:really|actually|truly)\s+"
        r"(?:your|a|an|the|from|who)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:money|funds|savings|account|information)\s+(?:is|are|will be|remains?|stays?)\s+safe\b", re.IGNORECASE),
    re.compile(r"\b(?:telling|tells|told)\s+the\s+truth\b|\b(?:is|are|was|were)\s+(?:lying|truthful|honest)\b", re.IGNORECASE),
)

_HEDGE = re.compile(
    r"\b(?:mean|whether|if|know|tell|prove|confirm|sure|certain|assume|decide|verify|check|judge|say)\b",
    re.IGNORECASE,
)


def _is_hedged(value: str, match_start: int) -> bool:
    """True when the clause leading up to ``match_start`` contains a hedge word."""
    sentence_start = max(value.rfind(".", 0, match_start), value.rfind("!", 0, match_start), value.rfind("?", 0, match_start))
    return bool(_HEDGE.search(value, sentence_start + 1, match_start))

# Recommendations may only point at independent, pre-known channels. Any phone
# number, URL, or e-mail address inside a next step is treated as an endorsement
# of message-supplied contact details and rejected.
_CONTACT_DETAIL = re.compile(
    r"(?:https?://|www\.|[\w.+-]+@[\w-]+\.\w+|(?:\+?\d[\d\s().-]{6,}\d))",
    re.IGNORECASE,
)


_ENGLISH_MARKERS = frozenset(
    """the a an and or to is are was were be been it its this that these those not no do does
    did you your yours they them their who what which when where why how if before after with
    without for of in on at from by about into someone anyone anything something can cannot
    could should would may might will there here have has had ask call check pause verify
    trust trusted message request money send sent tell talk know sure safe person family
    friend bank number already again yet please""".split()
)
_WORD = re.compile(r"[A-Za-z']+")


def _looks_english(value: str) -> bool:
    letters = _ANY_LETTER.findall(value)
    if not letters:
        return False
    latin = len(_LATIN_LETTER.findall(value))
    if latin / len(letters) < 0.9:
        return False
    words = [word.lower().strip("'") for word in _WORD.findall(value)]
    if len(words) < 3:
        return True
    markers = {word for word in words if word in _ENGLISH_MARKERS}
    needed = 2 if len(words) >= 8 else 1
    return len(markers) >= needed


def _check_generated_text(value: str, field_name: str) -> None:
    if not _looks_english(value):
        raise InvalidAnalysis(f"{field_name} must be written in English.")
    for pattern in _ABSOLUTE_CLAIMS:
        if pattern.search(value):
            raise InvalidAnalysis(f"{field_name} contains a claim PausePal does not make.")
    for pattern in _VERDICT_CLAIMS:
        for match in pattern.finditer(value):
            if not _is_hedged(value, match.start()):
                raise InvalidAnalysis(f"{field_name} contains a claim PausePal does not make.")


def validate_analysis(raw: Any, source_text: str) -> AnalysisResponse:
    """Validate raw model output against the submitted text and the contract.

    ``raw`` is the parsed JSON object from the model. ``mode`` is always set by
    the server, never trusted from the model. Raises ``InvalidAnalysis`` with a
    short English message that never includes the submitted text.
    """
    if not isinstance(raw, dict):
        raise InvalidAnalysis("Model output must be a JSON object.")

    candidate = {
        "assessment": raw.get("assessment"),
        "summary": raw.get("summary"),
        "signals": raw.get("signals", []),
        "next_steps": raw.get("next_steps"),
        "mode": "live",
    }

    try:
        result = AnalysisResponse.model_validate(candidate)
    except ValidationError as exc:
        first = exc.errors()[0] if exc.errors() else {}
        location = ".".join(str(part) for part in first.get("loc", ())) or "output"
        raise InvalidAnalysis(f"Model output field '{location}' is invalid.") from None

    _check_generated_text(result.summary, "summary")

    for signal in result.signals:
        if signal.quote not in source_text:
            raise InvalidAnalysis("A signal quote is not an exact excerpt of the submitted text.")
        _check_generated_text(signal.reason, "signal reason")

    if result.assessment == "insufficient_information" and result.signals:
        raise InvalidAnalysis("Insufficient information must not include signals.")
    if result.assessment == "warning" and not result.signals:
        raise InvalidAnalysis("A warning must cite at least one exact quote from the message.")

    for step in result.next_steps:
        _check_generated_text(step, "next step")
        if _CONTACT_DETAIL.search(step):
            raise InvalidAnalysis("Next steps must not include phone numbers, links, or addresses.")

    return result
