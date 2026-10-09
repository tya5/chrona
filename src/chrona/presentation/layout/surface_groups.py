"""Owns group-header presentation from completed base extents; reads fixed rows, groups, Theme text metrics."""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.group_header_runs import place_group_header_runs
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.surface_quality import CollisionDomain, FitWarning, GroupPlacement, TextPlacement
from chrona.presentation.layout.text import ellipsize_text, measure_text_width, metric_for_role, place_text
from chrona.presentation.layout.vertical_text import place_vertical_label_fit
from chrona.presentation.model.theme_tokens import ThemeTokenError


@dataclass(frozen=True)
class SurfaceGroupPresentation:
    """Ordered group-header text derived from immutable base group extents."""
    text: tuple[TextPlacement, ...]
    warnings: tuple[FitWarning, ...] = ()
    header_content_bounds: tuple[tuple[str, Rect], ...] = ()


@dataclass(frozen=True)
class GroupHeaderExtentUpdate:
    """Typed folded-mark request to replace one completed header extent."""
    source: GroupPlacement
    header_bounds: Rect


@dataclass(frozen=True)
class GroupTabSpec:
    """The Theme-declared tab of a group header (#882), resolved once; lengths are px."""
    inline_size: Decimal
    block_size: Decimal | None
    gap: Decimal
    position: str
    target: str = "header"

    @property
    def reserved(self) -> Decimal:
        """Inline extent of the header the tab and its gap take from the text."""
        return self.inline_size + self.gap


_TAB_ROLE = "group-tab"


def _tab_error(prop: str, value: Any, available: Any = None) -> LayoutError:
    detail = f"{_TAB_ROLE}:{prop}:{value}" + (f":{available}" if available is not None else "")
    return LayoutError("E_LAYOUT_GROUP_TAB_SIZE", f"/body/roles/{_TAB_ROLE}/{prop}", detail=detail)


def _header_content_extent(group: GroupPlacement, start: Decimal,
                           placements: tuple[TextPlacement, ...] | list[TextPlacement]) -> Rect:
    """Retain the band-start inset and the furthest actually shown glyph end, without remeasurement."""
    header = group.header_bounds
    assert header is not None
    right = max((item.bounds.inline + item.bounds.inline_size
                 for item in placements if item.overflow != "suppressed"), default=start)
    return Rect(header.inline, header.block, max(Decimal(0), right - header.inline), header.block_size)


def resolve_group_tab(theme_tokens: Any) -> GroupTabSpec | None:
    """Return the declared group tab, or None when the Theme declares no `group-tab` role or draws none."""
    # A role that declares neither a treatment nor a paint order declares no tab (every Theme without the role
    # draws today's header); one declaring only half of the pair is the Theme token error of every background.
    target = theme_tokens.optional_choice(_TAB_ROLE, "tabTarget", ("header", "tag")) or "header"
    if target == "tag":
        if theme_tokens.writing_mode("groupHeader") != "vertical":
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{_TAB_ROLE}/tabTarget")
        for prop in ("tabInlineSize", "tabBlockSize", "tabPosition"):
            value = (theme_tokens.optional_choice(_TAB_ROLE, prop, ("start", "end"))
                     if prop == "tabPosition" else theme_tokens.optional_number(_TAB_ROLE, prop))
            if value is not None:
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{_TAB_ROLE}/{prop}")
    declared = theme_tokens.optional_background(_TAB_ROLE)
    if declared is None or declared[0] == "none":
        return None
    if target == "tag":
        gap = theme_tokens.optional_number(_TAB_ROLE, "tabGap") or Decimal(0)
        if gap < 0:
            raise _tab_error("tabGap", gap)
        return GroupTabSpec(Decimal(0), None, gap, "start", target)
    inline = theme_tokens.optional_number(_TAB_ROLE, "tabInlineSize")
    if inline is None or inline <= 0:
        raise _tab_error("tabInlineSize", "missing" if inline is None else inline)
    block = theme_tokens.optional_number(_TAB_ROLE, "tabBlockSize")
    if block is not None and block <= 0:
        raise _tab_error("tabBlockSize", block)
    gap = theme_tokens.optional_number(_TAB_ROLE, "tabGap")
    if gap is not None and gap < 0:
        raise _tab_error("tabGap", gap)
    position = theme_tokens.optional_choice(_TAB_ROLE, "tabPosition", ("start", "end")) or "start"
    return GroupTabSpec(inline, block, gap or Decimal(0), position)


def check_group_tab_inline(tab: GroupTabSpec, header: Rect) -> None:
    """Reject a tab plus gap that leaves the header text no inline room."""
    if tab.reserved >= header.inline_size:
        raise _tab_error("tabInlineSize", tab.reserved, header.inline_size)


