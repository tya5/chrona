"""Named periods: View selection, Layout band, Scene primitive and the gates that cover it (#582, S3).

Each rule is proven on a synthetic Project rendered through a packaged preset bundle, so a corpus edit cannot
change what these tests prove. The HALCYON slide that shows a launch window is evidence, not a gate.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.surface_backgrounds import validate_background_shapes
from chrona.presentation.layout.surface_periods import compose_period_bands
from chrona.presentation.layout.surface_quality import ScalePlacement, ShapePlacement
from chrona.presentation.model.closure import ClosureError
from chrona.presentation.model.projection import ReviewPeriod
from chrona.presentation.model.semantic_registry import semantic_binding
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility
from chrona.presentation.scene.serialization import scene_document, validate_scene_document
from chrona.resources import schema_validator
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
STARTER_CATALOG = ROOT / "src/chrona/resources/icons/chrona-theme-starter-v2026-10-09.yaml"
WINDOW = {"mode": "explicit", "start": "2026-01-01", "end": "2026-04-01"}
# Every View member the dependency-network surface forbids because it has no timeline.
_TIMELINE_ONLY = ("tableColumns", "hierarchyColumn", "backgroundDecoration", "axis", "markers", "periods", "shading",
                  "timePresentation", "annotations", "annotationPresentation")
FEBRUARY = {"start": "2026-02-01", "end": "2026-03-01"}


def _source(**periods) -> dict:
    source = sr.project({
        "a": sr.span("a", date(2026, 1, 5), 40),
        "b": sr.span("b", date(2026, 2, 10), 30, owner="b"),
        "g": sr.point("g", date(2026, 3, 20)),
    })
    if periods:
        source["periods"] = periods
    return source


def _parts(*, treatment: str = "fill", order: int = 11, color: str = "accent", select=("window",),
           preset: str = "executive-light", pattern: str | None = None) -> dict:
    parts = sr.bundle(preset)
    body = parts["theme"]["body"]
    # The packaged Theme paints the band as an outline; each test states its own paint, so start from none (#880).
    for key in ("period-band.fill", "period-band.stroke"):
        body["colorBindings"].pop(key, None)
    role = {"backgroundTreatment": treatment, "backgroundPaintOrder": order, "opacity": "opacity.axis-band"}
    if pattern is not None:
        role["pattern"] = pattern
        body["colorBindings"]["period-band.stroke"] = "text"
    if treatment == "outline":
        role["strokeWidth"] = "stroke-width"
    body["roles"]["period-band"] = role
    if treatment == "fill":
        body["colorBindings"]["period-band.fill"] = color
    elif treatment == "outline":
        body["colorBindings"]["period-band.stroke"] = color
    parts["view"]["body"]["window"] = dict(WINDOW)
    if select is not None:
        parts["view"]["body"]["periods"] = [{"id": item} for item in select]
    return parts


def _labelled(parts: dict, placement: str = "top", *, overflow: str | None = None, chip: bool = False,
              treatment: str = "required", select: str = "window") -> dict:
    """Select `select` with a label and give the Theme the label role (and, optionally, its chip)."""
    body = parts["theme"]["body"]
    body["roles"]["period-label"] = {**{key: value for key, value in body["roles"]["annotation-note-text"].items()
                                        if key != "contrastTreatment"}, "contrastTreatment": treatment}
    body["colorBindings"]["period-label.fill"] = "text"
    if chip:
        body["values"]["period-chip-padding"] = {"type": "number", "value": 0.5}
        body["roles"]["period-label-chip"] = {"backgroundTreatment": "fill", "chipPadding": "period-chip-padding"}
        body["colorBindings"]["period-label-chip.fill"] = "surfaceRaised"
    entry: dict = {"id": select, "label": {"placement": placement}}
    if overflow is not None:
        entry["label"]["overflow"] = overflow
    parts["view"]["body"]["periods"] = [entry]
    return parts


def _labels(rendered) -> list:
    return [item for item in rendered.surface.primitives if item.purpose == "period-label"]


def _directory(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name
    path.mkdir()
    return path


def _render(tmp_path: Path, source: dict | None = None, parts: dict | None = None, name: str = "render",
            catalogs: tuple[Path, ...] = ()):
    return sr.render(_directory(tmp_path, name), source or _source(window=FEBRUARY), presentation=parts or _parts(),
                     icon_catalogs=catalogs)


def _patterned(tmp_path: Path):
    parts = _parts(preset="technical-print", pattern="starter-halftone", color="surfaceRaised")
    return _render(tmp_path, parts=parts, catalogs=(STARTER_CATALOG,))


def _plot_bottom(rendered) -> float:
    """Where the plot ends (#880): the bottom of the last row, which is above the slot when the slot is taller."""
    return max(float(row.bounds[1] + row.bounds[3]) for row in rendered.surface.rows)


def _bands(rendered) -> list:
    return [item for item in rendered.surface.primitives if item.purpose == "period-band"]


def _x(rendered, day: date) -> float:
    scale = rendered.surface.scale_manifest
    return scale.origin + (day - scale.domain_start).days * scale.unit_ratio


# --- geometry -------------------------------------------------------------------------------------------


def test_a_band_spans_its_dates_through_the_marks_scale_and_the_plot_rows(tmp_path):
    rendered = _render(tmp_path)
    (band,) = _bands(rendered)
    plot = next(slot for slot in rendered.surface.slots if slot.source == "timeline")
    assert (band.scene_id, band.source_ref, band.visual_role, band.kind) == (
        "period-band:window", "window", "period-band", "Rect")
    assert band.bounds[0] == pytest.approx(_x(rendered, date(2026, 2, 1)))
    assert band.bounds[0] + band.bounds[2] == pytest.approx(_x(rendered, date(2026, 3, 1)))
    assert band.bounds[1] == pytest.approx(plot.bounds[1])
    assert band.bounds[1] + band.bounds[3] == pytest.approx(_plot_bottom(rendered))
    assert band.slot_id == "timeline"


def test_the_end_is_exclusive_so_one_more_day_widens_the_band_by_exactly_one_day(tmp_path):
    shorter = _render(tmp_path, name="shorter")
    longer = _render(tmp_path, _source(window={"start": "2026-02-01", "end": "2026-03-02"}), name="longer")
    (short,), (long,) = _bands(shorter), _bands(longer)
    assert long.bounds[2] - short.bounds[2] == pytest.approx(shorter.surface.scale_manifest.unit_ratio)


def test_a_reference_resolves_through_the_plan_and_follows_it(tmp_path):
    source = _source(window={"start": {"object": "g", "endpoint": "at"}, "end": "2026-03-30"})
    rendered = _render(tmp_path, source, name="planned")
    (band,) = _bands(rendered)
    assert band.bounds[0] == pytest.approx(_x(rendered, date(2026, 3, 20)))
    moved = deepcopy(source)
    moved["objects"]["g"]["schedule"]["at"] = "2026-03-10"
    rendered_moved = _render(tmp_path, moved, name="moved")
    (moved_band,) = _bands(rendered_moved)
    assert moved_band.bounds[0] == pytest.approx(_x(rendered_moved, date(2026, 3, 10)))


def test_a_period_is_clipped_to_the_window_and_never_extends_it(tmp_path):
    source = _source(window={"start": "2025-12-01", "end": "2026-02-01"}, late={"start": "2026-03-01", "end": "2026-09-01"})
    rendered = _render(tmp_path, source, _parts(select=("window", "late")))
    early, late = _bands(rendered)
    scale = rendered.surface.scale_manifest
    assert (scale.domain_start, scale.domain_end) == (date(2026, 1, 1), date(2026, 4, 1))
    # The window does not grow; a band clipped at the window edge reaches the plot edge, the margin the scale leaves (#880).
    plot = next(slot for slot in rendered.surface.slots if slot.source == "timeline")
    assert early.bounds[0] == pytest.approx(plot.bounds[0])
    assert early.bounds[0] + early.bounds[2] == pytest.approx(_x(rendered, date(2026, 2, 1)))
    assert late.bounds[0] == pytest.approx(_x(rendered, date(2026, 3, 1)))
    assert late.bounds[0] + late.bounds[2] == pytest.approx(plot.bounds[0] + plot.bounds[2])


def test_a_period_outside_the_window_draws_nothing_and_is_recorded(tmp_path):
    source = _source(window={"start": "2025-01-01", "end": "2025-02-01"}, after={"start": "2026-04-01", "end": "2026-05-01"})
    rendered = _render(tmp_path, source, _parts(select=("window", "after")))
    assert _bands(rendered) == []
    assert [item for item in rendered.scene.diagnostics if item.startswith("I_LAYOUT_PERIOD_OUTSIDE_WINDOW:")] == [
        "I_LAYOUT_PERIOD_OUTSIDE_WINDOW:window", "I_LAYOUT_PERIOD_OUTSIDE_WINDOW:after"]
    assert not [item for item in rendered.scene.diagnostics if item.startswith("W_")]


def test_the_selection_order_is_the_drawing_order_and_unselected_periods_are_not_drawn(tmp_path):
    source = _source(a={"start": "2026-01-10", "end": "2026-01-20"}, b={"start": "2026-02-10", "end": "2026-02-20"},
                     c={"start": "2026-03-10", "end": "2026-03-20"})
    rendered = _render(tmp_path, source, _parts(select=("c", "a")))
    assert [item.source_ref for item in _bands(rendered)] == ["c", "a"]


# --- selection errors -----------------------------------------------------------------------------------


def test_a_view_naming_an_undeclared_period_is_refused_with_the_declared_ones(tmp_path):
    with pytest.raises(RenderFailed) as raised:
        _render(tmp_path, parts=_parts(select=("window", "launch")))
    error = raised.value
    assert (error.code, error.source_ref) == ("E_VIEW_PERIOD_UNKNOWN", "/body/periods/1/id")
    assert "launch" in error.message and "declared: window" in error.message


def test_a_view_naming_a_period_when_the_project_declares_none_says_so(tmp_path):
    with pytest.raises(RenderFailed) as raised:
        _render(tmp_path, _source(), _parts(select=("window",)))
    assert "declared: none" in raised.value.message


def test_a_view_selecting_the_same_period_twice_is_refused(tmp_path):
    with pytest.raises(ClosureError) as raised:
        _render(tmp_path, parts=_parts(select=("window", "window")))
    assert raised.value.diagnostic_id == "E_VIEW_PERIOD_DUPLICATE"


@pytest.mark.parametrize("entry", [{}, {"id": ""}, {"id": "window", "color": "red"}])
def test_a_malformed_selection_is_a_schema_error_with_its_pointer(tmp_path, entry):
    parts = _parts(select=None)
    parts["view"]["body"]["periods"] = [entry]
    with pytest.raises(ClosureError) as raised:
        _render(tmp_path, parts=parts)
    assert raised.value.diagnostic_id == "E_VIEW_SCHEMA"
    assert raised.value.source_ref.startswith("/body/periods/0")


def test_the_dependency_network_surface_has_no_timeline_to_draw_a_period_on():
    view = _parts(select=None)["view"]
    body = view["body"]
    body["surface"] = "dependency-network"
    for key in _TIMELINE_ONLY:
        body.pop(key, None)
    validator = schema_validator("view-v0.28.schema.yaml")
    without = [error.message for error in validator.iter_errors(view)]
    body["periods"] = [{"id": "window"}]
    with_periods = [error.message for error in validator.iter_errors(view)]
    assert len(with_periods) == len(without) + 1, "the prohibition must add exactly one finding for `periods`"


# --- defaults -------------------------------------------------------------------------------------------


def test_a_project_period_the_view_does_not_select_changes_no_byte(tmp_path):
    plain = _render(tmp_path, _source(), _parts(select=None), name="plain")
    declared = _render(tmp_path, _source(window=FEBRUARY), _parts(select=None), name="declared")
    assert plain.artifact.content == declared.artifact.content
    # The Project's content identity is provenance and moves with any Project edit; the drawn surface does not.
    assert scene_document(plain.scene)["surfaces"] == scene_document(declared.scene)["surfaces"]
    assert _bands(declared) == []


def test_an_empty_selection_changes_no_byte(tmp_path):
    parts = _parts(select=None)
    parts["view"]["body"]["periods"] = []
    plain = _render(tmp_path, _source(), _parts(select=None), name="plain")
    empty = _render(tmp_path, _source(), parts, name="empty")
    assert plain.artifact.content == empty.artifact.content


# --- Theme paint ----------------------------------------------------------------------------------------


def test_a_missing_period_band_role_is_refused_not_painted_by_another_role(tmp_path):
    parts = _parts()
    del parts["theme"]["body"]["roles"]["period-band"]
    del parts["theme"]["body"]["colorBindings"]["period-band.fill"]
    with pytest.raises(RenderFailed) as raised:
        _render(tmp_path, parts=parts)
    assert (raised.value.code, raised.value.source_ref) == ("E_THEME_ROLE_REQUIRED", "/body/roles/period-band")


def test_the_fill_treatment_paints_the_theme_colour_and_order(tmp_path):
    (band,) = _bands(_render(tmp_path))
    assert band.paint.fill and band.paint.stroke is None and band.paint.opacity == 1.0
    assert band.paint_order == 11


def test_the_outline_treatment_paints_a_stroke_and_no_fill(tmp_path):
    (band,) = _bands(_render(tmp_path, parts=_parts(treatment="outline")))
    assert band.paint.fill is None and band.paint.stroke and band.paint.stroke_width


def test_the_none_treatment_draws_nothing_and_records_the_absence(tmp_path):
    rendered = _render(tmp_path, parts=_parts(treatment="none"))
    assert _bands(rendered) == []
    assert "period-band" in {item.visual_role for item in rendered.surface.decoration_dispositions}


def test_a_catalogue_pattern_is_completed_in_layout_over_the_band(tmp_path):
    (band,) = _bands(_patterned(tmp_path))
    assert band.pattern is not None and band.pattern.primitives
    assert tuple(band.pattern.region_bounds) == pytest.approx(band.bounds)
    assert tuple(band.pattern.clip_bounds) == pytest.approx(band.bounds)


def test_the_band_is_painted_beneath_every_mark(tmp_path):
    rendered = _render(tmp_path)
    (band,) = _bands(rendered)
    marks = [item for item in rendered.surface.primitives if item.purpose in {"planned", "actual"}]
    assert marks and all(band.paint_order < item.paint_order for item in marks)


# --- Scene and gates ------------------------------------------------------------------------------------


def test_the_scene_validates_and_the_contrast_gate_evaluates_the_band(tmp_path):
    document = scene_document(_render(tmp_path).scene)
    validate_scene_document(document)
    findings = [item for item in evaluate_scene_contrast(document) if item.visual_role == "period-band"]
    assert [(item.code, item.severity, item.floor) for item in findings] == [("E_SCENE_DECORATION_CONTRAST", "info", 1.10)]
    assert findings[0].contrast_ratio > 1.10


def test_the_contrast_gate_fails_a_band_that_cannot_be_seen(tmp_path):
    document = scene_document(_render(tmp_path, parts=_parts(color="surface")).scene)
    (warned,) = [item for item in evaluate_scene_contrast(document) if item.visual_role == "period-band"]
    assert warned.severity == "warning" and warned.contrast_ratio < 1.10  # a decoration warns (#995)
    (finding,) = [item for item in evaluate_scene_contrast(document, decoration_severity="error")
                  if item.visual_role == "period-band"]
    assert finding.severity == "error" and finding.contrast_ratio < 1.10


def test_the_contrast_gate_reports_a_pattern_band_by_its_substrate_and_ink(tmp_path):
    document = scene_document(_patterned(tmp_path).scene)
    findings = [item for item in evaluate_scene_contrast(document) if item.visual_role == "period-band"]
    assert {(item.paint_channel, item.ground_kind) for item in findings} == {
        ("fill", "canvas"), ("stroke", "pattern-substrate"), ("stroke", "canvas")}


def test_the_perceptibility_gate_finds_no_error_in_a_plain_band(tmp_path):
    document = scene_document(_render(tmp_path).scene)
    assert [item for item in evaluate_scene_perceptibility(document) if item.severity == "error"] == []


# --- clipping to the plot, on a scale that overhangs it -------------------------------------------------


def _band_batch(scale_origin: float, ratio: float, periods: tuple[ReviewPeriod, ...]):
    plot = Rect(Decimal(100), Decimal(50), Decimal(300), Decimal(200))
    scale = ScalePlacement("table-timeline", "primary", date(2026, 1, 1), date(2026, 1, 31), 100.0, 400.0,
                           scale_origin, ratio)
    base = SimpleNamespace(timeline=SimpleNamespace(bounds=plot), plot=plot, scale=scale)
    tokens = SimpleNamespace(background=lambda role: ("fill", 11))
    return compose_period_bands(base=base, theme_tokens=tokens, periods=periods,
                                window=(date(2026, 1, 1), date(2026, 1, 31)))


def test_a_band_never_leaves_the_plot_even_when_the_scale_overhangs_it():
    # The mark-aware scale may place a date outside the plot's inline range; a band is clipped to the plot.
    batch = _band_batch(50.0, 15.0, (ReviewPeriod("p", "P", date(2026, 1, 1), date(2026, 1, 31)),))
    (shape,) = batch.shapes
    assert (float(shape.bounds.inline), float(shape.bounds.inline + shape.bounds.inline_size)) == (100.0, 400.0)
    assert (float(shape.bounds.block), float(shape.bounds.block_size)) == (50.0, 200.0)


def test_a_period_wholly_beyond_the_plot_edge_is_recorded_not_drawn():
    batch = _band_batch(-100.0, 5.0, (ReviewPeriod("p", "P", date(2026, 1, 1), date(2026, 1, 10)),))
    assert batch.shapes == () and batch.diagnostics == ("I_LAYOUT_PERIOD_OUTSIDE_WINDOW:p",)


# --- the one explicit overlay relation ------------------------------------------------------------------


def _shape(semantic_id: str, order: int, source: str = "s") -> ShapePlacement:
    return ShapePlacement(f"{semantic_id}:{source}", source, "Rect", Rect(Decimal(0), Decimal(0), Decimal(10), Decimal(10)),
                          slot_id="timeline", paint_order=order, semantic_id=semantic_id)


def _tokens(orders: dict[str, int], *, opacity: float = 0.5):
    return SimpleNamespace(background=lambda role: ("fill", orders[role]), opacity=lambda role: opacity)


def _orders(**by_semantic: int) -> dict[str, int]:
    return {semantic_binding(name).scene_role: order for name, order in by_semantic.items()}


@pytest.mark.parametrize(("upper", "lower"), [
    ("periodBand", "groupBand"), ("periodBand", "rowBand"), ("periodBand", "groupHeaderBand"),
    ("calendarClosed", "periodBand"), ("calendarClosed", "groupBand"),
])
def test_a_later_painted_translucent_overlay_may_cross_an_earlier_lower_ranked_background(upper, lower):
    orders = _orders(**{lower: 10, upper: 12})
    validate_background_shapes([_shape(lower, 10, "lower"), _shape(upper, 12, "upper")], _tokens(orders))


@pytest.mark.parametrize(("upper", "lower", "upper_order", "lower_order"), [
    ("periodBand", "groupBand", 9, 10),         # painted before the background it crosses
    ("periodBand", "groupBand", 10, 10),        # equal order is not a strict stacking
    ("groupBand", "periodBand", 12, 10),        # a lower-ranked background is never the overlay
    ("periodBand", "calendarClosed", 12, 11),   # the calendar closure ranks above a period
    ("groupHeaderBand", "rowBand", 11, 10),     # equal rank is never an overlay, even when strictly stacked
])
def test_any_other_translucent_crossing_is_still_rejected(upper, lower, upper_order, lower_order):
    orders = _orders(**{upper: upper_order, lower: lower_order})
    shapes = [_shape(lower, lower_order, "lower"), _shape(upper, upper_order, "upper")]
    with pytest.raises(LayoutError) as raised:
        validate_background_shapes(shapes, _tokens(orders))
    assert raised.value.diagnostic_id == "E_LAYOUT_BACKGROUND_OVERLAP"


def test_two_translucent_periods_may_not_cross():
    orders = _orders(periodBand=12)
    with pytest.raises(LayoutError) as raised:
        validate_background_shapes([_shape("periodBand", 12, "one"), _shape("periodBand", 12, "two")], _tokens(orders))
    assert raised.value.diagnostic_id == "E_LAYOUT_BACKGROUND_OVERLAP"


def test_opaque_backgrounds_may_overlap_in_any_order():
    orders = _orders(groupBand=10, periodBand=9)
    validate_background_shapes([_shape("groupBand", 10), _shape("periodBand", 9)], _tokens(orders, opacity=1.0))


# --- the label ------------------------------------------------------------------------------------------


@pytest.mark.parametrize("placement", ["top", "bottom", "inside"])
def test_a_label_is_a_scene_text_of_the_period_title_centred_on_its_band(tmp_path, placement):
    rendered = _render(tmp_path, parts=_labelled(_parts(), placement))
    (band,), (label,) = _bands(rendered), _labels(rendered)
    plot = next(slot for slot in rendered.surface.slots if slot.source == "timeline")
    assert (label.scene_id, label.source_ref, label.visual_role, label.kind, label.text) == (
        "period-label:window", "window", "period-label", "Text", "window")
    centre = label.bounds[0] + label.bounds[2] / 2
    assert centre == pytest.approx(band.bounds[0] + band.bounds[2] / 2, abs=1.0)
    top, bottom = label.bounds[1], label.bounds[1] + label.bounds[3]
    assert plot.bounds[1] - 0.01 <= top and bottom <= _plot_bottom(rendered) + 0.01
    if placement == "top":
        assert top - plot.bounds[1] < 4 * label.bounds[3]
    if placement == "bottom":
        assert _plot_bottom(rendered) - bottom < 4 * label.bounds[3]
    assert label.contrast_treatment == "required"


def _override(parts: dict, text: str) -> dict:
    parts["view"]["body"]["periods"][0]["label"]["text"] = text
    return parts


def test_a_view_label_text_replaces_the_project_period_title_for_that_view_only(tmp_path):
    rendered = _render(tmp_path, parts=_override(_labelled(_parts()), "OPENING NIGHT"))
    (label,) = _labels(rendered)

    assert label.text == "OPENING NIGHT"
    assert (label.scene_id, label.source_ref) == ("period-label:window", "window")
    # The Project period keeps its own title; only this View's caption changes.
    assert _labels(_render(tmp_path, parts=_labelled(_parts()), name="plain"))[0].text == "window"


def test_without_a_label_text_the_output_is_byte_identical(tmp_path):
    plain = _render(tmp_path, parts=_labelled(_parts()), name="plain")
    again = _render(tmp_path, parts=_labelled(_parts()), name="again")

    assert plain.artifact.content == again.artifact.content
    assert b"OPENING NIGHT" not in plain.artifact.content


def test_the_label_text_follows_the_literal_caption_rule(tmp_path):
    validator = schema_validator("view-v0.28.schema.yaml")
    for text, ok in (("OPENING NIGHT", True), ("", False), ("x" * 81, False), ("a" + chr(10) + "b", False)):
        view = _override(_labelled(_parts()), text)["view"]
        assert (not list(validator.iter_errors(view))) is ok, text


def test_a_label_text_without_a_placement_is_refused():
    validator = schema_validator("view-v0.28.schema.yaml")
    view = _parts()["view"]
    view["body"]["periods"] = [{"id": "window", "label": {"text": "OPENING NIGHT"}}]

    assert list(validator.iter_errors(view))


def test_a_band_without_a_label_selection_has_no_label_primitive(tmp_path):
    assert _labels(_render(tmp_path)) == []


def test_the_title_falls_back_to_the_period_identifier(tmp_path):
    source = _source(window={"start": "2026-02-01", "end": "2026-03-01"})
    (label,) = _labels(_render(tmp_path, source, _labelled(_parts())))
    assert label.text == "window"
    titled = _source(window={"title": "Launch window", "start": "2026-02-01", "end": "2026-03-01"})
    (named,) = _labels(_render(tmp_path, titled, _labelled(_parts()), name="titled"))
    assert named.text == "Launch window"


def test_a_label_slides_off_a_mark_it_would_cover_and_never_overprints_one(tmp_path):
    rendered = _render(tmp_path, parts=_labelled(_parts(), "inside"))
    (label,) = _labels(rendered)
    marks = [item for item in rendered.surface.primitives if item.purpose in {"planned", "actual"}]
    for mark in marks:
        overlap_x = min(label.bounds[0] + label.bounds[2], mark.bounds[0] + mark.bounds[2]) - max(label.bounds[0], mark.bounds[0])
        overlap_y = min(label.bounds[1] + label.bounds[3], mark.bounds[1] + mark.bounds[3]) - max(label.bounds[1], mark.bounds[1])
        assert not (overlap_x > 0 and overlap_y > 0), mark.scene_id


def _crowded_source() -> dict:
    """A band narrower than its label, over a plot so full of marks that no collision-free position exists."""
    objects = {f"t{i}": sr.span(f"t{i}", date(2026, 1, 5), 85, owner=f"o{i % 3}") for i in range(40)}
    source = sr.project(objects)
    source["periods"] = {"window": {"title": "A rather long period title", "start": "2026-02-01", "end": "2026-02-03"}}
    return source


def test_the_overflow_policy_decides_what_a_label_with_no_free_position_does(tmp_path):
    source = _crowded_source()
    suppressed = _render(tmp_path, source, _labelled(_parts(), "inside", overflow="suppress"), name="suppress")
    assert _labels(suppressed) == []
    assert any(item.startswith("W_LAYOUT_LABEL_SUPPRESSED:period-label:window") for item in suppressed.scene.diagnostics)
    visible = _render(tmp_path, source, _labelled(_parts(), "inside", overflow="visible-overflow"), name="visible")
    assert len(_labels(visible)) == 1
    default = _render(tmp_path, source, _labelled(_parts(), "inside"), name="default")
    assert [item.bounds for item in _labels(default)] == [item.bounds for item in _labels(visible)]


def test_a_label_is_an_obstacle_for_the_labels_placed_after_it(tmp_path):
    with_label = _render(tmp_path, parts=_labelled(_parts(), "top"), name="with")
    without = _render(tmp_path, name="without")
    (label,) = _labels(with_label)
    def overlaps(item) -> bool:
        return (min(label.bounds[0] + label.bounds[2], item.bounds[0] + item.bounds[2]) > max(label.bounds[0], item.bounds[0])
                and min(label.bounds[1] + label.bounds[3], item.bounds[1] + item.bounds[3]) > max(label.bounds[1], item.bounds[1]))
    later = [item for item in with_label.surface.primitives
             if item.kind == "Text" and item.purpose in {"member-label", "finish-delta"}]
    assert later and not [item.scene_id for item in later if overlaps(item)]
    assert [item.purpose for item in without.surface.primitives if item.purpose == "period-label"] == []


def test_a_chip_gives_the_label_its_own_ground_and_the_text_is_gated_against_it(tmp_path):
    rendered = _render(tmp_path, parts=_labelled(_parts(), "top", chip=True))
    (label,) = _labels(rendered)
    chips = [item for item in rendered.surface.primitives if item.visual_role == "period-label-chip"]
    assert [item.scene_id for item in chips] == ["chip:period-label:window"] and chips[0].source_ref == "window"
    chip = chips[0]
    assert chip.bounds[0] <= label.bounds[0] and chip.bounds[0] + chip.bounds[2] >= label.bounds[0] + label.bounds[2]
    document = scene_document(rendered.scene)
    (finding,) = [item for item in evaluate_scene_contrast(document) if item.visual_role == "period-label"]
    assert finding.ground_id == "chip:period-label:window" and finding.severity == "info"


def test_the_label_text_is_gated_at_its_declared_floor_and_against_its_ground(tmp_path):
    required = scene_document(_render(tmp_path, parts=_labelled(_parts(), "top"), name="required").scene)
    (finding,) = [item for item in evaluate_scene_contrast(required) if item.visual_role == "period-label"]
    assert finding.floor == 4.5 and finding.disposition == "required"
    relaxed = scene_document(_render(tmp_path, parts=_labelled(_parts(), "top", treatment="deemphasized"), name="relaxed").scene)
    (soft,) = [item for item in evaluate_scene_contrast(relaxed) if item.visual_role == "period-label"]
    assert soft.floor == 3.0 and soft.disposition == "deemphasized"
    # Text over a chip of its own colour cannot be read: the Scene gate fails on the chip ground.
    blind = _labelled(_parts(), "top", chip=True)
    blind["theme"]["body"]["colorBindings"]["period-label-chip.fill"] = "text"
    document = scene_document(_render(tmp_path, parts=blind, name="blind").scene)
    (weak,) = [item for item in evaluate_scene_contrast(document) if item.visual_role == "period-label"]
    assert weak.severity == "error" and weak.contrast_ratio < 4.5 and weak.ground_id == "chip:period-label:window"


def test_a_label_colour_below_its_floor_against_the_scheme_surface_is_refused_at_closure(tmp_path):
    faint = _labelled(_parts(), "top")
    faint["theme"]["body"]["colorBindings"]["period-label.fill"] = "surfaceRaised"
    with pytest.raises(ClosureError) as raised:
        _render(tmp_path, parts=faint)
    assert raised.value.diagnostic_id == "E_SCHEME_STATE_TEXT_CONTRAST"


def test_a_theme_that_declares_no_period_label_role_still_renders_every_other_surface(tmp_path):
    # The role is opt-in: classifying the label as state text must not require it of a Theme that selects none.
    parts = _parts(select=None)
    body = parts["theme"]["body"]
    for role in ("period-band", "period-label", "period-label-chip"):
        body["roles"].pop(role, None)
        for key in [key for key in body["colorBindings"] if key.startswith(f"{role}.")]:
            del body["colorBindings"][key]
    assert "period-label" not in body["roles"]
    assert _render(tmp_path, _source(), parts).surface.primitives


def test_a_missing_period_label_role_is_refused(tmp_path):
    parts = _labelled(_parts())
    del parts["theme"]["body"]["roles"]["period-label"]
    del parts["theme"]["body"]["colorBindings"]["period-label.fill"]
    with pytest.raises(RenderFailed):
        _render(tmp_path, parts=parts)


@pytest.mark.parametrize("label", [{}, {"placement": "left"}, {"placement": "top", "overflow": "clip"}, {"placement": "top", "x": 1}])
def test_a_malformed_label_is_a_schema_error(tmp_path, label):
    parts = _parts(select=None)
    parts["view"]["body"]["periods"] = [{"id": "window", "label": label}]
    with pytest.raises(ClosureError) as raised:
        _render(tmp_path, parts=parts)
    assert raised.value.diagnostic_id == "E_VIEW_SCHEMA" and raised.value.source_ref.startswith("/body/periods/0/label")
