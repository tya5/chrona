from decimal import Decimal as D

import pytest

from chrona.presentation.layout.canvas_viewport import (
    DeclaredViewport,
    canvas_viewport_warning,
)
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_geometry import GEOMETRY_TOLERANCE


def rect(x=0, y=0, width=1, height=1):
    return Rect(D(str(x)), D(str(y)), D(str(width)), D(str(height)))


def test_overflow_reports_native_slot_union_and_preserves_actual_rect():
    actual = rect(-2, 0, 112, 80)
    warning = canvas_viewport_warning(
        surface_id="timeline",
        declared=DeclaredViewport(D(100), D(80)),
        actual=actual,
        contributors=(
            ("title", rect(-2, 0, 5, 4)),
            ("title", rect(97, 2, 13, 5)),
            ("body", rect(10, 10, 80, 60)),
        ),
    )

    assert warning is not None
    assert warning.code == "W_LAYOUT_CANVAS_EXCEEDS_VIEWPORT"
    assert warning.source_ref == "/body/environment/viewport"
    assert warning.surface_id == "timeline"
    assert warning.declared == DeclaredViewport(D(100), D(80))
    assert warning.actual is actual
    assert warning.contributor_count == 1
    title = warning.contributors[0]
    assert title.slot_id == "title"
    assert title.bounds == rect(-2, 0, 112, 7)
    assert title.overrun.inline_start == D(2)
    assert title.overrun.inline_end == D(10)
    assert title.overrun.block_start == title.overrun.block_end == D(0)


def test_fitting_canvas_returns_none_and_checks_all_four_edges():
    declared = DeclaredViewport(D(100), D(80))
    assert canvas_viewport_warning(
        surface_id="fit", declared=declared, actual=rect(0, 0, 100, 80), contributors=()
    ) is None
    assert canvas_viewport_warning(
        surface_id="fit", declared=declared, actual=rect(0, 0, 100 + float(GEOMETRY_TOLERANCE), 80), contributors=()
    ) is None
    warning = canvas_viewport_warning(
        surface_id="overflow",
        declared=declared,
        actual=rect(0, -3, 100, 84),
        contributors=(("frame", rect(0, -3, 100, 84)),),
    )
    assert warning is not None
    assert warning.contributors[0].overrun.block_start == D(3)
    assert warning.contributors[0].overrun.block_end == D(1)


def test_auto_block_does_not_constrain_either_block_edge_but_inline_still_does():
    declared = DeclaredViewport(D(100), None)
    assert canvas_viewport_warning(
        surface_id="auto", declared=declared, actual=rect(0, -10, 100, 1000),
        contributors=(("body", rect(0, -10, 100, 1000)),),
    ) is None
    warning = canvas_viewport_warning(
        surface_id="auto", declared=declared, actual=rect(-2, -10, 102, 1000),
        contributors=(("body", rect(-2, -10, 102, 1000)),),
    )
    assert warning is not None
    assert warning.contributors[0].overrun == warning.contributors[0].overrun.__class__(inline_start=D(2))


def test_no_declaration_means_no_comparison():
    assert canvas_viewport_warning(
        surface_id="auto", declared=None, actual=rect(-500, -500, 1000, 1000), contributors=()
    ) is None


def test_tolerance_applies_to_start_and_end_edges():
    declared = DeclaredViewport(D(100), D(80))
    tol = GEOMETRY_TOLERANCE
    assert canvas_viewport_warning(
        surface_id="near", declared=declared,
        actual=Rect(-tol, -tol, D(100) + tol * 2, D(80) + tol * 2), contributors=(),
    ) is None
    assert canvas_viewport_warning(
        surface_id="over", declared=declared,
        actual=Rect(-tol * 2, D(0), D(100), D(80)), contributors=(),
    ) is not None


def test_contributors_are_unioned_sorted_deterministically_and_limited_to_five():
    declared = DeclaredViewport(D(100), D(100))
    entries = [(f"slot-{index:02}", rect(100, 0, 1 + (index % 3), 1)) for index in range(8)]
    entries.extend((("slot-01", rect(0, 101, 1, 1)), ("slot-01", rect(0, 102, 1, 1))))
    actual = rect(0, 0, 110, 110)
    first = canvas_viewport_warning(surface_id="s", declared=declared, actual=actual, contributors=entries)
    second = canvas_viewport_warning(surface_id="s", declared=declared, actual=actual, contributors=reversed(entries))
    assert first == second
    assert first is not None
    assert first.contributor_count == 8
    assert len(first.contributors) == 5
    assert [item.slot_id for item in first.contributors] == ["slot-01", "slot-02", "slot-05", "slot-04", "slot-07"]
    assert first.contributors[0].bounds == rect(0, 0, 102, 103)


@pytest.mark.parametrize("inline,block", [(D(0), D(10)), (D(-1), D(10)), (D("NaN"), D(10)), (D(10), D("Infinity"))])
def test_declared_viewport_requires_positive_finite_decimal_sizes(inline, block):
    with pytest.raises(ValueError, match="E_LAYOUT_VIEWPORT_DECLARATION_INVALID"):
        DeclaredViewport(inline, block)


@pytest.mark.parametrize("invalid", [D(-1), D("NaN"), 1, True])
def test_declared_block_size_is_null_or_positive_finite_decimal(invalid):
    with pytest.raises(ValueError, match="E_LAYOUT_VIEWPORT_DECLARATION_INVALID"):
        DeclaredViewport(D(10), invalid)


def test_malformed_contributor_facts_are_rejected():
    with pytest.raises(ValueError, match=r"contributors\[0\]"):
        canvas_viewport_warning(
            surface_id="s", declared=DeclaredViewport(D(1), None), actual=rect(0, 0, 2, 1),
            contributors=(("slot", (0, 0, 2, 1)),),
        )
