"""Completion facts shared by scheduling and View selection."""
from __future__ import annotations

from collections.abc import Mapping, Iterable


def actual_occurrence_completed(kind: str, actual: Mapping[str, object] | None) -> bool:
    """Whether the selected Actual supplies the terminal fact for one occurrence.

    Progress, a planned target, and a forecast estimate are deliberately not
    completion facts.  The caller supplies the normalized occurrence kind.
    """
    if not isinstance(actual, Mapping):
        return False
    if kind == "span":
        return "finish" in actual
    if kind == "point":
        return "at" in actual
    raise ValueError(f"unknown temporal occurrence kind: {kind!r}")


def rollup_completed(children: Iterable[bool]) -> bool:
    """A rollup is complete only when each temporal child is complete."""
    return all(children)
