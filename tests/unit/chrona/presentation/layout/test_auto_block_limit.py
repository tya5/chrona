"""Declared auto-block advice never becomes a geometry constraint."""
from decimal import Decimal

import pytest

from chrona.presentation.layout.canvas_viewport import DeclaredViewport, auto_block_size_warning
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.profile import resolve_layout_profile
from tests.support import synthetic_review as sr


@pytest.mark.parametrize("limit,block,warns", [(None, None, False), (900, None, False),
                                               (1000, None, False), (899, None, True),
                                               (0, None, True), (0, 900, False)])
def test_completed_extent_strict_boundary_omission_zero_and_finite(limit, block, warns):
    result = auto_block_size_warning(surface_id="s", row_count=12, actual=Rect(*(Decimal(n) for n in (0, 0, 1600, 900))),
                                    declared=DeclaredViewport(Decimal(1600), Decimal(block) if block else None),
                                    limit=Decimal(limit) if limit is not None else None)
    assert (result is not None) == warns
    if result:
        assert result.row_count == 12
        assert result.actual_block_size == 900
        assert result.limit == limit


def _resolve(parts):
    return resolve_layout_profile(parts["layout"], available_sources={"title", "table", "timeline", "timeline-axis"},
                                  theme=parts["theme"])


@pytest.mark.parametrize("value", [0, 3600])
def test_literal_limit_is_admitted_and_resolved(value):
    parts = sr.bundle()
    parts["layout"]["reviewSurface"]["maxBlockSize"] = value
    assert _resolve(parts).distances["/reviewSurface/maxBlockSize"] == value


def test_limit_token_uses_existing_required_token_resolution():
    parts = sr.bundle()
    parts["layout"]["reviewSurface"]["maxBlockSize"] = {"token": "canvas.limit"}
    with pytest.raises(LayoutError) as caught:
        _resolve(parts)
    assert caught.value.diagnostic_id == "E_LAYOUT_TOKEN_REQUIREMENT_MISSING"
    parts["layout"]["requiredThemeTokens"] = sorted([*parts["layout"]["requiredThemeTokens"], "canvas.limit"])
    with pytest.raises(LayoutError) as caught:
        _resolve(parts)
    assert caught.value.diagnostic_id == "E_LAYOUT_TOKEN_REQUIREMENT_UNAVAILABLE"
    parts["theme"]["body"]["values"]["canvas.limit"] = {"type": "number", "value": 2000}
    assert _resolve(parts).distances["/reviewSurface/maxBlockSize"] == 2000
    parts["theme"]["body"]["values"]["canvas.limit"]["value"] = -1
    with pytest.raises(LayoutError) as caught:
        _resolve(parts)
    assert caught.value.diagnostic_id == "E_LAYOUT_TOKEN_REQUIREMENT_TYPE"


@pytest.mark.parametrize("value", [-1, True, "auto", {"token": "bad token"}])
def test_invalid_limit_is_rejected_by_live_profile(value):
    parts = sr.bundle()
    parts["layout"]["reviewSurface"]["maxBlockSize"] = value
    with pytest.raises(LayoutError) as caught:
        _resolve(parts)
    assert caught.value.diagnostic_id == "E_LAYOUT_SCHEMA"
