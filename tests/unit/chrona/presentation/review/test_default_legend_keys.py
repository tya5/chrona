"""Bounded source candidates for the default comparison keys (#1703)."""
from datetime import date
from types import SimpleNamespace

from chrona.presentation.contracts.resources import LegendEntry, ReviewDetailInput
from chrona.presentation.model.projection import ReviewItem, ReviewProjection, ReviewRowProjection
from chrona.presentation.model.surface_content import SurfaceLegendEntry
from chrona.presentation.review.style_occurrences import surface_comparison_mark_semantics
from chrona.presentation.review.v05_content import _default_legend_entries


def test_defaults_follow_authored_entries_before_scale_keys_and_accept_wording():
    entries = (SurfaceLegendEntry("actual", "Observed"),
               SurfaceLegendEntry("scale:owner:a", "Team A"))
    assert _default_legend_entries(entries, None,
        potential_roles=frozenset({"snapshot", "deadlineMark"}),
        wording={"snapshot": "Reference"}) == (
            entries[0], SurfaceLegendEntry("snapshot", "Reference"),
            SurfaceLegendEntry("deadlineMark", "Deadline"), entries[1])


def test_explicit_entry_retains_its_order_label_and_shape_without_duplication():
    explicit = SurfaceLegendEntry("snapshot", "Saved plan", swatch_shape="circle")
    entries = (explicit, SurfaceLegendEntry("actual", "Actual"))
    detail = ReviewDetailInput((), (), (LegendEntry("snapshot", "Saved plan"),), None)
    result = _default_legend_entries(entries, detail,
        potential_roles=frozenset({"snapshot", "deadlineMark"}), wording={})
    assert result == (*entries, SurfaceLegendEntry("deadlineMark", "Deadline"))


def test_absent_meanings_and_explicit_opt_out_add_no_default_candidates():
    assert _default_legend_entries((), None, potential_roles=frozenset(), wording={}) == ()
    detail = ReviewDetailInput((), (), (), None,
                              unkeyed_legend_roles=("snapshot", "deadlineMark"))
    assert _default_legend_entries((), detail,
        potential_roles=frozenset({"snapshot", "deadlineMark"}), wording={}) == ()


def test_snapshot_potential_comes_from_selected_occurrences_not_bound_source_alone():
    day = date(2027, 3, 1)
    item = ReviewItem("task", "Task", "span", {"start": day, "end": date(2027, 3, 4)},
                      None, None, (), item_id="saved", source_kind="snapshot")
    row = ReviewRowProjection("r", "Task", "", "saved", (item,))
    projection = ReviewProjection((), (day, date(2027, 4, 1)), (), (), (row,), rows_resolved=True)
    assert "snapshot" in surface_comparison_mark_semantics(projection, SimpleNamespace(as_of=None))
    empty = ReviewProjection((), projection.window, (), (), rows_resolved=True,
                             bound_comparison_sources=frozenset({"snapshot"}))
    assert "snapshot" not in surface_comparison_mark_semantics(empty, SimpleNamespace(as_of=None))
