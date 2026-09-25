"""Dependency-free typed values for normalized table presentation intent."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BooleanPresencePresentation:
    """Author-declared text for the two states of a boolean table fact."""

    when_true: str
    when_false: str
