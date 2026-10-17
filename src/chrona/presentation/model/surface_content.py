"""Normalized presentation content inputs."""
from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

from chrona.presentation.model.axis_color_scale import AxisBandFillSpec
from chrona.presentation.model.date_basis import DisplayDateRange
from chrona.presentation.model.placement_candidates import PlacementCandidate
from chrona.presentation.model.projection import ObservationState, ReviewItem, display_finish_delta
from chrona.presentation.model.style_rules import OccurrenceStyleIndex, StyleOccurrenceKey


def _diagnostic_error(code: str, detail: str) -> ValueError:
    """Build a stable surface-content error with the invalid operand detail."""
    return ValueError(f"{code}: {detail}")
from chrona.presentation.table_presentation import BooleanPresencePresentation


@dataclass(frozen=True)
class HeadingContent:
    """Normalized kicker, title and subtitle text for one table-timeline heading."""

    title: str | None
    subtitle: str | None = None
    kicker: str | None = None
    text_wrap: Literal["allow", "forbid"] = "forbid"


@dataclass(frozen=True)
class SummaryTextRun:
    """One normalized, ordered summary line before Layout gives it geometry."""

    placement_id: str
    source_ref: str
    content: str
    typography_role: str
    semantic_id: str = ""


@dataclass(frozen=True)
class SummaryPanel:
    """One selected summary panel and its canonical text-run sequence."""

    panel_id: str
    runs: tuple[SummaryTextRun, ...]
    arrangement: str = "stack"


@dataclass(frozen=True)
class SummaryContent:
    """Immutable semantic summary facts shared by measurement and placement."""

    panels: tuple[SummaryPanel, ...]
    absent: bool = False

    @property
    def runs(self) -> tuple[SummaryTextRun, ...]:
        return tuple(run for panel in self.panels for run in panel.runs)


@dataclass(frozen=True)
class RelationPresentationFact:
    """One selected dependency fact closed before Layout resolves geometry."""

    relation_id: str
    source_object_id: str
    source_endpoint: str
    target_object_id: str
    target_endpoint: str
    lag: object
    lag_calendar: str | None
    semantic_id: str
    label_content: tuple[str, ...] = ()
    critical: bool = False
    source_title: str = ""
    target_title: str = ""


@dataclass(frozen=True)
class TableColumnWidth:
    """Closed measured-allocation intent, normalized before Layout ingress."""

    minimum: str
    maximum: str
    fraction: float = 0.0

    @property
    def flexible(self) -> bool:
        return self.maximum in {"fill", "fr"}


@dataclass(frozen=True)
class TableColumnContent:
    """One semantic table column, retaining View intent without schema maps."""

    column_id: str
    header: str
    align: str
    width: TableColumnWidth
    header_orientation: str = "horizontal"
    text_wrap: Literal["allow", "forbid"] = "forbid"
    column_source: str | tuple[tuple[str, str], ...] | None = None

    def __post_init__(self) -> None:
        source = self.column_source
        if isinstance(source, Mapping):
            object.__setattr__(self, "column_source", tuple(sorted(source.items())))
        elif isinstance(source, list):
            object.__setattr__(self, "column_source", tuple(tuple(pair) for pair in source))


@dataclass(frozen=True)
class TableCellContent:
    """One rendered table fact with its selected, finite Scene semantic."""

    object_id: str
    column_id: str
    content: str
    semantic_id: str
    typography_role: str = "text"
    affix_prefix: str = ""
    affix_suffix: str = ""
    # Forecast deltas are required full text; Layout must refuse truncation/overflow.
    required: bool = False
    # Exact source row/member identity selected before table measurement.
    style_key: StyleOccurrenceKey | None = None


@dataclass(frozen=True)
class TableRowLevel:
    """One table row's hierarchy facts, addressed by the keys its cells use."""

    keys: tuple[str, ...]
    grouped: bool
    depth: int = 0


@dataclass(frozen=True)
class TableContent:
    """Typed table facts normalized once, before measurement and composition."""

    columns: tuple[TableColumnContent, ...]
    cells: tuple[TableCellContent, ...]
    cell_objects: tuple[tuple[str, str, str, bool], ...]
    hierarchy_column: str | None
    row_levels: tuple[TableRowLevel, ...]
    # Rows of a header group sit one declared step under their header (#1065): field grouping with header
    # presentation, a hierarchy column, and no other nesting.
    indent_under_headers: bool = False


