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


@dataclass(frozen=True)
class PurposeClassification:
    """The reviewed disposition of one registered Scene purpose (#419 C1).

    The report derives a row per purpose from the vocabulary and the committed
    Scenes; this is only the classification of that row, never the list of rows.

    ``distinct``    drawn with more than one realized appearance role.
    ``single-role`` drawn with exactly one role, intentionally; ``reason`` says why.
    ``gap``         drawn, but its model states or registered roles are not all
                    distinguished or drawn yet; ``reason`` names what is missing.
    ``unpainted``   registered but not drawn by any committed Scene; ``reason`` says why.
    """

    purpose: str
    disposition: str
    reason: str = ""


DISPOSITIONS = ("distinct", "single-role", "gap", "unpainted")


def _p(purpose: str, disposition: str, reason: str = "") -> PurposeClassification:
    return PurposeClassification(purpose, disposition, reason)


_S, _D, _G, _U = "single-role", "distinct", "gap", "unpainted"

_PURPOSES = (
    # Marks and time decorations.
    _p("planned", _D), _p("actual", _S, "one actual-progress bar; the planned/actual contrast is carried by the two purposes"),
    _p("forecast", _U, "purpose=forecast is preserved by the vocabulary and the Scene; only its fallback role is planned, and the committed corpus draws no forecast purpose"),
    _p("snapshot", _S, "one baseline-snapshot mark"), _p("missingActual", _S, "one missing-observation marker"),
    _p("summary-bar", _S, "one summary-bar fill"), _p("progress-fill", _S, "one progress fill"),
    _p("icon-mark", _U, "no committed slide draws a standalone icon mark"),
    _p("label-visual", _S, "one label glyph role"),
    _p("as-of", _S, "one as-of marker"), _p("as-of-label", _D), _p("as-of-cone", _S, "one translucent light cone"),
    _p("deadline-mark", _U, "no committed slide draws a Project deadline (#822)"),
    _p("deadline-outline", _U, "ground of the deadline mark; absent whenever the mark is"),
    _p("deadline-caption", _U, "no committed slide draws a Project deadline (#822)"),
    _p("label-chip", _G, "finish-delta-chip and member-label-chip are registered but no committed Scene draws them"),
    _p("calendar-closed", _S, "closed days are one distinction"),
    _p("calendar-exception", _S, "one calendar-exception day paint"),
    _p("period-band", _S, "a named period has one band paint; the variant suffix is authored, not a state"),
    _p("period-label", _S, "one period label ink"),
    _p("canvas-texture", _S, "one ground texture"),
    _p("canvas-overlay", _U, "no committed slide draws a fixed canvas overlay"),
    _p("canvas-overlay-gradient", _U, "no committed slide draws a fixed gradient overlay"),
    _p("region-frame", _D), _p("frame-glyph", _S, "one catalogue border family"),
    # Axis.
    _p("axis-band", _D), _p("axis-label", _D), _p("axis-grid", _D),
    _p("axis-rule", _S, "one axis/plot boundary rule"), _p("axis-cell-separator", _S, "one cell separator"),
    # Grouping and rows.
    _p("group-decoration", _S, "one group band paint"), _p("row-decoration", _S, "one row band paint"),
    _p("row-rule", _S, "one row rule"),
    _p("table-column-rule", _U, "no committed slide draws the rule under column headers (#1545)"),
    _p("group-header-band", _S, "one header band paint"), _p("group-header-strip", _S, "one header strip paint"),
    _p("group-tab", _S, "one patterned header tab"), _p("group-header", _D),
    _p("group-detail", _S, "one group detail ink"),
    # Table.
    _p("observation-source", _S, "one source caption ink"), _p("observation-column-label", _S, "one column label ink"),
    _p("observation-cell", _G, "variance-behind is registered but no committed Scene draws an observation cell behind plan"),
    _p("title-text", _D), _p("kicker-text", _S, "one kicker ink"), _p("subtitle-text", _D),
    _p("slot-heading", _S, "one slot caption ink"), _p("table-column-label", _D), _p("table-cell", _D),
    # Plot labels.
    _p("member-label", _G, "inside planned/actual/scenario/snapshot labels are registered but every committed label uses the shared text role"),
    _p("finish-delta", _D),
    _p("forecast-finish-delta", _U, "no committed slide draws a forecast finish delta"),
    _p("milestone-digest-entry", _S, "one digest entry ink"),
    # Relations.
    _p("dependency", _D),
    _p("dependency-halo", _U, "no committed slide draws a dependency halo"),
    _p("relation-label", _S, "a relation label is label text with the text role's ink (#880)"),
    _p("network-node", _S, "one network node paint"), _p("network-edge", _S, "one network edge paint"),
    _p("critical-edge", _U, "no committed slide draws a critical edge"),
    # Legend, notes and annotations.
    _p("legend-swatch", _D), _p("legend-label", _D),
    _p("project-note", _S, "one project note ink"), _p("annotation-list-text", _S, "one annotation list ink"),
    _p("note-index", _S, "one note index ink"),
    _p("annotation-box", _D), _p("annotation-text", _D), _p("annotation-leader", _D),
    _p("annotation-kind-bar", _S, "kind identity is the purpose itself; one bar paint per kind"),
    _p("annotation-kind-accent", _S, "one accent edge paint"), _p("annotation-kind-stamp", _S, "one stamp paint"),
    _p("annotation-artwork", _D),
    _p("annotation-border-start", _S, "one role per logical side"), _p("annotation-border-end", _S, "one role per logical side"),
    _p("annotation-border-top", _S, "one role per logical side"), _p("annotation-border-bottom", _S, "one role per logical side"),
    _p("annotation-kind-label", _S, "one kind label ink"), _p("annotation-kind-secondary", _S, "one secondary ink"),
    _p("annotation-heading", _S, "one annotation heading ink"),
    # Summary panels.
    _p("summary-header", _S, "one header ink"), _p("summary-metric", _S, "one metric ink"),
    _p("summary-figure-value", _S, "one figure value ink"), _p("summary-figure-caption", _S, "one figure caption ink"),
    _p("summary-caption", _S, "one caption ink"), _p("summary-unit", _S, "one unit ink"),
)


