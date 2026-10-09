"""Finite semantic families whose distinctions must reach a completed Scene."""
from __future__ import annotations

from dataclasses import dataclass


def _shown(value: object) -> str:
    text = repr(value)
    return text if len(text) <= 96 else text[:93] + "..."


def _diagnostic_error(code: str, detail: str) -> ValueError:
    return ValueError(f"{code}: {detail}")


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
        "annotation-box", ("callout", "highlight", "note", "explanatory-arrow"),
    ),
    RealizationFamily(
        "table-missing-observation", "table-column:comparisonFacet=missingActual",
        "table-cell", ("observed", "missing"),
    ),
)


def realization_families() -> tuple[RealizationFamily, ...]:
    """Return the closed realization evidence registry in canonical order."""
    return _FAMILIES


def validate_realization_families(families: tuple[RealizationFamily, ...]) -> None:
    """Reject an ambiguous or unreviewed realization-evidence declaration."""
    seen: set[str] = set()
    for index, family in enumerate(families):
        if (not family.family_id or family.family_id in seen or not family.selector
                or not family.primitive_purpose or not family.admitted_states
                or len(set(family.admitted_states)) != len(family.admitted_states)):
            raise _diagnostic_error("E_PRESENTATION_REALIZATION_INVALID", f"familyIndex={index}, familyId={_shown(family.family_id)}, selector={_shown(family.selector)}, purpose={_shown(family.primitive_purpose)}; expected unique id and nonempty selector/purpose/states")
        states = set(family.admitted_states)
        if any(state not in states or not reason for state, reason in family.intentional_equivalences):
            bad = next((state, reason) for state, reason in family.intentional_equivalences
                       if state not in states or not reason)
            raise _diagnostic_error("E_PRESENTATION_REALIZATION_INVALID", f"familyId={_shown(family.family_id)}, equivalenceState={_shown(bad[0])}, reasonPresent={bool(bad[1])}; expected admitted state and nonempty reason")
        seen.add(family.family_id)


def realization_family(identifier: str) -> RealizationFamily:
    """Resolve one finite family or reject an unreviewed evidence policy."""
    for family in _FAMILIES:
        if family.family_id == identifier:
            return family
    raise _diagnostic_error("E_PRESENTATION_REALIZATION_UNKNOWN", f"identifier={_shown(identifier)}; expected one of {tuple(family.family_id for family in _FAMILIES)!r}")
