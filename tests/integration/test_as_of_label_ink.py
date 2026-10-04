"""A Theme binding on `as-of-label` gives the as-of label its own ink on its chip (#1110).

The label took the shared `text` colour whatever `as-of-label.fill` said, and the binding validated without a
consumer. Synthetic Project through the packaged `executive-light` bundle; no test reads `examples/`.
"""
from __future__ import annotations

from datetime import date

import pytest

from chrona.presentation.model.closure import ClosureError
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document
from tests.support import synthetic_review as sr

ACTUAL = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
          "body": {"asOf": "2026-02-20", "observations": []}}


def _render(directory, *, chip=True, ink=None, extra=None):
    directory.mkdir(parents=True, exist_ok=True)
    source = sr.project({"a": sr.span("a", date(2026, 2, 2), 40, title="Alpha")})
    parts = sr.bundle("executive-light")
    body = parts["theme"]["body"]
    if chip:
        body["values"]["asof-chip-padding"] = {"type": "number", "value": 0.3}
        body["roles"]["as-of-label-chip"] = {"backgroundTreatment": "fill", "chipPadding": "asof-chip-padding"}
        body["colorBindings"]["as-of-label-chip.fill"] = "warning"
    if ink:
        body["colorBindings"]["as-of-label.fill"] = ink
    body["colorBindings"].update(extra or {})
    return sr.render(directory, source, presentation=parts, actual=ACTUAL)


def _label(rendered):
    return next(item for item in rendered.surface.primitives if item.scene_id == "as-of-label")


def _chip(rendered):
    return next(item for item in rendered.surface.primitives if item.scene_id == "chip:as-of-label")


def _findings(rendered):
    return [item for item in evaluate_scene_contrast(scene_document(rendered.scene)) if item.purpose == "as-of-label"]


def test_a_declared_fill_paints_the_label_and_the_gate_judges_it_against_the_chip(tmp_path):
    plain = _render(tmp_path / "plain")
    inked = _render(tmp_path / "inked", ink="surface")
    assert _label(plain).visual_role == "text"
    assert _label(inked).visual_role == "as-of-label"
    assert _label(inked).paint.fill != _label(plain).paint.fill
    assert _label(inked).bounds == _label(plain).bounds  # colour moves nothing
    findings = _findings(inked)
    # The gate judges the label's own ink on the chip: white on the amber chip passes, the default dark ink does not.
    assert findings and all(item.floor == 4.5 and item.severity != "error" for item in findings)
    assert all(item.severity == "error" for item in _findings(plain))


def test_an_ink_that_cannot_be_read_on_the_chip_is_reported(tmp_path):
    same_as_chip = _render(tmp_path, ink="warning")  # the chip's own colour: unreadable
    findings = _findings(same_as_chip)
    assert findings and all(item.severity == "error" for item in findings)


def test_without_the_binding_the_label_keeps_the_text_colour_byte_for_byte(tmp_path):
    first = _render(tmp_path / "a")
    second = _render(tmp_path / "b")
    assert scene_document(first.scene)["surfaces"] == scene_document(second.scene)["surfaces"]
    assert _label(first).paint.fill == _label(_render(tmp_path / "c", chip=False)).paint.fill


@pytest.mark.parametrize("target", ["as-of-label.stroke", "as-of-label.gradientStart"])
def test_a_binding_no_primitive_reads_fails_at_its_pointer(tmp_path, target):
    with pytest.raises(ClosureError) as raised:
        _render(tmp_path, extra={target: "text"})
    assert raised.value.diagnostic_id == "E_THEME_ROLE_PROPERTY_UNSUPPORTED"
    assert raised.value.source_ref.endswith(target)  # the pointer of the binding no primitive reads


# --- the as-of label's own typography (reviewer addendum of #1110) ----------------------------------------------


