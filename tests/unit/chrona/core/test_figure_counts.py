"""View figure counts consume caller-injected neutral facts (#927)."""
from dataclasses import FrozenInstanceError

import pytest

from chrona.core.figures import COUNT_SOURCES, FigureCounts, FigureSpec, resolve_figures


COUNTS = FigureCounts(
    selected=11,
    recorded=12,
    due_unobserved=13,
    not_yet_due=14,
    unavailable=15,
    missing_actual=16,
    known_finish_variance=17,
    behind=18,
    ahead=19,
)


@pytest.mark.parametrize(("source", "expected"), list(zip(COUNT_SOURCES, range(11, 20), strict=True)))
def test_each_closed_count_source_resolves_its_injected_value(source, expected):
    result = resolve_figures(
        (FigureSpec("count", "count", source=source, path="/body/figures/0"),),
        as_of=None,
        placements={},
        periods=(),
        calendars={},
        default_calendar=None,
        counts=COUNTS,
    )

    assert dict(result.values) == {"count": expected}
    assert result.diagnostics == ()


def test_zero_is_a_resolved_count_not_absence():
    zero = FigureCounts(0, 0, 0, 0, 0, 0, 0, 0, 0)
    result = resolve_figures(
        (FigureSpec("selected", "count", source="selected", path="/body/figures/0"),),
        as_of=None,
        placements={},
        periods=(),
        calendars={},
        default_calendar=None,
        counts=zero,
    )

    assert dict(result.values) == {"selected": 0}
    assert result.diagnostics == ()


@pytest.mark.parametrize("counts", [None, FigureCounts(0, 0, 0, 0, 0, None, 0, 0, 0)])
def test_unavailable_count_and_missing_actual_without_as_of_are_diagnostics(counts):
    result = resolve_figures(
        (FigureSpec("missing", "count", source="missingActual", path="/body/figures/2"),),
        as_of=None,
        placements={},
        periods=(),
        calendars={},
        default_calendar=None,
        counts=counts,
    )

    assert dict(result.values) == {}
    assert [(item.id, item.path) for item in result.diagnostics] == [
        ("E_FIGURE_COUNT_UNAVAILABLE", "/body/figures/2/source")
    ]
    assert result.diagnostics[0].details == {"figure": "missing", "source": "missingActual"}


def test_count_resolution_uses_injected_facts_without_a_projection_argument():
    """Core receives only the count bundle; selection/projection remains caller-owned."""
    result = resolve_figures(
        (FigureSpec("selected", "count", source="selected"),),
        as_of=None,
        placements={},
        periods=(),
        calendars={},
        default_calendar=None,
        counts=COUNTS,
    )

    assert result.values == {"selected": 11}
    assert "projection" not in FigureCounts.__dataclass_fields__


def test_count_bundle_is_immutable():
    with pytest.raises(FrozenInstanceError):
        COUNTS.selected = 0


def test_unknown_count_source_is_rejected():
    with pytest.raises(TypeError, match="unknown count source"):
        resolve_figures(
            (FigureSpec("bad", "count", source="allObjects", path="/body/figures/0"),),
            as_of=None,
            placements={},
            periods=(),
            calendars={},
            default_calendar=None,
            counts=COUNTS,
        )


def test_unknown_figure_kind_is_rejected():
    with pytest.raises(TypeError, match="unknown kind"):
        resolve_figures(
            (FigureSpec("bad", "expression", path="/body/figures/0"),),
            as_of=None,
            placements={},
            periods=(),
            calendars={},
            default_calendar=None,
            counts=COUNTS,
        )
