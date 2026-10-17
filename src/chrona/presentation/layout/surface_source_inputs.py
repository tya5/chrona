"""Owns source inputs and visual advances; reads closed semantic content and Theme/icon resources."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

from dataclasses import replace

from chrona.presentation.contracts.resources import ViewInput, ViewRowMode
from chrona.presentation.heading_text import HeadingTextPrograms
from chrona.presentation.layout.label_visual_measurement import resolve_label_visual_advances
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.sources import SourceInput, SourceTextRun
from chrona.presentation.layout.surface_content import detail_source_inputs
from chrona.presentation.layout.surface_quality import VisualRequest
from chrona.presentation.model.surface_content import HeadingContent, SummaryContent, SurfaceContentInput, TableContent
from chrona.presentation.model.theme_tokens import ThemeTokenView


def surface_source_inputs(project, view, projection, summary, *, content, table,
                          heading, view_heading, visual_requests, icon_assets, theme):
    """Close visual advances before assembling the same source facts for measurement."""
    annotation_input = _annotation_source_input(view, content, visual_requests, icon_assets, theme)
    return _source_inputs(project, view, projection, summary, annotation_input,
                          content=content, table=table, heading=heading, view_heading=view_heading)


def network_deadline_source_input(projection: Any, theme: Mapping[str, Any]) -> SourceInput:
    """Supplemental measured node-footer runs; this is not an authorable Layout source."""
    network = getattr(projection, "network", None)
    tokens = ThemeTokenView(theme)
    role = "deadline-caption" if tokens.has_role("deadline-caption") else "text"
    runs = tuple(
        SourceTextRun(node.deadline.label, role, node.object_id)
        for node in getattr(network, "nodes", ())
        if node.deadline is not None
    )
    return SourceInput(runs=runs, typography_role=role, content_present=bool(runs))


def _source_inputs(project: dict[str, Any], view: ViewInput, projection: Any,
                   summary: SummaryContent, annotation_input: SourceInput | None = None, *,
                   content: SurfaceContentInput,
                   table: TableContent | None = None,
                   heading: HeadingContent | None = None,
                   view_heading: HeadingContent | None = None) -> dict[str, SourceInput]:
    """Declare what each slot will hold, for measurement before layout.

    The `legend` entry is a placeholder: Layout measures the legend from the entries it
    draws and the legend slot's own arrangement (`legend_source_input`).
    """
    lane_mode = view.rows.mode is ViewRowMode.LANES
    rows = projection.lane_rows if lane_mode else projection.rows or ()
    resolved = getattr(projection, "rows_resolved", False)
    row_count = len(rows) if resolved else len(rows) or len(projection.items)
    if lane_mode and (not rows or table is None):
        raise LayoutError("E_LAYOUT_LANE_TABLE_ENVELOPE", "/body/rows/laneTable")
    table_lines = (tuple(cell.content for cell in table.cells if cell.column_id == "Lane")
                   if lane_mode and table is not None else
                   tuple(row.label for row in rows) or (() if resolved else tuple(item.title for item in projection.items)))
    span_days = max(1, (projection.window[1] - projection.window[0]).days)
    network = getattr(projection, "network", None)
    notes = tuple(text for _, text in content.notes)
    sources = {
        "title": _title_source(project, heading),
        "table": SourceInput(
            table_lines,
            row_count, len(view.table_columns) or 1, table=table),
        "timeline": SourceInput(item_count=row_count, span_days=span_days),
        "timeline-axis": SourceInput(span_days=span_days, typography_role="axis",
                                     axis_tiers=content.axis_tiers),
        "network": SourceInput(
            runs=tuple(SourceTextRun(node.title, "text", node.object_id)
                       for node in network.nodes) if network is not None else (),
            typography_role="text"),
        "summary": _summary_source(summary),
        "legend": SourceInput(("legend",), typography_role="legend"),
        "notes": SourceInput(notes or ("notes",), typography_role="annotation"),
    }
    if view_heading is not None:
        sources.update(heading_part_sources(view_heading))
    sources.update(detail_source_inputs(content))
    if annotation_input is not None:
        sources["annotations"] = annotation_input
    return sources


def heading_part_sources(heading: HeadingContent) -> dict[str, SourceInput]:
    sources = {}
    for part, text, role in (("title", heading.title, "heading"),
                             ("kicker", heading.kicker, "kicker"),
                             ("subtitle", heading.subtitle, "subtitle")):
        source_ref = f"heading.{part}"
        sources[source_ref] = SourceInput(
            lines=(text,) if text else (), typography_role=role,
            runs=(SourceTextRun(text, role, source_ref),) if text else (),
            content_present=bool(text), run_flow="block", text_wrap=heading.text_wrap)
    return sources


def bind_heading_dependencies(inputs: dict[str, SourceInput], programs: HeadingTextPrograms) -> dict[str, SourceInput]:
    """Attach closed per-part references, never derive them from formatted/project text."""
    aliases = {"title": "title", "kicker": "kicker", "subtitle": "subtitle",
               "heading.title": "title", "heading.kicker": "kicker", "heading.subtitle": "subtitle"}
    result = dict(inputs)
    for source in ("title", "heading.title", "heading.kicker", "heading.subtitle"):
        value = result.get(source)
        if value is None:
            continue
        runs = []
        for run in value.text_runs():
            part = aliases.get(run.source_ref, aliases[source])
            program = getattr(programs, part)
            runs.append(replace(run, figure_dependencies=program.figure_ids if program is not None else frozenset()))
        result[source] = replace(value, runs=tuple(runs))
    return result


def _summary_source(summary: SummaryContent) -> SourceInput:
    """Retain panel grouping only when an arrangement opts into grouped flow."""
    if summary.absent:
        return SourceInput(content_present=False)
    if not any(panel.arrangement == "inline" for panel in summary.panels):
        return SourceInput(runs=tuple(SourceTextRun(run.content, run.typography_role) for run in summary.runs))
    return SourceInput(runs=tuple(SourceTextRun(run.content, run.typography_role, run.placement_id)
                                  for run in summary.runs), summary=summary)


def _title_source(project: dict[str, Any], heading: HeadingContent | None) -> SourceInput:
    """The title slot's content: one `heading` line, plus a `subtitle` line when the View declares one (#991)."""
    title = heading.title if heading is not None else project["project"].get("title", "Chrona")
    subtitle = heading.subtitle if heading is not None else None
    if title is None:
        runs = tuple(SourceTextRun(text, role, part) for part, text, role in (
            ("kicker", heading.kicker, "kicker"), ("subtitle", subtitle, "subtitle")) if text is not None)
        return SourceInput(tuple(run.content for run in runs), typography_role="heading", runs=runs,
                           run_flow="block", text_wrap=heading.text_wrap, content_present=bool(runs))
    if heading is not None and heading.kicker is not None:
        runs = (SourceTextRun(heading.kicker, "kicker", "kicker"), SourceTextRun(title, "heading", "title"))
        if subtitle is not None:
            runs += (SourceTextRun(subtitle, "subtitle", "subtitle"),)
        return SourceInput(tuple(run.content for run in runs), typography_role="heading", runs=runs,
                           run_flow="block", text_wrap=heading.text_wrap)
    if subtitle is None:
        return SourceInput((title,), typography_role="heading",
                           text_wrap=heading.text_wrap if heading is not None else "forbid")
    return SourceInput((title, subtitle), typography_role="heading",
                       runs=(SourceTextRun(title, "heading"), SourceTextRun(subtitle, "subtitle")),
                       text_wrap=heading.text_wrap if heading is not None else "forbid")


def _annotation_source_input(view: ViewInput, content: SurfaceContentInput,
                             visual_requests: tuple[VisualRequest, ...],
                             icon_assets: dict[str, Any], theme: Mapping[str, Any]) -> SourceInput:
    """Build annotation measurements from the same closed visuals Layout composes."""
    visible = view.visibility.annotations
    mode = visible.get("mode", "none") if isinstance(visible, Mapping) else visible
    if mode == "none" or not content.annotations:
        return SourceInput(content_present=False)
    tokens = ThemeTokenView(theme)
    runs = []
    for annotation in content.annotations:
        annotation_id = annotation.annotation_id
        prefix = f"{annotation.number}. " if annotation.number is not None else ""
        advances = resolve_label_visual_advances(
            f"annotation-text:{annotation_id}", "annotation", visual_requests=visual_requests,
            icon_assets=icon_assets, theme_tokens=tokens,
        )
        inline_advance = sum((Decimal(str(width + gap)) for _, _, width, gap in advances), Decimal(0))
        runs.append(SourceTextRun(prefix + annotation.content, "annotation",
                                  f"annotation-text:{annotation_id}", inline_advance))
    return SourceInput(runs=tuple(runs), typography_role="annotation")