def purpose_classifications() -> tuple[PurposeClassification, ...]:
    """Return the reviewed purpose classifications in canonical order."""
    return _PURPOSES


def validate_purpose_classifications(classifications: tuple[PurposeClassification, ...],
                                     registered: frozenset[str] | set[str]) -> dict[str, PurposeClassification]:
    """Require exactly one reviewed classification for every registered purpose."""
    by_purpose: dict[str, PurposeClassification] = {}
    for index, item in enumerate(classifications):
        if item.disposition not in DISPOSITIONS or item.purpose in by_purpose or (item.disposition != "distinct" and not item.reason):
            raise _diagnostic_error("E_PRESENTATION_PURPOSE_CLASSIFICATION_INVALID", f"index={index}, purpose={_shown(item.purpose)}, disposition={_shown(item.disposition)}, reasonPresent={bool(item.reason)}; expected unique purpose, one of {DISPOSITIONS!r}, and a reason unless distinct")
        by_purpose[item.purpose] = item
    unknown = sorted(set(by_purpose) - set(registered))
    if unknown:
        raise _diagnostic_error("E_PRESENTATION_PURPOSE_CLASSIFICATION_UNKNOWN", f"purposes={unknown!r}; expected only registered purposes")
    missing = sorted(set(registered) - set(by_purpose))
    if missing:
        raise _diagnostic_error("E_PRESENTATION_PURPOSE_UNCLASSIFIED", f"purposes={missing!r}; classify each as distinct, single-role with a reason, gap, or unpainted in model/semantic_realization.py")
    return by_purpose
