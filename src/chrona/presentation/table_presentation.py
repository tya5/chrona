"""Dependency-free typed values for normalized table presentation intent."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BooleanPresencePresentation:
    """Author-declared text for the two states of a boolean table fact."""

    when_true: str
    when_false: str


SIGNED_FORMATS = frozenset(("signedDays", "signedNumber"))
AFFIX_STATES = ("slip", "onTime", "ahead", "missing")


@dataclass(frozen=True)
class CellAffix:
    """Literal text wrapped around a table cell's text in one state (#588)."""

    prefix: str = ""
    suffix: str = ""


@dataclass(frozen=True)
class ColumnAffixes:
    """A column's per-state affixes; a state without an entry is unchanged."""

    slip: CellAffix | None = None
    on_time: CellAffix | None = None
    ahead: CellAffix | None = None
    missing: CellAffix | None = None

    def for_state(self, state: str | None) -> CellAffix | None:
        return {"slip": self.slip, "onTime": self.on_time, "ahead": self.ahead,
                "missing": self.missing}.get(state) if state else None


def affix_state(value: object, formatter: object) -> str | None:
    """The state of one cell value: `missing` for an absent value, else the sign of a signed integer."""
    if value is None:
        return "missing"
    if formatter in SIGNED_FORMATS and isinstance(value, int) and not isinstance(value, bool):
        return "slip" if value > 0 else "ahead" if value < 0 else "onTime"
    return None
