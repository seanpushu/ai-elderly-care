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
# 1. Verdict vocabulary is banned outright, hedged or not. PausePal describes
#    pressure patterns; it never labels a message a scam, legitimate, fake, etc.
_VERDICT_WORDS = re.compile(
    r"\b(?:scams?|scammers?|scammy|frauds?|fraudulent|fraudsters?|phishing|smishing|vishing|"
    r"hoax(?:es)?|swindles?|con\s+artists?|legit|legitimate|illegitimate|genuine|authentic|"
    r"inauthentic|fakes?|faked|impost[eo]rs?|impersonators?|cloned|deepfakes?|ai[- ]generated|"
    r"lying|liars?|truthful|dishonest|trustworthy|untrustworthy)\b",
    re.IGNORECASE,
)

# 2. Probabilities, scores, and certainty language are banned outright.
_ABSOLUTE_CLAIMS = (
    re.compile(r"\b\d{1,3}(?:\.\d+)?\s?%"),
    re.compile(r"\b(?:percent|percentage|probability|probabilities|likelihood|odds|chance|chances|score|scores)\b", re.IGNORECASE),
    re.compile(r"\b(?:likely|unlikely|probably|probable|improbable|almost certainly|definitely|for sure|100 ?percent|without (?:a )?doubt)\b", re.IGNORECASE),
    re.compile(r"\b(?:is|are|will be|it's|that's)\s+guaranteed\b|\b(?:i|we)\s+guarantee\b", re.IGNORECASE),
    re.compile(r"\bguaranteed\s+(?:to be\s+)?(?:safe|secure)\b", re.IGNORECASE),
)

# 3. Authenticity, truth, and safety verdicts built from ordinary words are
#    rejected unless the same sentence hedges them first, e.g. "that does not
#    mean it is safe" or "PausePal cannot tell whether the caller is really
#    your grandson".
_VERDICT_CLAIMS = (
    re.compile(
        r"\b(?:this|it|that|the message|the sender|the caller|the request|the offer|the story)\s+"
        r"(?:is|was|are|were|isn't|wasn't)\s+(?:not\s+)?(?:real|safe|true|false|honest)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:voice|caller|speaker|identity|person|sender|grandson|granddaughter|grandchild|relative)\b"
        r"[^.!?]{0,40}?\b(?:real|honest)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:is|are|was|were|isn't|aren't|wasn't|weren't)\s+(?:not\s+)?(?:really|actually|truly)\s+"
        r"(?:your|a|an|the|from|who|in)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:money|funds|savings|account|information|you)\s+(?:is|are|will be|remains?|stays?)\s+safe\b", re.IGNORECASE),
    re.compile(r"\b(?:telling|tells|told)\s+the\s+truth\b|\b(?:looks?|seems?|sounds?|appears?)\s+(?:like\s+)?(?:a\s+)?(?:real|safe|suspicious)\b", re.IGNORECASE),
)

_HEDGE = re.compile(
    r"\b(?:mean|whether|if|know|tell|prove|confirm|sure|certain|assume|decide|verify|check|judge|say)\b",
    re.IGNORECASE,
)


def _is_hedged(value: str, match_start: int) -> bool:
    """True when the clause leading up to ``match_start`` contains a hedge word."""
    sentence_start = max(value.rfind(".", 0, match_start), value.rfind("!", 0, match_start), value.rfind("?", 0, match_start))
    return bool(_HEDGE.search(value, sentence_start + 1, match_start))


