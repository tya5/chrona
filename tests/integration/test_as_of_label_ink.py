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
