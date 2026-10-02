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
STARTER_CATALOG = ROOT / "src/chrona/resources/icons/chrona-theme-starter-v2026-09-29.yaml"
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
    assert (band.bounds[1], band.bounds[3]) == pytest.approx((plot.bounds[1], plot.bounds[3]))
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
    assert early.bounds[0] == pytest.approx(_x(rendered, date(2026, 1, 1)))
    assert early.bounds[0] + early.bounds[2] == pytest.approx(_x(rendered, date(2026, 2, 1)))
    assert late.bounds[0] == pytest.approx(_x(rendered, date(2026, 3, 1)))
    assert late.bounds[0] + late.bounds[2] == pytest.approx(_x(rendered, date(2026, 4, 1)))


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
    (finding,) = [item for item in evaluate_scene_contrast(document) if item.visual_role == "period-band"]
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
    base = SimpleNamespace(timeline=SimpleNamespace(bounds=plot), scale=scale)
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
