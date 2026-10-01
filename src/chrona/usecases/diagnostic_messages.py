"""What a diagnostic row says: the message every row an agent can see must carry (#782).

A producer that knows the offending value says so in its own message. A producer that
raises a bare code (a ``ValueError("E_X")``, an importer that reports ``E_X source=/``)
leaves a message that is only the code, which tells a reader nothing. ``error_message``
is the one guarantee placed on the single record builder: an informative message passes
through unchanged; a bare one is replaced by a curated sentence for the code, or else by
a derived one that says plainly that no further detail is recorded for it.

Nothing here prints, reads arguments or imports a presentation, core or adapter module:
it reads strings.
"""
from __future__ import annotations

import re
from typing import Mapping

# Codes whose producers cannot know the value, so the sentence names the cause and the
# next action instead. Add one entry per code an agent reaches by an ordinary mistake;
# a code with no entry is still safe (the derived sentence), only less helpful.
CURATED_MESSAGES: Mapping[str, str] = {
    "E_ACTUAL_REQUIRED": (
        "the View compares against actuals (comparison.actual is required) but no actual file was given; "
        "pass --actual FILE, or change the View so actuals are not required"
    ),
    "E_SCHEME_INTENT_UNKNOWN": (
        "a Color Scheme colorBindings entry is not ROLE.PROPERTY bound to a known intent or a declared color; "
        "check every target name and value in colorBindings"
    ),
    "E_SCHEME_THEME_BINDING": (
        "a Color Scheme colorBindings target names an unsupported property; "
        "use fill, stroke, gradientStart, gradientEnd or shadowColor"
    ),
    "E_THEME_ROLE_PROPERTY_UNSUPPORTED": (
        "a Theme role binds a property that no drawing rule reads; remove it or bind a supported property"
    ),
    "E_LAYOUT_TOKEN_REQUIREMENT_UNAVAILABLE": (
        "a Layout profile refers to a Theme token that the Theme does not declare; "
        "add the token to the Theme or use a Theme that declares it"
    ),
    "E_LAYOUT_TOKEN_REQUIREMENT_TYPE": (
        "a Layout profile uses a Theme token whose type does not fit that place; "
        "the token must be a number here"
    ),
}

_SOURCE_SUFFIX = re.compile(r"\bsource=\S*")
_PUNCTUATION = " \t\r\n:;,.-"


def is_bare(code: str, message: str | None) -> bool:
    """Whether ``message`` says nothing beyond ``code``: empty, the code itself, or the code and ``source=<ref>``."""
    text = (message or "").strip()
    if not text:
        return True
    remainder = _SOURCE_SUFFIX.sub("", text.replace(code, ""))
    return not remainder.strip(_PUNCTUATION)


def derived_message(code: str) -> str:
    """A sentence built from the code alone; honest that it is only the code's name."""
    words = code.split("_", 1)[-1].replace("_", " ").lower() or code
    return f"{words}: no further detail is recorded for this code ({code})"


def error_message(code: str, message: str | None) -> str:
    """The message a row carries: the producer's if informative, else the curated or derived sentence."""
    if not is_bare(code, message):
        return str(message)
    return CURATED_MESSAGES.get(code) or derived_message(code)