def group_tab_bounds(tab: GroupTabSpec, header: Rect) -> Rect:
    """Complete the tab Rect on one header (its final extent, after folded marks), rejecting an oversize tab."""
    check_group_tab_inline(tab, header)
    block = tab.block_size if tab.block_size is not None else header.block_size
    if block > header.block_size:
        raise _tab_error("tabBlockSize", block, header.block_size)
    inline = header.inline if tab.position == "start" else header.inline + header.inline_size - tab.inline_size
    return Rect(inline, header.block, tab.inline_size, block)


def group_tag_bounds(tab: GroupTabSpec, column: tuple[float, float], rows: Rect) -> Rect:
    """One gap-inset tag cell shared by its completed text and plate."""
    start, size = (Decimal(str(value)) for value in column)
    inline, block = size - 2 * tab.gap, rows.block_size - 2 * tab.gap
    if inline <= 0 or block <= 0:
        raise _tab_error("tabGap", tab.gap, min(size, rows.block_size))
    return Rect(start + tab.gap, rows.block + tab.gap, inline, block)


def compose_group_presentation(*, request: Any, rows: tuple[Any, ...],
                               review_rows: tuple[Any, ...], groups: tuple[GroupPlacement, ...],
                               body_size: float,
                               tag_column: tuple[float, float] | None = None) -> SurfaceGroupPresentation:
    """Place declared group labels inside completed group-header bounds."""
    labels = {row.group_id: next((item.group_label for item in review_row.items if item.group_label), row.group_id)
              for review_row, row in zip(review_rows, rows, strict=True) if row.group_id}
    # A View-declared header template replaces the title text only (#583).
    labels.update(dict(request.surface_content.group_headers))
    marked = dict(request.surface_content.group_header_runs)
    if tag_column is not None:
        if request.theme_tokens.optional_number("groupHeader", "labelInset") is not None:
            raise LayoutError("E_THEME_ROLE_PROPERTY_UNSUPPORTED", "/body/roles/groupHeader/labelInset",
                              detail="labelInset is horizontal; vertical groupHeader tags use tabGap")
        if any(group_id in marked for group_id in labels):
            # A vertical tag is one rotated label: runs on one baseline have no meaning there (#1192).
            raise LayoutError("E_LAYOUT_GROUP_HEADER_RUNS_VERTICAL", "/body/grouping/header",
                              detail="a role-marked header template needs a horizontal groupHeader role")
        # A vertical label spans the group's rows in the column carved from the table's start (#585).
        text, tag_warnings = [], []
        tab = resolve_group_tab(request.theme_tokens)
        align = request.theme_tokens.optional_choice("groupHeader", "align", ("start", "center", "end")) or "start"
        for group in groups:
            if group.group_id and group.group_id in labels:
                cell = (group_tag_bounds(tab, tag_column, group.content_bounds)
                        if tab is not None and tab.target == "tag" else
                        Rect(Decimal(str(tag_column[0])), group.content_bounds.block,
                             Decimal(str(tag_column[1])), group.content_bounds.block_size))
                fitted = place_vertical_label_fit(
                    label=labels[group.group_id], placement_prefix=f"group-tag:{group.group_id}",
                    source_ref=group.group_id, column_inline=float(cell.inline), column_size=float(cell.inline_size),
                    block_start=float(cell.block),
                    available_block=float(cell.block_size), typography_role="groupHeader",
                    theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                    collision_region=f"group:{group.group_id}",
                    collision_domain=CollisionDomain("group-header", group.group_id), semantic_id="groupHeader",
                    align=align)
                text.extend(fitted.placements)
                # A tag cut or overrunning its group's rows is reported, never silently shortened (#981).
                shown = fitted.placements[0].overflow if fitted.placements else "fit"
                if shown in {"ellipsized", "visible-overflow"}:
                    ellipsized = shown == "ellipsized"
                    tag_warnings.append(FitWarning(
                        "W_LAYOUT_TEXT_ELLIPSIZED" if ellipsized else "W_LAYOUT_VISIBLE_OVERFLOW",
                        fitted.placements[0].placement_id, group.group_id, "group-tag-text",
                        "ellipsize-with-source" if ellipsized else "visible-overflow",
                        float(cell.inline_size), fitted.required_block, float(cell.inline_size),
                        fitted.available_block))
        return SurfaceGroupPresentation(tuple(text), tuple(tag_warnings))
    if request.theme_tokens.optional_choice("groupHeader", "align", ("start", "center", "end")) is not None:
        # `align` places a vertical tag in its rows; on a horizontal header it would be silently ignored (#981).
        raise LayoutError("E_THEME_ROLE_PROPERTY_UNSUPPORTED", "/body/roles/groupHeader/align",
                          detail="align on groupHeader needs a vertical writingMode")
    group_header_font_size = (float(request.theme_tokens.text_treatment("groupHeader").font_size)
                              if any(group.header_bounds is not None for group in groups) else body_size)
    label_inset_ratio = (request.theme_tokens.optional_number("groupHeader", "labelInset")
                         if any(group.header_bounds is not None for group in groups) else None)
    if label_inset_ratio is not None and label_inset_ratio < 0:
        raise ThemeTokenError("E_THEME_TOKEN_TYPE", "/body/roles/groupHeader/labelInset",
                              f"labelInset={label_inset_ratio}; expected a finite nonnegative ratio")
    label_inset = (label_inset_ratio * Decimal(str(group_header_font_size))
                   if label_inset_ratio is not None else Decimal(0))
    text, warnings, content_bounds = [], [], []
    tab = resolve_group_tab(request.theme_tokens) if any(group.header_bounds is not None for group in groups) else None
    for group in groups:
        if group.header_bounds is not None:
            start, size = group.header_bounds.inline, group.header_bounds.inline_size
            if label_inset_ratio is not None:
                start += label_inset
                size = max(Decimal(0), size - label_inset)
            if tab is not None:
                # The text never lies on the tab (#882): it starts after a start tab and gives an end tab its room.
                check_group_tab_inline(tab, group.header_bounds)
                if label_inset_ratio is None:
                    size -= tab.reserved
                    start += tab.reserved if tab.position == "start" else Decimal(0)
                elif tab.position == "start":
                    if label_inset < tab.reserved:
                        raise LayoutError(
                            "E_LAYOUT_GROUP_TAB_SIZE", "/body/roles/groupHeader/labelInset",
                            detail=f"actual offset={label_inset}; required reservation={tab.reserved}")
                else:
                    if label_inset + tab.reserved > group.header_bounds.inline_size:
                        raise LayoutError(
                            "E_LAYOUT_GROUP_TAB_SIZE", "/body/roles/groupHeader/labelInset",
                            detail=(f"actual offset={label_inset}; required reservation={tab.reserved}; "
                                    f"available={group.header_bounds.inline_size}"))
                    size = max(Decimal(0), size - tab.reserved)
            if group.group_id in marked:
                # Role-marked runs share the header's baseline, each measured with its own role (#1192).
                placed, run_warnings = place_group_header_runs(
                    group_id=group.group_id, runs=marked[group.group_id], start=start, size=size, bounded=tab is not None,
                    baseline_block=float(group.header_bounds.block) + group_header_font_size,
                    header_block_size=float(group.header_bounds.block_size), theme_tokens=request.theme_tokens,
                    font_metrics=request.font_metrics)
                text.extend(placed)
                warnings.extend(run_warnings)
                content_bounds.append((group.group_id, _header_content_extent(group, start, placed)))
                continue
            content, disposition = labels[group.group_id], "fit"
            if tab is not None:
                # A header without a tab keeps today's unbounded text. Beside a tab the text is bounded by the room the
                # tab leaves and is shortened with its source kept, never silently (#882, as the legend of #497).
                treatment = request.theme_tokens.text_treatment("groupHeader")
                metrics = metric_for_role(request.theme_tokens, "groupHeader", request.font_metrics)
                shape = dict(font_size=float(treatment.font_size), font_metrics=metrics,
                             letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
                             numeric_spacing=treatment.numeric_spacing)
                natural = measure_text_width(content, **shape)
                if natural > float(size):
                    content, disposition = ellipsize_text(content, available_inline=float(size), **shape), "ellipsized"
                    warnings.append(FitWarning(
                        "W_LAYOUT_TEXT_ELLIPSIZED", f"group-header:{group.group_id}", group.group_id,
                        "group-header-text", "ellipsize-with-source", natural, float(group.header_bounds.block_size),
                        float(size), float(group.header_bounds.block_size)))
            placed = place_text(
                placement_id=f"group-header:{group.group_id}", source_ref=group.group_id,
                content=content, overflow=disposition, inline=float(start),
                baseline_block=float(group.header_bounds.block) + group_header_font_size,
                typography_role="groupHeader", theme_tokens=request.theme_tokens,
                font_metrics=request.font_metrics, collision_region=f"group:{group.group_id}",
                collision_domain=CollisionDomain("group-header", group.group_id),
                source_content=labels[group.group_id], semantic_id="groupHeader",
                available_inline_start=float(start),
                available_inline_size=float(size))
            text.append(placed)
            content_bounds.append((group.group_id, _header_content_extent(group, start, [placed])))
    return SurfaceGroupPresentation(tuple(text), tuple(warnings), tuple(content_bounds))


def replace_group_header_extent(groups: tuple[GroupPlacement, ...],
                                update: GroupHeaderExtentUpdate) -> tuple[GroupPlacement, ...]:
    """Return a group tuple with one folded-point header extent replaced."""
    index = groups.index(update.source)
    return groups[:index] + (replace(update.source, header_bounds=update.header_bounds),) + groups[index + 1:]
