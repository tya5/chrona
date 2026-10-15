"""Style selection of optional Actual variance fill traits."""
from datetime import date

from chrona.presentation.model.actual_variance_paint import (
    resolve_actual_variance_colors,
    select_actual_variance_paints,
)
from chrona.presentation.model.projection import (
    FoldedPointProjection, ReviewItem, ReviewProjection, ReviewRowProjection,
)
from chrona.presentation.model.theme_tokens import ThemeTokenView


def _theme(roles=None):
    return {
        "version": "chrona/resolved-theme/v0.2",
        "kind": "resolved-theme",
        "body": {
            "values": {"ahead": {"type": "color", "value": "#2266AA"},
                       "track": {"type": "color", "value": "#228844"},
                       "behind": {"type": "color", "value": "#CC3344"}},
            "roles": roles if roles is not None else {
                "actual-ahead": {"fill": "ahead"},
                "actual-on-track": {"fill": "track"},
                "actual-behind": {"fill": "behind"},
            },
            "metrics": {},
        },
    }


def _item(object_id, roles, *, actual=None, source_kind="primary"):
    return ReviewItem(
        object_id, object_id, "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 10)},
        actual, None, roles, item_id=object_id, source_kind=source_kind,
    )


def _point_item(object_id, roles, *, actual=None, source_kind="primary"):
    return ReviewItem(
        object_id, object_id, "point", {"at": date(2026, 1, 10)}, actual, None, roles,
        item_id=object_id, source_kind=source_kind,
    )


def test_theme_traits_resolve_only_optional_variance_fills():
    tokens = ThemeTokenView(_theme())

    assert resolve_actual_variance_colors(tokens) == {
        "variance-ahead": "#2266AA",
        "variance-on-track": "#228844",
        "variance-behind": "#CC3344",
    }
    assert resolve_actual_variance_colors(ThemeTokenView(_theme(roles={}))) == {}


def test_actual_variance_selection_is_fact_role_based_and_covers_folded_items():
    ahead = _item("ahead", ("planned", "actual", "variance-ahead"),
                  actual={"finish": date(2026, 1, 8)})
    behind = _item("behind", ("planned", "actual", "variance-behind"),
                   actual={"finish": date(2026, 1, 12)})
    on_track = _item("track", ("planned", "actual", "variance-on-track"),
                     actual={"finish": date(2026, 1, 10)}, source_kind="actual")
    folded_point = _point_item("folded-point", ("planned", "actual"),
                               actual={"at": date(2026, 1, 11)})
    missing = _item("missing", ("planned", "missing-actual"))
    snapshot = _item("snapshot", ("planned",), source_kind="snapshot")
    scenario = _item("scenario", ("planned",), source_kind="scenario")
    projection = ReviewProjection(
        items=(ahead, behind, missing, snapshot, scenario),
        window=(date(2026, 1, 1), date(2026, 1, 20)),
        unmatched_actual_ids=(), diagnostics=(),
        rows=(ReviewRowProjection("row-track", "Track", "", "track", (on_track,)),),
        folded_points=(FoldedPointProjection(folded_point, "g"),),
    )

    assert select_actual_variance_paints(projection, {
        "variance-ahead": "#2266AA",
        "variance-on-track": "#228844",
        "variance-behind": "#CC3344",
    }) == (("ahead", "#2266AA"), ("behind", "#CC3344"), ("track", "#228844"))


def test_unbound_class_and_unclassified_actual_leave_no_override():
    projection = ReviewProjection(
        items=(
            _item("ahead", ("planned", "actual", "variance-ahead"),
                  actual={"finish": date(2026, 1, 8)}),
            _item("unclassified", ("planned", "actual"), actual={"at": date(2026, 1, 8)}),
        ),
        window=(date(2026, 1, 1), date(2026, 1, 20)),
        unmatched_actual_ids=(), diagnostics=(),
    )

    assert select_actual_variance_paints(projection, {}) == ()
    assert select_actual_variance_paints(projection, {"variance-behind": "#CC3344"}) == ()
