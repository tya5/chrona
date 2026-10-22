"""Role-marked runs of one group header on a shared baseline (#1192).

A header template that marks placeholders with Theme text roles (``{ordinal|group-ordinal}``) completes as several
Text placements, one per run, in template order. Each run is measured with its own role's metric (the transform and
compression its viewer sees), starts where the previous run and the gap before it end, and shares the header's
baseline. Layout owns this arithmetic; Scene emits each placement as an ordinary Text primitive with the role's ink and
every adapter draws it as it draws any other text.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.model import LayoutError, geometry_sum
from chrona.presentation.layout.surface_quality import CollisionDomain, FitWarning, TextPlacement
from chrona.presentation.layout.text import _cjk, _wrap_units, ellipsize_text, measure_text_width, metric_for_role, place_text

DEFAULT_ROLE = "groupHeader"


def run_placement_prefix(group_id: str) -> str:
    """The placement id of run ``k`` is ``<prefix><k>``."""
    return f"group-header:{group_id}#run"


def validate_group_header_roles(role_pointers: tuple[tuple[str, str], ...], theme_tokens: Any) -> None:
    """Fail a header template that marks a role the Theme does not declare, or declares without ink (#1192).

    The pointer is the View template the author must change; the missing Theme pointer is in the detail. A role's
    typography is resolved here too, so a malformed role is reported before any measurement.
    """
    for role, pointer in role_pointers:
        if not theme_tokens.has_role(role):
            raise LayoutError("E_THEME_ROLE_REQUIRED", pointer,
                              detail=f"the Theme declares no text role {role!r} (/body/roles/{role})")
        if theme_tokens.optional_color(role, "fill") is None:
            raise LayoutError("E_THEME_ROLE_REQUIRED", pointer,
                              detail=f"text role {role!r} declares no ink (/body/roles/{role}/fill)")
        theme_tokens.text_treatment(role)


@dataclass
class _Run:
    role: str
    source: str
    content: str
    shape: dict[str, Any]
    gap: float
    width: float
    state: str = "fit"


@dataclass(frozen=True)
class GroupHeaderRunSegment:
    """One source-ordered, role-preserving piece in a wrapped group-header line."""

    text: str
    role: str
    gap: float
    width: float
    block_size: float
    font_size: float


def wrap_group_header_runs(*, runs: tuple[tuple[str, str | None], ...], available_inline: float,
                           theme_tokens: Any, font_metrics: Any
                           ) -> tuple[tuple[GroupHeaderRunSegment, ...], ...]:
    """Wrap resolved header runs without changing their roles, order or measured spaces."""
    resolved = _resolve_runs(runs, theme_tokens, font_metrics)
    tokens: list[GroupHeaderRunSegment] = []
    previous_shape: dict[str, Any] | None = None
    for run in resolved:
        shape = run.shape
        treatment = theme_tokens.text_treatment(run.role)
        block_size = shape["font_size"] * float(treatment.line_height)
        units = _wrap_units(run.source)
        for index, unit in enumerate(units):
            if index == 0:
                gap = run.gap
            else:
                previous_unit = units[index - 1]
                separator = " " if not (_cjk(unit[0]) or _cjk(previous_unit[-1])) else ""
                gap = _painted(separator, shape) + _trailing_spacing(shape)
            if index == 0 and previous_shape is not None and run.gap == 0:
                # Adjacent template runs still have the same role-aware character spacing as one painted line.
                gap = _trailing_spacing(previous_shape)
            tokens.append(GroupHeaderRunSegment(
                unit, run.role, gap, measure_text_width(unit, **shape), block_size, shape["font_size"]))
        previous_shape = shape

    lines: list[list[GroupHeaderRunSegment]] = []
    line: list[GroupHeaderRunSegment] = []
    line_width = 0.0
    for token in tokens:
        proposed = line_width + token.gap + token.width
        if line and available_inline > 0 and proposed > available_inline:
            lines.append(line)
            line = [replace(token, gap=0.0)]
            line_width = token.width
            continue
        if not line and token.gap:
            token = replace(token, gap=0.0)
        line.append(token)
        line_width += token.gap + token.width
    if line:
        lines.append(line)
    return tuple(tuple(items) for items in lines) or ((),)


def place_wrapped_group_header_runs(*, group_id: str,
                                    lines: tuple[tuple[GroupHeaderRunSegment, ...], ...],
                                    start: Decimal, size: Decimal, top_block: float,
                                    line_blocks: tuple[float, ...], theme_tokens: Any, font_metrics: Any
                                    ) -> tuple[TextPlacement, ...]:
    """Place premeasured wrapped segments on shared per-line baselines in source order."""
    placements: list[TextPlacement] = []
    prefix = run_placement_prefix(group_id)
    line_offset = 0.0
    for line_index, line in enumerate(lines):
        cursor = float(start)
        line_block = line_blocks[line_index] if line_index < len(line_blocks) else 0.0
        top_inset = min(((segment.block_size - segment.font_size) / 2 for segment in line), default=0.0)
        for segment in line:
            cursor += segment.gap
            baseline = (top_block + line_offset + (segment.block_size - segment.font_size) / 2
                        - top_inset + segment.font_size)
            placement_id = f"{prefix}{len(placements)}"
            placements.append(place_text(
                placement_id=placement_id, source_ref=group_id, content=segment.text,
                inline=cursor, baseline_block=baseline, typography_role=segment.role,
                theme_tokens=theme_tokens, font_metrics=font_metrics,
                collision_region=f"group:{group_id}",
                collision_domain=CollisionDomain("group-header", group_id),
                source_content=segment.text, available_inline_start=float(start),
                available_inline_size=float(size)))
            cursor += segment.width
        line_offset += line_block
    return tuple(placements)


def _shape(theme_tokens: Any, role: str, font_metrics: Any) -> dict[str, Any]:
    treatment = theme_tokens.text_treatment(role)
    return dict(font_size=float(treatment.font_size), font_metrics=metric_for_role(theme_tokens, role, font_metrics),
                letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
                numeric_spacing=treatment.numeric_spacing)


def _painted(text: str, shape: dict[str, Any]) -> float:
    """The advance of whitespace as painted: each character is followed by its letter-spacing (#1238).

    ``measure_text_width`` counts the spacing between characters only; the spacing after the last one is the gap's.
    """
    if not text:
        return 0.0
    spacing = measure_text_width("  ", **shape) - 2 * measure_text_width(" ", **shape)
    return measure_text_width(text, **shape) + spacing


def _trailing_spacing(shape: dict[str, Any]) -> float:
    """The letter-spacing painted after the last character of a run (not part of its measured width)."""
    return measure_text_width("  ", **shape) - 2 * measure_text_width(" ", **shape)


def _resolve_runs(runs: tuple[tuple[str, str | None], ...], theme_tokens: Any, font_metrics: Any) -> list[_Run]:
    """Split edge whitespace into gaps (measured in the face of the text it belongs to) and measure each run.

    Literal edge spaces are the gap between two runs (Spec 50 section 3.4). As in one painted line, the gap also holds
    the letter-spacing after the last character before the whitespace and after each whitespace character (#1238).
    """
    resolved: list[_Run] = []
    pending = 0.0
    spaced = False  # whitespace was seen since the last run
    previous: dict[str, Any] | None = None
    for text, declared in runs:
        role = declared or DEFAULT_ROLE
        shape = _shape(theme_tokens, role, font_metrics)
        core = text.strip()
        if not core:
            if text:
                pending += _painted(text, shape)
                spaced = True
            continue
        lead = text[:len(text) - len(text.lstrip())]
        trail = text[len(text.rstrip()):]
        gap = pending + _painted(lead, shape)
        spaced = spaced or bool(lead)
        if spaced and previous is not None:
            gap += _trailing_spacing(previous)
        pending = _painted(trail, shape)
        spaced = bool(trail)
        previous = shape
        resolved.append(_Run(role, core, core, shape, gap, measure_text_width(core, **shape)))
    return resolved


def _extent(runs: list[_Run]) -> float:
    """The inline size of the runs and the gaps before them, as one correctly rounded sum."""
    return geometry_sum(value for run in runs for value in (run.gap, run.width))


def _give_way(runs: list[_Run], available: float) -> None:
    """Shorten the last run first, then the one before it, until the block fits ``available``."""
    for index in reversed(range(len(runs))):
        if _extent(runs) <= available:
            return
        before = geometry_sum((_extent(runs[:index]), runs[index].gap))
        run = runs[index]
        budget = available - before
        shortened = ellipsize_text(run.source, available_inline=budget, **run.shape) if budget > 0 else ""
        if shortened:
            run.content, run.state = shortened, "ellipsized"
            run.width = measure_text_width(shortened, **run.shape)
            return
        run.content, run.state, run.gap, run.width = "", "suppressed", 0.0, 0.0


def place_group_header_runs(*, group_id: str, runs: tuple[tuple[str, str | None], ...], start: Decimal,
                            size: Decimal, bounded: bool, baseline_block: float, header_block_size: float,
                            theme_tokens: Any, font_metrics: Any,
                            ) -> tuple[tuple[TextPlacement, ...], tuple[FitWarning, ...]]:
    """Complete one header's runs from ``start`` on one baseline.

    ``size`` is the inline room from ``start``; the block is held to it only when ``bounded`` (a group tab leaves
    less room), as an unmarked header is, and otherwise it keeps today's unbounded text. A run that gives way keeps its full source, and a run that cannot keep even an ellipsis is
    suppressed with the same typed warning.
    """
    resolved = _resolve_runs(runs, theme_tokens, font_metrics)
    if bounded and _extent(resolved) > float(size):
        _give_way(resolved, float(size))
    placements: list[TextPlacement] = []
    warnings: list[FitWarning] = []
    advances: list[float] = [float(start)]
    prefix = run_placement_prefix(group_id)
    for index, run in enumerate(resolved):
        advances.append(run.gap)
        cursor = geometry_sum(advances)
        placement_id = f"{prefix}{index}"
        placed = place_text(
            placement_id=placement_id, source_ref=group_id, content=run.content or run.source,
            overflow="ellipsized" if run.state == "ellipsized" else "fit", inline=cursor, baseline_block=baseline_block,
            typography_role=run.role, theme_tokens=theme_tokens, font_metrics=font_metrics,
            collision_region=f"group:{group_id}", collision_domain=CollisionDomain("group-header", group_id),
            source_content=run.source, available_inline_start=float(start),
            available_inline_size=float(size))
        if run.state == "suppressed":
            placed = replace(placed, overflow="suppressed", required=False, selected_rung="suppress")
        else:
            advances.append(run.width)
        if run.state != "fit":
            warnings.append(FitWarning(
                "W_LAYOUT_TEXT_ELLIPSIZED", placement_id, group_id, "group-header-text",
                "ellipsize-with-source" if run.state == "ellipsized" else "suppress-with-source",
                measure_text_width(run.source, **run.shape), header_block_size,
                float(size), header_block_size))
        placements.append(placed)
    return tuple(placements), tuple(warnings)
