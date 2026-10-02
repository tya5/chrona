"""Owns group-header presentation from completed base extents; reads fixed rows, groups, Theme text metrics."""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.surface_quality import CollisionDomain, FitWarning, GroupPlacement, TextPlacement
from chrona.presentation.layout.text import ellipsize_text, measure_text_width, metric_for_role, place_text


@dataclass(frozen=True)
class SurfaceGroupPresentation:
    """Ordered group-header text derived from immutable base group extents."""
    text: tuple[TextPlacement, ...]
    warnings: tuple[FitWarning, ...] = ()


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

    @property
    def reserved(self) -> Decimal:
        """Inline extent of the header the tab and its gap take from the text."""
        return self.inline_size + self.gap


_TAB_ROLE = "group-tab"


def _tab_error(prop: str, value: Any, available: Any = None) -> LayoutError:
    detail = f"{_TAB_ROLE}:{prop}:{value}" + (f":{available}" if available is not None else "")
    return LayoutError("E_LAYOUT_GROUP_TAB_SIZE", f"/body/roles/{_TAB_ROLE}/{prop}", detail=detail)


def resolve_group_tab(theme_tokens: Any) -> GroupTabSpec | None:
    """Return the declared group tab, or None when the Theme declares no `group-tab` role or draws none."""
    # A role that declares neither a treatment nor a paint order declares no tab (every Theme without the role
    # draws today's header); one declaring only half of the pair is the Theme token error of every background.
    declared = theme_tokens.optional_background(_TAB_ROLE)
    if declared is None or declared[0] == "none":
        return None
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


def compose_group_presentation(*, request: Any, rows: tuple[Any, ...],
                               review_rows: tuple[Any, ...], groups: tuple[GroupPlacement, ...],
                               body_size: float) -> SurfaceGroupPresentation:
    """Place declared group labels inside completed group-header bounds."""
    labels = {row.group_id: next((item.group_label for item in review_row.items if item.group_label), row.group_id)
              for review_row, row in zip(review_rows, rows, strict=True) if row.group_id}
    # A View-declared header template replaces the title text only (#583).
    labels.update(dict(request.surface_content.group_headers))
    group_header_font_size = (float(request.theme_tokens.text_treatment("groupHeader").font_size)
                              if any(group.header_bounds is not None for group in groups) else body_size)
    text, warnings = [], []
    tab = resolve_group_tab(request.theme_tokens) if any(group.header_bounds is not None for group in groups) else None
    for group in groups:
        if group.header_bounds is not None:
            start, size = group.header_bounds.inline, group.header_bounds.inline_size
            if tab is not None:
                # The text never lies on the tab (#882): it starts after a start tab and gives an end tab its room.
                check_group_tab_inline(tab, group.header_bounds)
                size -= tab.reserved
                start += tab.reserved if tab.position == "start" else Decimal(0)
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
            text.append(place_text(
                placement_id=f"group-header:{group.group_id}", source_ref=group.group_id,
                content=content, overflow=disposition, inline=float(start),
                baseline_block=float(group.header_bounds.block) + group_header_font_size,
                typography_role="groupHeader", theme_tokens=request.theme_tokens,
                font_metrics=request.font_metrics, collision_region=f"group:{group.group_id}",
                collision_domain=CollisionDomain("group-header", group.group_id),
                source_content=labels[group.group_id], semantic_id="groupHeader",
                available_inline_start=float(start),
                available_inline_size=float(size)))
    return SurfaceGroupPresentation(tuple(text), tuple(warnings))


def replace_group_header_extent(groups: tuple[GroupPlacement, ...],
                                update: GroupHeaderExtentUpdate) -> tuple[GroupPlacement, ...]:
    """Return a group tuple with one folded-point header extent replaced."""
    index = groups.index(update.source)
    return groups[:index] + (replace(update.source, header_bounds=update.header_bounds),) + groups[index + 1:]
