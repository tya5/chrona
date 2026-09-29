"""Owns group-header presentation from completed base extents; reads fixed rows, groups, Theme text metrics."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_quality import CollisionDomain, GroupPlacement, TextPlacement
from chrona.presentation.layout.text import place_text


@dataclass(frozen=True)
class SurfaceGroupPresentation:
    """Ordered group-header text derived from immutable base group extents."""
    text: tuple[TextPlacement, ...]


@dataclass(frozen=True)
class GroupHeaderExtentUpdate:
    """Typed folded-mark request to replace one completed header extent."""
    source: GroupPlacement
    header_bounds: Rect


def compose_group_presentation(*, request: Any, rows: tuple[Any, ...],
                               review_rows: tuple[Any, ...], groups: tuple[GroupPlacement, ...],
                               body_size: float) -> SurfaceGroupPresentation:
    """Place declared group labels inside completed group-header bounds."""
    labels = {row.group_id: next((item.group_label for item in review_row.items if item.group_label), row.group_id)
              for review_row, row in zip(review_rows, rows, strict=True) if row.group_id}
    group_header_font_size = (float(request.theme_tokens.text_treatment("groupHeader").font_size)
                              if any(group.header_bounds is not None for group in groups) else body_size)
    text = []
    for group in groups:
        if group.header_bounds is not None:
            text.append(place_text(
                placement_id=f"group-header:{group.group_id}", source_ref=group.group_id,
                content=labels[group.group_id], inline=float(group.header_bounds.inline),
                baseline_block=float(group.header_bounds.block) + group_header_font_size,
                typography_role="groupHeader", theme_tokens=request.theme_tokens,
                font_metrics=request.font_metrics, collision_region=f"group:{group.group_id}",
                collision_domain=CollisionDomain("group-header", group.group_id),
                source_content=labels[group.group_id], semantic_id="groupHeader",
                available_inline_start=float(group.header_bounds.inline),
                available_inline_size=float(group.header_bounds.inline_size)))
    return SurfaceGroupPresentation(tuple(text))


def replace_group_header_extent(groups: tuple[GroupPlacement, ...],
                                update: GroupHeaderExtentUpdate) -> tuple[GroupPlacement, ...]:
    """Return a group tuple with one folded-point header extent replaced."""
    index = groups.index(update.source)
    return groups[:index] + (replace(update.source, header_bounds=update.header_bounds),) + groups[index + 1:]