# ---------------------------------------------------------------------------
# Next steps: independent verification only.
#
# A step is rejected when it contains literal contact details, tells the user
# to reply/click/scan/log in/send codes, or refers to a channel attributed to
# the message or sender ("the number in the message", "the link they sent").
# This applies even when phrased as a warning ("do not click the link") so
# that no wording that names the attacker's channel can reach the user as a
# recommendation. A channel noun ("number", "link", ...) is allowed only when
# the step also names an independent source ("already saved", "on the back of
# your card", "official", "in person", ...).
_CONTACT_DETAIL = re.compile(
    r"(?:https?://|www\.|[\w.+-]+@[\w-]+\.\w+|(?:\+?\d[\d\s().-]{6,}\d))",
    re.IGNORECASE,
)
_CHANNEL_NOUN = re.compile(
    r"\b(?:numbers?|phone|telephone|links?|urls?|websites?|web ?sites?|sites?|web ?pages?|addresses?|"
    r"e-?mails?|contacts?|contact details|lines?|hotlines?|extensions?|attachments?|qr|buttons?|apps?|"
    r"portals?|accounts?|chats?|whatsapp|telegram|messenger)\b",
    re.IGNORECASE,
)
_MESSAGE_CHANNEL_ACTIONS = re.compile(
    r"\b(?:write back|text back|message back|"
    r"click|clicking|tap|tapping|scan|scanning|download|downloading|install|installing|"
    r"log ?in|sign ?in|log on|enter (?:the|your|a) (?:code|password|pin|details)|"
    r"(?:share|give|read|read out|provide|send|confirm|repeat) (?:the|your|a|this|that|any) (?:code|codes|password|pin|otp|one-time|verification|security))\b",
    re.IGNORECASE,
)
# "reply"/"respond" is only acceptable as something to hold off on
# ("before you respond", "do not reply"), never as an instruction.
_REPLY_WORD = re.compile(r"\b(?:reply|replies|replying|respond|responds|responding|answer|answering)\b", re.IGNORECASE)
_DEFERRED_REPLY = re.compile(
    r"\b(?:before|without|do not|don't|never|avoid|instead of|rather than|not)\s+(?:\w+\s+)?"
    r"(?:reply|replies|replying|respond|responds|responding|answer|answering)\b",
    re.IGNORECASE,
)
_MESSAGE_ATTRIBUTION = re.compile(
    r"\b(?:this|that|their|his|her|its|new|provided|given|listed|included|supplied|attached|above|"
    r"sender'?s?|caller'?s?|unknown|unfamiliar|different)\s+(?:phone\s+|mobile\s+|cell\s+|contact\s+)?"
    r"(?:numbers?|links?|urls?|websites?|sites?|addresses?|e-?mails?|contacts?|lines?|extensions?|attachments?|buttons?|apps?)\b"
    r"|\b(?:in|from|within|of|on|via|through)\s+(?:the|this|that|their|his|her)\s+(?:message|text|e-?mail|call|voicemail|chat|post|sms)\b"
    r"|\b(?:they|he|she|the sender|the caller)\s+(?:gave|sent|provided|listed|shared|left|texted|mentioned|included|offered|supplied)\b"
    r"|\b(?:number|link|website|address|e-?mail|contact)\s+(?:they|he|she)\s+(?:gave|sent|provided|left|shared|mentioned)\b"
    r"|\b(?:sent|provided|given|included|listed|mentioned|shown|quoted)\s+(?:to you\s+)?(?:in|with|by)\s+(?:the|this|that)\b"
    r"|\bcall(?:ing)?\s+(?:them|him|her)\s+back\b(?!\s+(?:on|using|at)\s+(?:a|the)\s+(?:number|phone)\s+you)",
    re.IGNORECASE,
)
_INDEPENDENT_SOURCE = re.compile(
    r"\b(?:already (?:had|have|has|saved|know|knew|use|used)|saved|known|trusted|official|independent(?:ly)?|"
    r"yourself|your own|on the back of|on your (?:card|statement|bill|passbook)|in person|branch|"
    r"directory|phone ?book|address book|before this message|look(?:ed)? up|previous(?:ly)?|"
    r"usual|normal|regular|used before|have used|family member|friend)\b",
    re.IGNORECASE,
)


def _check_next_step(step: str) -> None:
    if _CONTACT_DETAIL.search(step):
        raise InvalidAnalysis("Next steps must not include phone numbers, links, or addresses.")
    if _MESSAGE_CHANNEL_ACTIONS.search(step):
        raise InvalidAnalysis("Next steps must not tell the user to click, scan, log in, or share codes.")
    reply_mentions = len(_REPLY_WORD.findall(step))
    if reply_mentions and reply_mentions != len(_DEFERRED_REPLY.findall(step)):
        raise InvalidAnalysis("Next steps must not tell the user to reply to the message.")
    if _MESSAGE_ATTRIBUTION.search(step):
        raise InvalidAnalysis("Next steps must not refer to contact channels supplied by the message.")
    if _CHANNEL_NOUN.search(step) and not _INDEPENDENT_SOURCE.search(step):
        raise InvalidAnalysis("Next steps may only mention contact channels the user already trusts.")


# ---------------------------------------------------------------------------
# English check. Latin-script ratio plus a minimum number of distinctly English
# function/content words. Every generated field must be at least three words.
_ENGLISH_MARKERS = frozenset(
    """the and or to is are was were be been not does did you your yours they them their who what
    which when where why how if before after with without for about into someone anyone anything
    something can cannot could should would may might will there here have has had ask call check
    pause verify trust trusted message request money send sent tell talk know sure safe person
    family friend bank number already again yet please this that these those wait stop take time
    think else first from someone anybody nobody yourself""".split()
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
        return False
    markers = {word for word in words if word in _ENGLISH_MARKERS}
    needed = 2 if len(words) >= 8 else 1
    return len(markers) >= needed


def _check_generated_text(value: str, field_name: str) -> None:
    if not _looks_english(value):
        raise InvalidAnalysis(f"{field_name} must be written in English.")
    if _VERDICT_WORDS.search(value):
        raise InvalidAnalysis(f"{field_name} contains a verdict PausePal does not make.")
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
        _check_next_step(step)

    return result
