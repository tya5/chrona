"""A baseline ghost is a comparison mark, never a relation endpoint (#1031).

Synthetic fixtures only: two related items, each with a snapshot ghost, composed by the real projection in every
row mode and routed by the real surface composer. Each relation must yield exactly one path between primary marks.
"""
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from chrona.presentation.contracts.resources import (
    ViewComparison, ViewGrouping, ViewInput, ViewRow, ViewRowItem, ViewRows, ViewVisibility, ViewWindow,
)
from chrona.presentation.layout.sources import MeasuredSources, SourceInput
from chrona.presentation.layout.surface_lanes import preflight_fixed_lane_layout
from chrona.presentation.model.projection import build_review_projection
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.v05_builder import build_scene_input, compose_review_surface

from tests.unit.chrona.presentation.scene.test_v05_builder import (
    _Font, _manifest, _theme, _title_measurement, surface_content,
)

PROJECT = {
    "objects": {"a": {"title": "A", "fields": {"owner": "x"}}, "b": {"title": "B", "fields": {"owner": "x"}}},
    "entities": {},
    "relations": [{"id": "dep", "type": "dependency", "from": {"object": "a", "endpoint": "end"},
                   "to": {"object": "b", "endpoint": "start"}}],
}
PLACED = {"a": {"start": date(2026, 2, 1), "end": date(2026, 2, 8)}, "b": {"start": date(2026, 2, 12), "end": date(2026, 2, 20)}}
SNAPSHOT = {"a": {"start": date(2026, 1, 20), "end": date(2026, 1, 27)}, "b": {"start": date(2026, 2, 1), "end": date(2026, 2, 9)}}


def _view(mode: str, *, grouped: bool = False, rows: tuple[ViewRow, ...] = ()) -> ViewInput:
    grouping = ViewGrouping("field", "owner", ("x",), "ungrouped", "header", None, None) if grouped else None
    return ViewInput(None, grouping, None, ViewWindow("selected-planned", None, None, 0),
        ViewComparison("snapshot", "optional", None, None, (), baseline_marks=None if mode == "explicit" else "ghost"),
        ViewVisibility(False, "none", "none"), (), (),
        ViewRows(mode, rows, packing=("dates",) if mode == "lanes" else ()), None, (), None, None, None)


def _explicit_rows() -> tuple[ViewRow, ...]:
    return tuple(ViewRow(oid, oid.upper(), 0, None, None, None, (
        ViewRowItem(oid, "primary", oid, "shared"), ViewRowItem(f"snapshot:{oid}", "snapshot", oid, "shared")))
        for oid in ("a", "b"))


MODES = {
    "automatic": _view("automatic"),
    "grouped": _view("automatic", grouped=True),
    "lanes": _view("lanes", grouped=True),
    "explicit": _view("explicit", rows=_explicit_rows()),
}


def _relation_paths(view: ViewInput, ghost_kind: str = "snapshot"):
    projection = build_review_projection(PROJECT, PLACED, view, None, snapshot_project=PROJECT, snapshot_placements=SNAPSHOT,
                                         scenarios={"what-if": (PROJECT, SNAPSHOT)})
    assert any(item.source_kind == ghost_kind for row in projection.rows for item in row.items), "the fixture must carry ghosts"
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8),
                                   "timeline.mark.blockSize": Decimal(8)})
    content = surface_content(relations=PROJECT["relations"])
    manifest, theme = _manifest("title", "table", "timeline", "timeline-axis"), _theme()
    preflight = (preflight_fixed_lane_layout(projection=projection, layout_manifest=manifest, surface_content=content,
        theme_tokens=ThemeTokenView(theme), metric_values=measurement.metric_values, icon_assets={}, visual_requests=(),
        font_metrics=_Font()) if projection.lane_membership is not None else None)
    value = build_scene_input(projection=projection, surface_content=content, layout_manifest=manifest,
        resolved_theme=theme, font_metrics=_Font(), measured_sources=measurement, capabilities={"svg": True},
        fixed_lane_preflight=preflight)
    surface = compose_review_surface(value)
    return [item for item in surface.primitives
            if item.scene_id.startswith("relation:") and not item.scene_id.startswith("relation-label")]


@pytest.mark.parametrize("mode", sorted(MODES))
def test_each_relation_is_one_path_between_primary_marks_whatever_the_row_mode(mode):
    paths = _relation_paths(MODES[mode])
    assert len(paths) == 1, [item.scene_id for item in paths]
    assert "snapshot" not in paths[0].scene_id


def test_a_scenario_ghost_is_not_a_relation_endpoint_either():
    view = replace(MODES["grouped"], comparison=ViewComparison("scenario", "optional", None, None, (), scenario_id="what-if"))
    paths = _relation_paths(view, "scenario")
    assert len(paths) == 1
    assert "scenario" not in paths[0].scene_id


def test_an_object_with_only_comparison_instances_keeps_its_relation():
    rows = tuple(ViewRow(oid, oid.upper(), 0, None, None, None, (ViewRowItem(f"snapshot:{oid}", "snapshot", oid, "shared"),))
                 for oid in ("a", "b"))
    paths = _relation_paths(_view("explicit", rows=rows))
    assert len(paths) == 1