@dataclass(frozen=True)
class AnnotationIntent:
    """One schema-validated annotation fact detached before Layout ingress."""

    annotation_id: str
    purpose: str
    anchor: dict[str, str]
    side: str
    alignment: str
    content: str
    number: int | None = None
    fallback_ladder: tuple[str, ...] = ()
    candidates: tuple[PlacementCandidate, ...] = ()
    # The `kind` of the Project annotation a `projectAnnotation` reference selects (#584);
    # None for a View annotation that carries its own text.
    kind: str | None = None
    # The title of the anchored Project object, the `{subject}` of a kind header (#584).
    subject: str = ""
    # The id of the anchored Project object, the `{subjectId}` of a kind header (#991).
    subject_id: str = ""
    # Presentation-composed kind text; Layout measures these strings without figure substitution.
    kind_header_lines: tuple[str, ...] | None = None
    kind_heading_text: str | None = None
    # Canonical declared View/Project anchor pointer for Layout failures only; never enters
    # placement equality, hashing, repr or Scene output.
    anchor_source_ref: str = field(default="/", kw_only=True, compare=False, hash=False, repr=False)


@dataclass(frozen=True)
class AxisSecondaryIntent:
    """A second form of the same interval, drawn smaller in the same cell (#493)."""

    form: str
    name_table_id: str
    typography_role: str
    placement: str  # "stacked" | "inline"


@dataclass(frozen=True)
class AxisLabelIntent:
    """Finite label vocabulary and placement policy for one labels tier."""

    form: str | None
    candidate_forms: tuple[tuple[str, str], ...]
    align: str
    overflow: str
    orientation: str
    name_table_id: str
    secondary: AxisSecondaryIntent | None = None


@dataclass(frozen=True)
class AxisTier:
    """One View-declared axis responsibility before Layout creates geometry."""

    unit: str
    every: int
    role: str
    label: AxisLabelIntent | None = None
    typography_role: str | None = None
    fill_scale: AxisBandFillSpec | None = None


@dataclass(frozen=True)
class SurfaceLegendEntry:
    """One measured-and-placed legend entry, with identity independent of its visual role."""

    role: str
    label: str
    source_ref: str | None = None
    swatch_shape: str | None = None

    @property
    def source_identity(self) -> str:
        return self.source_ref if self.source_ref is not None else self.role

    @property
    def text_placement_id(self) -> str:
        return (f"legend-period:{self.source_ref}" if self.source_ref is not None
                else f"legend:{self.role}")

    @property
    def swatch_placement_id(self) -> str:
        return (f"legend-period-swatch:{self.source_ref}" if self.source_ref is not None
                else f"legend-swatch:{self.role}")


