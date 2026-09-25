"""Finite semantic families whose distinctions must reach a completed Scene."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RealizationFamily:
    """One reviewable set of source states and its Scene primitive family.

    ``selector`` names a deliberately small corpus/View traversal understood by
    the evidence generator.  It is not an author-facing expression language.
    """

    family_id: str
    selector: str
    primitive_purpose: str
    admitted_states: tuple[str, ...]
    intentional_equivalences: tuple[tuple[str, str], ...] = ()


_FAMILIES = (
    RealizationFamily(
        "table-finish-variance", "table-column:comparisonFacet=finishDelta",
        "table-cell", ("ahead", "on-plan", "behind", "unavailable"),
        (("unavailable", "A finish variance without an observation is intentionally neutral."),),
    ),
    RealizationFamily(
        "annotation-purpose", "annotation:purpose",
        "annotation", ("callout", "highlight", "note", "explanatory-arrow"),
    ),
)


def realization_families() -> tuple[RealizationFamily, ...]:
    """Return the closed realization evidence registry in canonical order."""
    return _FAMILIES


def validate_realization_families(families: tuple[RealizationFamily, ...]) -> None:
    """Reject an ambiguous or unreviewed realization-evidence declaration."""
    seen: set[str] = set()
    for family in families:
        if (not family.family_id or family.family_id in seen or not family.selector
                or not family.primitive_purpose or not family.admitted_states
                or len(set(family.admitted_states)) != len(family.admitted_states)):
            raise ValueError("E_PRESENTATION_REALIZATION_INVALID")
        states = set(family.admitted_states)
        if any(state not in states or not reason for state, reason in family.intentional_equivalences):
            raise ValueError("E_PRESENTATION_REALIZATION_INVALID")
        seen.add(family.family_id)


def realization_family(identifier: str) -> RealizationFamily:
    """Resolve one finite family or reject an unreviewed evidence policy."""
    for family in _FAMILIES:
        if family.family_id == identifier:
            return family
    raise ValueError(f"E_PRESENTATION_REALIZATION_UNKNOWN:{identifier}")