def _render_typed(directory, *, size=9, fill_only=False, placement=None, viewport=(1600, None)):
    directory.mkdir(parents=True, exist_ok=True)
    source = sr.project({"a": sr.span("a", date(2026, 2, 2), 40, title="Alpha")})
    parts = sr.bundle("executive-light")
    body = parts["theme"]["body"]
    body["values"]["asof-chip-padding"] = {"type": "number", "value": 0.3}
    body["roles"]["as-of-label-chip"] = {"backgroundTreatment": "fill", "chipPadding": "asof-chip-padding"}
    body["colorBindings"]["as-of-label-chip.fill"] = "warning"
    if fill_only:
        body["colorBindings"]["as-of-label.fill"] = "surface"
    else:
        body["values"]["asof-size"] = {"type": "number", "value": size}
        body["roles"]["as-of-label"] = {key: value for key, value in body["roles"]["text"].items()
                                       if key not in {"iconScale", "iconGap"}} | {"fontSize": "asof-size"}
    if placement:
        next(item for item in parts["view"]["body"]["markers"] if item["kind"] == "asOf")["placement"] = placement
    return sr.render(directory, source, presentation=parts, actual=ACTUAL, viewport=viewport)


def _typed_reserve(size=9):
    from chrona.presentation.layout.asof_foot_reserve import below_plot_reserve
    from chrona.presentation.model.theme_tokens import ThemeTokenView
    theme = sr.bundle("executive-light")["theme"]
    body = theme["body"]
    body["values"]["asof-chip-padding"] = {"type": "number", "value": 0.3}
    body["roles"]["as-of-label-chip"] = {"backgroundTreatment": "fill", "chipPadding": "asof-chip-padding"}
    body["values"]["asof-size"] = {"type": "number", "value": size}
    body["roles"]["as-of-label"] = {key: value for key, value in body["roles"]["text"].items()
                                   if key not in {"iconScale", "iconGap"}} | {"fontSize": "asof-size"}
    return below_plot_reserve(ThemeTokenView({**theme, "version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme"}))


def test_a_role_with_its_own_size_sets_the_label_and_its_chip_follows(tmp_path):
    plain, typed = _render(tmp_path / "plain"), _render_typed(tmp_path / "typed")
    assert _label(plain).text_layout.font_size == 14 and _label(typed).text_layout.font_size == 9
    assert _chip(typed).bounds[3] < _chip(plain).bounds[3]  # the chip's block size follows the role
    label, chip = _label(typed), _chip(typed)
    pad = chip.bounds[3] - label.bounds[3]
    assert pad == pytest.approx(2 * 0.3 * 9 / 2)  # the chip padding is a ratio of the role's own size
    assert chip.bounds[2] == pytest.approx(label.bounds[2] + 2 * 0.3 * 9)


def test_a_role_that_only_binds_a_colour_keeps_the_text_size(tmp_path):
    plain, ink_only = _render(tmp_path / "plain"), _render_typed(tmp_path / "ink", fill_only=True)
    assert _label(ink_only).text_layout.font_size == _label(plain).text_layout.font_size
    assert _chip(ink_only).bounds[2:] == _chip(plain).bounds[2:]


def test_the_space_reserved_below_the_plot_follows_the_role_size(tmp_path):
    foot_plain = _render_typed(tmp_path / "foot-plain", fill_only=True, placement="foot")
    below_plain = _render_typed(tmp_path / "below-plain", fill_only=True, placement="below-plot")
    foot_typed = _render_typed(tmp_path / "foot-typed", placement="foot")
    below_typed = _render_typed(tmp_path / "below-typed", placement="below-plot")
    grown_plain = below_plain.surface.canvas_bounds[3] - foot_plain.surface.canvas_bounds[3]
    grown_typed = below_typed.surface.canvas_bounds[3] - foot_typed.surface.canvas_bounds[3]
    assert 0 < grown_typed < grown_plain  # a smaller chip reserves less
    label = _label(below_typed)
    rule = next(item for item in below_typed.surface.primitives if item.scene_id == "as-of")
    assert label.bounds[1] >= rule.points[-1][1]  # still below the plot
    # Layout's reservation is exactly the placed gap plus the placed chip, both from the role's own size.
    chip = _chip(below_typed)
    placed = (chip.bounds[1] - rule.points[-1][1]) + chip.bounds[3]
    assert placed == pytest.approx(_typed_reserve())
