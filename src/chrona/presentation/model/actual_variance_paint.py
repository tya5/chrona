"""Style-owned Actual fill selection from finite, fact-derived variance roles."""
from __future__ import annotations

from collections.abc import Mapping

from chrona.presentation.model.projection import ReviewItem, ReviewProjection
from chrona.presentation.model.theme_tokens import ThemeTokenView


# Optional Theme trait roles provide fill colors only; they do not replace the
# semantic `actual` paint role or any of its geometry properties.
ACTUAL_VARIANCE_TRAIT_ROLES = (
    ("variance-ahead", "actual-ahead"),
    ("variance-on-track", "actual-on-track"),
    ("variance-behind", "actual-behind"),
)


def resolve_actual_variance_colors(tokens: ThemeTokenView) -> dict[str, str]:
    """Resolve declared class fills without falling back to another role."""
    return {
        variance_role: color
        for variance_role, trait_role in ACTUAL_VARIANCE_TRAIT_ROLES
        if (color := tokens.optional_color(trait_role, "fill")) is not None
    }


def select_actual_variance_paints(projection: ReviewProjection,
                                  colors: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
    """Select explicit Theme fills for recorded Actual source objects only."""
    if not colors:
        return ()
    items: list[ReviewItem] = list(projection.items)
    items.extend(item for row in projection.rows for item in row.items)
    items.extend(item for folded in projection.folded_points for item in folded.all_items)
    selected: dict[str, str] = {}
    for item in items:
        if item.actual is None or "actual" not in item.roles:
            continue
        variance_role = next((role for role, _ in ACTUAL_VARIANCE_TRAIT_ROLES if role in item.roles), None)
        color = colors.get(variance_role) if variance_role is not None else None
        if color is not None:
            selected.setdefault(item.object_id, color)
    return tuple(sorted(selected.items()))
