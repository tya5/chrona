"""The deadline mark: View selection, Layout tick and run, Scene primitive and the gates that cover it (#822, I822-3).

Each rule is proven on a synthetic Project rendered through a packaged preset bundle, so a corpus edit cannot change
what these tests prove. The Core decides which deadlines slipped (`deadline_statuses`); Layout only draws the verdict.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from chrona.core.deadlines import deadline_warnings
from chrona.presentation.layout.surface_deadlines import compose_deadline_marks
from chrona.presentation.layout.surface_quality import MarkPlacement
from chrona.presentation.layout.model import Rect
from chrona.presentation.model.closure import ClosureError
from chrona.presentation.model.projection import ReviewDeadline
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility
from chrona.presentation.scene.serialization import scene_document, validate_scene_document
from chrona.resources import builtin_preset_source_root, safe_load, schema_validator
from chrona.scheduling.scheduler import schedule
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr

WINDOW = {"mode": "explicit", "start": "2026-01-01", "end": "2026-04-01"}
_TIMELINE_ONLY = ("tableColumns", "hierarchyColumn", "backgroundDecoration", "axis", "markers", "periods", "shading",
                  "timePresentation", "annotations", "annotationPresentation", "deadlines")


def _source(**deadlines: str) -> dict:
    """Span `a` ends 2026-02-14, span `b` ends 2026-03-12, point `g` is 2026-03-20, point `h` is 2026-03-05."""
    source = sr.project({
        "a": sr.span("a", date(2026, 1, 5), 40),
        "b": sr.span("b", date(2026, 2, 10), 30, owner="b"),
        "g": sr.point("g", date(2026, 3, 20)),
        "h": sr.point("h", date(2026, 3, 5)),
    })
    for key, value in deadlines.items():
        source["objects"][key]["deadline"] = value
    return source


# a slipped span, a kept span, a slipped point, a point kept on its day
MIXED = {"a": "2026-02-05", "b": "2026-03-25", "g": "2026-03-10", "h": "2026-03-05"}


def _parts(show: str | None = "all", *, color: str = "text", reach: float = 1.7, width: float = 2, order: int = 5,
           preset: str = "executive-light", role: bool = True) -> dict:
    parts = sr.bundle(preset)
    body = parts["theme"]["body"]
    if role:
        body["values"].update({"deadline-reach": {"type": "number", "value": reach},
                               "deadline-order": {"type": "number", "value": order},
                               "deadline-width": {"type": "number", "value": width}})
        body["roles"]["deadline-mark"] = {"strokeWidth": "deadline-width", "markReach": "deadline-reach",
                                          "markPaintOrder": "deadline-order"}
        body["colorBindings"]["deadline-mark.stroke"] = color
    else:  # the bundled appearances declare the role since #946: "no role" removes it
        body["roles"].pop("deadline-mark", None)
        body["colorBindings"].pop("deadline-mark.stroke", None)
    parts["view"]["body"]["window"] = dict(WINDOW)
    if show is not None:
        parts["view"]["body"]["deadlines"] = {"show": show}
    return parts


def _render(tmp_path: Path, source: dict | None = None, parts: dict | None = None, name: str = "render", **kwargs):
    directory = tmp_path / name
    directory.mkdir()
    return sr.render(directory, source or _source(**MIXED), presentation=parts or _parts(), **kwargs)


def _marks(rendered) -> list:
    return [item for item in rendered.surface.primitives if item.purpose == "deadline-mark"]


def _ticks(rendered) -> dict[str, object]:
    return {item.source_ref: item for item in _marks(rendered) if item.scene_id.startswith("deadline-tick:")}


def _runs(rendered) -> dict[str, object]:
    return {item.source_ref: item for item in _marks(rendered) if item.scene_id.startswith("deadline-run:")}


def _x(rendered, day: date) -> float:
    scale = rendered.surface.scale_manifest
    return scale.origin + (day - scale.domain_start).days * scale.unit_ratio


def _planned(rendered, object_id: str):
    return next(item for item in rendered.surface.primitives if item.purpose == "planned" and item.source_ref == object_id)


# --- geometry -------------------------------------------------------------------------------------------


def test_a_tick_stands_at_the_deadline_date_through_the_marks_scale_centred_on_the_planned_mark(tmp_path):
    rendered = _render(tmp_path)
    ticks = _ticks(rendered)
    assert set(ticks) == {"a", "b", "g", "h"}
    for object_id, day in {"a": date(2026, 2, 5), "b": date(2026, 3, 25), "g": date(2026, 3, 10), "h": date(2026, 3, 5)}.items():
        tick, mark = ticks[object_id], _planned(rendered, object_id)
        assert (tick.kind, tick.visual_role, tick.slot_id) == ("Path", "deadline-mark", "timeline")
        assert tick.bounds[0] == pytest.approx(_x(rendered, day)) and tick.bounds[2] == 0
        assert tick.bounds[3] == pytest.approx(mark.bounds[3] * 1.7)  # the Theme's markReach
        assert tick.bounds[1] + tick.bounds[3] / 2 == pytest.approx(mark.bounds[1] + mark.bounds[3] / 2)
        assert [tuple(point) for point in tick.points] == pytest.approx([(tick.bounds[0], tick.bounds[1]),
                                                                          (tick.bounds[0], tick.bounds[1] + tick.bounds[3])])


def test_a_slipped_deadline_has_a_run_from_the_tick_to_the_planned_finish_below_the_bar(tmp_path):
    rendered = _render(tmp_path)
    runs = _runs(rendered)
    assert set(runs) == {"a", "g"}  # b is kept, h is on its day
    span_run, point_run = runs["a"], runs["g"]
    assert span_run.bounds[0] == pytest.approx(_x(rendered, date(2026, 2, 5)))
    assert span_run.bounds[0] + span_run.bounds[2] == pytest.approx(_x(rendered, date(2026, 2, 14)))  # a span's finish is its end
    assert point_run.bounds[0] + point_run.bounds[2] == pytest.approx(_x(rendered, date(2026, 3, 20)))  # a point's is its date
    for run, object_id in ((span_run, "a"), (point_run, "g")):
        tick, mark = _ticks(rendered)[object_id], _planned(rendered, object_id)
        assert run.bounds[3] == 0 and run.bounds[1] == pytest.approx(tick.bounds[1] + tick.bounds[3])  # the tick's lower end
        assert run.bounds[1] > mark.bounds[1] + mark.bounds[3]  # beneath the bar, so it never covers the bar's own paint
        assert run.points[0][1] == run.points[1][1]


def test_a_deadline_before_the_bar_starts_still_draws_its_run_to_the_end(tmp_path):
    rendered = _render(tmp_path, _source(b="2026-01-20"))  # b starts 2026-02-10
    tick, run = _ticks(rendered)["b"], _runs(rendered)["b"]
    assert tick.bounds[0] < _planned(rendered, "b").bounds[0]
    assert run.bounds[0] == pytest.approx(tick.bounds[0])
    assert run.bounds[0] + run.bounds[2] == pytest.approx(_x(rendered, date(2026, 3, 12)))


def test_the_run_is_clipped_at_the_plot_edge_when_the_finish_is_beyond_the_window(tmp_path):
    source = _source(a="2026-03-20")
    source["objects"]["a"]["schedule"]["end"] = "2026-05-20"  # past the 2026-04-01 window edge
    rendered = _render(tmp_path, source)
    plot = next(slot for slot in rendered.surface.slots if slot.source == "timeline")
    run = _runs(rendered)["a"]
    assert run.bounds[0] + run.bounds[2] == pytest.approx(plot.bounds[0] + plot.bounds[2])


def test_the_paint_order_is_the_themes_above_the_marks_base(tmp_path):
    rendered = _render(tmp_path, parts=_parts(order=7))
    assert {item.paint_order for item in _marks(rendered)} == {107}
    assert all(item.paint_order < 107 for item in rendered.surface.primitives if item.purpose == "planned")


# --- selection ------------------------------------------------------------------------------------------


def test_slipped_draws_only_the_missed_promises(tmp_path):
    rendered = _render(tmp_path, parts=_parts("slipped"))
    assert set(_ticks(rendered)) == {"a", "g"} and set(_runs(rendered)) == {"a", "g"}


def test_all_draws_a_tick_for_every_deadline_and_a_run_only_for_the_slipped(tmp_path):
    rendered = _render(tmp_path, parts=_parts("all"))
    assert set(_ticks(rendered)) == {"a", "b", "g", "h"} and set(_runs(rendered)) == {"a", "g"}


def test_the_objects_with_a_run_are_exactly_the_w_deadline_objects(tmp_path):
    for deadlines in (MIXED, {"a": "2026-02-14", "b": "2026-03-11", "g": "2026-03-20", "h": "2026-03-04"},
                      {"a": "2026-03-01", "b": "2026-04-01", "g": "2026-03-21", "h": "2026-03-06"}):
        source = _source(**deadlines)
        rendered = _render(tmp_path, source, name="r" + "".join(deadlines.values()))
        warned = {item.details["object"] for item in deadline_warnings(source, schedule(source).placements)}
        assert set(_runs(rendered)) == warned


def test_a_deadline_equal_to_the_finish_keeps_the_promise_and_one_day_later_is_missed(tmp_path):
    on_the_day = _render(tmp_path, _source(a="2026-02-14"), name="day")
    assert "a" in _ticks(on_the_day) and "a" not in _runs(on_the_day)
    one_late = _render(tmp_path, _source(a="2026-02-13"), name="late")
    run = _runs(one_late)["a"]
    assert run.bounds[2] == pytest.approx(one_late.surface.scale_manifest.unit_ratio)


def test_an_object_without_a_deadline_gets_no_mark(tmp_path):
    rendered = _render(tmp_path, _source(a="2026-02-05"))
    assert set(_ticks(rendered)) == {"a"}


# --- defaults -------------------------------------------------------------------------------------------


def test_a_view_without_deadlines_changes_no_byte(tmp_path):
    plain = _render(tmp_path, _source(), _parts(None), name="plain")
    declared = _render(tmp_path, _source(**MIXED), _parts(None), name="declared")
    assert _marks(declared) == []
    assert plain.artifact.content == declared.artifact.content
    assert scene_document(plain.scene)["surfaces"] == scene_document(declared.scene)["surfaces"]


def test_a_theme_role_nobody_selects_changes_no_byte(tmp_path):
    bare = _render(tmp_path, _source(**MIXED), _parts(None, role=False), name="bare")  # no deadline role at all
    with_role = _render(tmp_path, _source(**MIXED), _parts(None), name="role")
    assert bare.artifact.content == with_role.artifact.content


def test_the_deadline_alone_in_the_project_moves_no_placement_and_adds_no_diagnostic_but_the_records(tmp_path):
    shown = _render(tmp_path, _source(**MIXED), name="shown")
    hidden = _render(tmp_path, _source(**MIXED), _parts(None), name="hidden")
    assert [item.scene_id for item in shown.surface.primitives if item.purpose == "planned"] == [
        item.scene_id for item in hidden.surface.primitives if item.purpose == "planned"]
    assert [item.bounds for item in shown.surface.primitives if item.purpose == "planned"] == [
        item.bounds for item in hidden.surface.primitives if item.purpose == "planned"]


# --- failure behaviour ----------------------------------------------------------------------------------


def test_a_deadline_outside_the_window_draws_nothing_and_is_recorded(tmp_path):
    rendered = _render(tmp_path, _source(a="2025-12-01", b="2026-05-01", g="2026-03-10"))
    assert set(_ticks(rendered)) == {"g"}
    assert [item for item in rendered.scene.diagnostics if item.startswith("I_LAYOUT_DEADLINE_")] == [
        "I_LAYOUT_DEADLINE_OUTSIDE_WINDOW:a", "I_LAYOUT_DEADLINE_OUTSIDE_WINDOW:b"]


def test_a_missing_theme_role_is_refused_not_painted_by_another_role(tmp_path):
    with pytest.raises(RenderFailed) as raised:
        _render(tmp_path, parts=_parts(role=False))
    assert (raised.value.code, raised.value.source_ref) == ("E_THEME_ROLE_REQUIRED", "/body/roles/deadline-mark")


@pytest.mark.parametrize("reach", [0, -1, 4.5])
def test_a_reach_outside_the_closed_range_is_refused(tmp_path, reach):
    with pytest.raises(RenderFailed) as raised:
        _render(tmp_path, parts=_parts(reach=reach))
    assert raised.value.code == "E_THEME_TOKEN_TYPE" and raised.value.source_ref == "/body/roles/deadline-mark/markReach"


def test_a_folded_header_point_is_recorded_and_not_decorated():
    class Tokens:
        def deadline_mark(self, role):
            return Decimal("1.5"), 5

    base = SimpleNamespace(plot=Rect(Decimal(0), Decimal(0), Decimal(100), Decimal(50)), scale=SimpleNamespace(
        domain_start=date(2026, 1, 1), domain_end=date(2026, 1, 11), range_start=0.0, range_end=100.0, origin=0.0,
        unit_ratio=10.0))
    folded = MarkPlacement("planned:group-header:grp:x", "x", Rect(Decimal(0), Decimal(0), Decimal(5), Decimal(5)),
                           (0, 0), (0, 0), semantic_id="planned")
    batch = compose_deadline_marks(
        base=base, theme_tokens=Tokens(), marks=(folded,), window=(date(2026, 1, 1), date(2026, 1, 11)), paint_order_base=100,
        deadlines=(ReviewDeadline("x", date(2026, 1, 5), date(2026, 1, 8), True),))
    assert batch.shapes == () and batch.diagnostics == ("I_LAYOUT_DEADLINE_FOLDED:x",)


def test_the_mark_is_drawn_in_lane_rows_and_in_automatic_rows_alike(tmp_path):
    lanes = _render(tmp_path, name="lanes")  # the packaged View packs lanes
    parts = _parts()
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    automatic = _render(tmp_path, parts=parts, name="automatic")
    assert not any(item.scene_id.startswith("review-lane") for item in automatic.surface.primitives)
    for rendered in (lanes, automatic):
        assert set(_ticks(rendered)) == {"a", "b", "g", "h"} and set(_runs(rendered)) == {"a", "g"}
        for object_id, tick in _ticks(rendered).items():
            mark = _planned(rendered, object_id)
            assert tick.bounds[1] + tick.bounds[3] / 2 == pytest.approx(mark.bounds[1] + mark.bounds[3] / 2)


# --- selection errors and the schema --------------------------------------------------------------------


@pytest.mark.parametrize("entry", [{}, {"show": "later"}, {"show": "slipped", "color": "red"}, "slipped"])
def test_a_malformed_member_is_a_schema_error_with_its_pointer(tmp_path, entry):
    parts = _parts(None)
    parts["view"]["body"]["deadlines"] = entry
    with pytest.raises(ClosureError) as raised:
        _render(tmp_path, parts=parts)
    assert raised.value.diagnostic_id == "E_VIEW_SCHEMA"
    assert raised.value.source_ref.startswith("/body/deadlines")


def test_the_dependency_network_surface_has_no_timeline_to_draw_a_deadline_on():
    view = _parts(None)["view"]
    body = view["body"]
    body["surface"] = "dependency-network"
    for key in _TIMELINE_ONLY:
        body.pop(key, None)
    validator = schema_validator("view-v0.28.schema.yaml")
    without = [error.message for error in validator.iter_errors(view)]
    body["deadlines"] = {"show": "all"}
    with_deadlines = [error.message for error in validator.iter_errors(view)]
    assert len(with_deadlines) == len(without) + 1, "the prohibition must add exactly one finding for `deadlines`"


# --- Scene and gates ------------------------------------------------------------------------------------


def test_the_scene_validates_and_the_contrast_gate_judges_every_mark_at_the_mark_floor(tmp_path):
    document = scene_document(_render(tmp_path).scene)
    validate_scene_document(document)
    findings = [item for item in evaluate_scene_contrast(document) if item.visual_role == "deadline-mark"]
    assert len(findings) == 6  # four ticks and two runs
    assert {(item.code, item.floor) for item in findings} == {("E_SCENE_MARK_CONTRAST", 3.0)}
    assert all(item.severity == "info" and item.contrast_ratio >= 3.0 for item in findings)
    # a tick that crosses a bar is judged against the bar, the rest against the row ground
    assert {item.ground_kind for item in findings} == {"flat", "canvas"}


def test_the_contrast_gate_fails_ink_that_cannot_be_seen_on_the_row_and_on_a_bar(tmp_path):
    document = scene_document(_render(tmp_path, parts=_parts(color="neutral")).scene)
    findings = [item for item in evaluate_scene_contrast(document) if item.visual_role == "deadline-mark"]
    assert findings and all(item.severity == "error" and item.contrast_ratio < 3.0 for item in findings)
    assert {item.ground_kind for item in findings} == {"flat", "canvas"}  # on a bar and on the row ground
    assert any(item.ground_id.startswith("planned:") for item in findings if item.ground_kind == "flat")


def test_the_perceptibility_gate_finds_no_error_in_the_marks(tmp_path):
    document = scene_document(_render(tmp_path).scene)
    assert [item for item in evaluate_scene_perceptibility(document) if item.severity == "error"] == []


def test_the_svg_carries_each_path_in_the_role_paint(tmp_path):
    rendered = _render(tmp_path, parts=_parts(width=3))
    svg = rendered.artifact.content.decode()
    mark = _marks(rendered)[0]
    assert mark.paint.stroke_width == 3 and mark.paint.fill is None and mark.paint.stroke
    assert svg.count(mark.paint.stroke) >= 6


# --- the legend -----------------------------------------------------------------------------------------


def test_the_legend_entry_is_a_line_swatch_in_the_roles_paint(tmp_path):
    detail = safe_load(builtin_preset_source_root("presets/bundles/executive-light").joinpath("detail.yaml").read_bytes())
    detail["body"]["legend"] = [*detail["body"]["legend"], {"role": "deadlineMark", "label": "Deadline"}]
    rendered = _render(tmp_path, detail=detail)
    swatch = next(item for item in rendered.surface.primitives if item.scene_id == "legend-swatch:deadlineMark")
    assert (swatch.kind, swatch.visual_role, swatch.purpose) == ("Path", "deadline-mark", "deadline-mark")
    assert swatch.paint.stroke == _marks(rendered)[0].paint.stroke
    assert any(item.text == "Deadline" for item in rendered.surface.primitives if item.kind == "Text")


# --- obstacles, hosts and the window edge ---------------------------------------------------------------


def _overlaps_segment(box, points, pad=0.0) -> bool:
    """Whether the axis-aligned segment (a tick or a run) crosses the rectangle `box`."""
    (x1, y1), (x2, y2) = points
    left, top, width, height = box
    return (min(x1, x2) <= left + width + pad and max(x1, x2) >= left - pad
            and min(y1, y2) <= top + height + pad and max(y1, y2) >= top - pad)


def test_an_annotation_candidate_never_covers_a_tick_or_a_run(tmp_path):
    source, parts = _source(**MIXED), _parts()
    sr.add_notes(source, parts["view"], ["a", "g", "h", "b"], [sr.candidate("plot-near", connector="leader")], words=3)
    rendered = _render(tmp_path, source, parts)
    boxes = [item for item in rendered.surface.primitives if item.scene_id.startswith("annotation-box:")]
    assert len(boxes) == 4
    for box in boxes:
        for mark in _marks(rendered):
            assert not _overlaps_segment(box.bounds, mark.points), (box.scene_id, mark.scene_id)


def test_a_deadline_on_the_first_window_day_is_drawn_and_one_day_before_it_is_recorded(tmp_path):
    first = _render(tmp_path, _source(a="2026-01-01"), name="first")  # the window starts 2026-01-01
    assert "a" in _ticks(first)
    before = _render(tmp_path, _source(a="2025-12-31"), name="before")
    assert "a" not in _ticks(before) and "I_LAYOUT_DEADLINE_OUTSIDE_WINDOW:a" in before.scene.diagnostics


def test_a_deadline_on_the_window_edge_is_drawn_and_one_day_past_it_is_recorded(tmp_path):
    edge = _render(tmp_path, _source(a="2026-04-01"), name="edge")  # the window ends 2026-04-01
    assert "a" in _ticks(edge) and not [item for item in edge.scene.diagnostics if item.startswith("I_LAYOUT_DEADLINE_")]
    past = _render(tmp_path, _source(a="2026-04-02"), name="past")
    assert "a" not in _ticks(past)
    assert "I_LAYOUT_DEADLINE_OUTSIDE_WINDOW:a" in past.scene.diagnostics


def test_only_a_planned_mark_hosts_a_deadline_never_a_snapshot_or_scenario_mark():
    class Tokens:
        def deadline_mark(self, role):
            return Decimal("1.5"), 5

    base = SimpleNamespace(plot=Rect(Decimal(0), Decimal(0), Decimal(100), Decimal(50)), scale=SimpleNamespace(
        domain_start=date(2026, 1, 1), domain_end=date(2026, 1, 11), range_start=0.0, range_end=100.0, origin=0.0,
        unit_ratio=10.0))
    bounds = Rect(Decimal(10), Decimal(10), Decimal(20), Decimal(8))
    marks = (MarkPlacement("snapshot:row:x", "x", bounds, (0, 0), (0, 0), semantic_id="snapshot"),
             MarkPlacement("planned:row:x", "x", bounds, (0, 0), (0, 0), semantic_id="planned", slot_id="timeline"))
    batch = compose_deadline_marks(
        base=base, theme_tokens=Tokens(), marks=marks, window=(date(2026, 1, 1), date(2026, 1, 11)), paint_order_base=100,
        deadlines=(ReviewDeadline("x", date(2026, 1, 5), date(2026, 1, 8), True),))
    assert [item.placement_id for item in batch.shapes] == ["deadline-tick:row:x", "deadline-run:row:x"]
    assert batch.shapes[0].bounds.inline == Decimal("40.0")
    assert batch.shapes[0].bounds.block_size == Decimal("12.0")  # 8 * the reach of 1.5