@dataclass(frozen=True)
class SurfaceContentInput:
    """Selected presentation facts normalized once before Scene construction."""

    table_columns: tuple[TableColumnContent, ...]
    table_cells: tuple[TableCellContent, ...]
    relations: tuple[RelationPresentationFact, ...]
    annotations: tuple[AnnotationIntent, ...]
    show_member_labels: bool
    label_placement: str
    label_content: tuple[str, ...]
    label_side: str
    label_overflow: str
    relation_overflow: str
    group_presentation: str
    axis_tiers: tuple[AxisTier, ...]
    axis_fiscal_start_month: int
    as_of: date | None
    as_of_label: str
    annotation_numbered: bool
    calendar_closed: tuple[date, ...]
    calendar_exceptions: tuple[date, ...]
    notes: tuple[tuple[str, str], ...]
    legend_entries: tuple[SurfaceLegendEntry, ...]
    coverage_text: str
    summary: SummaryContent
    template_values: tuple[tuple[str, str], ...]
    group_details: tuple[tuple[str, str, str], ...]
    milestones: tuple[tuple[str, str, date], ...]
    observation_columns: tuple[tuple[str, str], ...]
    observation_rows: tuple[tuple[str, str, str, tuple[tuple[str, str], ...]], ...]
    label_fallback: tuple[str, ...] = ()
    label_text_role: str | None = None  # the Theme text role of the plot member labels (#1141)
    annotation_fallback: tuple[str, ...] = ()
    link_mode: str = "none"
    title_link_columns: tuple[str, ...] = ()
    # (table row id, column id, object id, is selected-current item).  This is
    # identity only: Scene uses it to attach presentation metadata and never to
    # infer geometry or re-resolve a View row.
    table_cell_objects: tuple[tuple[str, str, str, bool], ...] = ()
    # Completed data-dependent paint selected before Scene construction.  The
    # value is keyed by semantic source object, never by geometry or renderer.
    scale_target_role: str | None = None
    scale_paints: tuple[tuple[str, str], ...] = ()
    scale_legend_paints: tuple[tuple[str, str], ...] = ()
    progress_fill_source: str | None = None
    table_hierarchy_column: str | None = None
    table_indent_under_headers: bool = False
    row_decoration: str = "none"
    group_decoration: str = "all"
    # Composed group-header text, (group id, text), in display order (#583); a
    # group without an entry keeps its entity title.
    group_headers: tuple[tuple[str, str], ...] = ()
    # The role-marked runs of a header, (group id, ((text, Theme role or None), ...)), only for a group whose
    # template marks a placeholder (#1192); `group_headers` keeps the same text, joined.
    group_header_runs: tuple[tuple[str, tuple[tuple[str, str | None], ...]], ...] = ()
    # Where the as-of label sits on the plot: `top` margin (default) or the plot `foot` (#991).
    as_of_placement: str = "top"
    # Completed per-group band colour, (group id, "#RRGGBB"), from the View's
    # `grouping.tint` scale (#583); Scene replaces only the band's visible channel.
    group_tints: tuple[tuple[str, str], ...] = ()
    # Completed per-annotation kind colour, (annotation id, "#RRGGBB"), from the Theme's
    # `annotationKinds` (#584); Scene replaces only the fill of the kind bar, accent and stamp.
    annotation_kind_paints: tuple[tuple[str, str], ...] = ()
    # Required plot-label text of each point drawn on the row of the span it
    # attaches to (#486): title, planned date and finish delta, never dropped.
    attached_labels: tuple[tuple[str, str], ...] = ()
    # View literal overrides plus Layout-bound template copy, keyed by a headed slot node.
    slot_heading_text: tuple[tuple[str, str], ...] = ()
    # Completed Scheme colours keyed by neutral axis-band placement identity (#490).
    axis_band_paints: tuple[tuple[str, str], ...] = ()
    relation_overflow_declared: bool = False
    # Completed fill overrides for Actual marks, keyed by semantic source object.
    actual_variance_paints: tuple[tuple[str, str], ...] = ()
    # Evaluated Style intent remains attached to exact source occurrence identity.
    style_intents: OccurrenceStyleIndex = field(default_factory=OccurrenceStyleIndex)


@dataclass(frozen=True)
class ResolvedPresentationInput:
    """One derived input boundary between authoring resources and Scene geometry."""

    title: str
    window: tuple[date, date]
    items: tuple[object, ...]
    settings: dict
    surface_content: SurfaceContentInput


def table_value(item: ReviewItem, project: dict[str, Any], source: Any, row_index: int | None = None) -> Any:
    """Resolve one renderer-neutral table cell from normalized review data."""
    if isinstance(source, str):
        if source == "path":
            return " / ".join(str(project.get("objects", {}).get(object_id, {}).get("title", object_id))
                              for object_id in item.hierarchy_path)
        return {"id": item.object_id, "title": item.title, "objectType": item.source_type,
                "entity": item.group_label, "rowIndex": row_index, "totalFloat": item.total_float,
                "wbsCode": item.wbs_code}.get(source)
    if "field" in source or "fieldRole" in source:
        return item.field_bindings.read(item.fields, source)
    if "facet" in source:
        return {"planned": item.planned, "actual": item.actual,
                "finishDelta": display_finish_delta(item)}.get(source["facet"])
    if "scenario" in source:
        if item.source_kind != "scenario" or item.scenario_id is None:
            return None
        if source["scenario"] == "id":
            return item.scenario_id
        declared = project.get("scenarios", {}).get(item.scenario_id, {})
        return declared.get("title") if isinstance(declared, dict) else None
    facet = source["comparisonFacet"]
    missing_actual = (True if item.observation_state == ObservationState.DUE_UNOBSERVED else
                      False if item.observation_state == ObservationState.RECORDED else None)
    return {"finishDelta": display_finish_delta(item), "missingActual": missing_actual,
            "progress": (item.actual or {}).get("progress")}.get(facet)


_WORD_BREAKS = re.compile(r"[\s\u2010\u2011-]+")


def initials(text: str) -> str:
    """The abbreviation of a multi-word name; a single word is shown whole (#1629).

    Words split on Unicode whitespace and hyphens, and a word is one with a letter or digit. With two or more words
    the result is the upper-cased first letter or digit of each (leading punctuation is skipped, combining marks that
    follow it stay), by the Unicode default mapping of ``str.upper``, never a locale tailoring. With exactly one word
    the result is that word as written, so `Raj`, `pm`, an unspaced CJK name and `QT` are not cut to one letter. A text
    without a letter or digit gives the empty string.
    """
    parts, words = [], []
    for word in _WORD_BREAKS.split(unicodedata.normalize("NFC", text)):
        start = next((index for index, char in enumerate(word) if unicodedata.category(char)[0] in "LN"), None)
        if start is None:
            continue
        words.append(word)
        end = start + 1
        while end < len(word) and unicodedata.category(word[end])[0] == "M":
            end += 1
        parts.append(word[start:end].upper())
    if len(words) == 1:
        return words[0]
    return unicodedata.normalize("NFC", "".join(parts))


def display_value(value: Any, missing: str | Mapping[str, Any], formatter: str | BooleanPresencePresentation = "text", *,
                  locale: str = "en-US", zero: str = "signed", end_display: str = "exclusive",
                  transform: str | None = None) -> str:
    """Format a normalized table value according to its declared View contract."""
    if value is None:
        if isinstance(missing, Mapping):
            return str(missing["text"])  # an author-chosen literal, shown exactly (#1288)
        return {"blank": "", "em-dash": "—", "unknown": "unknown",
                "in-progress": "in progress"}[missing]
    if isinstance(value, bool):
        if isinstance(formatter, BooleanPresencePresentation):
            return formatter.when_true if value else formatter.when_false
        raise _diagnostic_error("E_VIEW_BOOLEAN_PRESENTATION", f"valueType=bool, formatter={type(formatter).__name__}; expected presence mapping for boolean values")
    if isinstance(formatter, BooleanPresencePresentation):
        raise _diagnostic_error("E_VIEW_BOOLEAN_PRESENTATION", f"valueType={type(value).__name__}, formatter=presence; expected boolean value")
    if transform == "initials":
        if not isinstance(value, str):
            raise _diagnostic_error("E_VIEW_COLUMN_TRANSFORM", f"valueType={type(value).__name__}, transform=initials; expected a text value")
        return initials(value) or display_value(None, missing, formatter)
    if formatter == "date":
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, dict):
            point = value.get("at", value.get("finish", value.get("end", value.get("start"))))
            return point.isoformat() if isinstance(point, date) else str(point)
    if formatter == "dateRange" and isinstance(value, DisplayDateRange):
        if value.start == value.end:
            return _format_compact_date(value.start, include_year=False, locale=locale)
        return _format_date_range(value.start, value.end, locale=locale)
    if formatter == "dateRange" and isinstance(value, dict):
        start, end = value.get("start"), value.get("end", value.get("finish"))
        if isinstance(start, date) and isinstance(end, date):
            if end_display == "inclusive" and start < end:
                end -= timedelta(days=1)
                if start == end:
                    return _format_compact_date(start, include_year=False, locale=locale)
            return _format_date_range(start, end, locale=locale)
        if isinstance(start, date) and end is None:
            return f"{_format_compact_date(start, include_year=True, locale=locale)} –"
        if isinstance(value.get("at"), date):
            return _format_compact_date(value["at"], include_year=True, locale=locale)
    if formatter == "signedDays" and isinstance(value, int) and not isinstance(value, bool):
        return f"{value:d}d" if value == 0 and zero == "plain" else f"{value:+d}d"
    if formatter == "signedNumber" and isinstance(value, int) and not isinstance(value, bool):
        return f"{value:d}" if value == 0 and zero == "plain" else f"{value:+d}"
    return str(value)


def _format_date_range(start: date, end: date, *, locale: str) -> str:
    if start == end:
        return _format_compact_date(start, include_year=True, locale=locale)
    if start.year == end.year:
        return f"{_format_compact_date(start, include_year=False, locale=locale)} – {_format_compact_date(end, include_year=False, locale=locale)}"
    return f"{_format_compact_date(start, include_year=True, locale=locale)} – {_format_compact_date(end, include_year=True, locale=locale)}"


def _format_compact_date(value: date, *, include_year: bool, locale: str) -> str:
    if locale == "ja-JP":
        rendered = f"{value.month}月{value.day}日"
        return f"{value.year}年{rendered}" if include_year else rendered
    if locale != "en-US":
        raise _diagnostic_error("E_PRESENTATION_LOCALE_UNSUPPORTED", f"locale={locale!r}; expected one of ('en-US', 'ja-JP')")
    months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    rendered = f"{value.day:02d} {months[value.month - 1]}"
    return f"{rendered} {value.year}" if include_year else rendered
