"""Physical-only mark corner-radius bindings render through marks and legend (#1198).

All inputs are synthetic and pass through the packaged executive-light preset.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal
from xml.etree import ElementTree

import pytest

from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView
from chrona.presentation.scene.serialization import scene_document, serialize_scene
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr


DETAIL = {"version": "chrona/review-detail-profile/v0.1", "id": "physical-radius-legend",
          "body": {"legend": [{"role": "planned", "label": "Planned"}]}}


def _parts(*, physical_radius=None, remove_legacy=False):
    parts = sr.bundle()
    planned = parts["theme"]["body"]["roles"]["planned"]
    if remove_legacy:
        planned.pop("markCornerRadius")
    if physical_radius is not None:
        parts["theme"]["body"]["values"]["physical-radius"] = {
            "type": "radius", "value": physical_radius,
        }
        planned["cornerRadius"] = "physical-radius"
    return parts


def _render(tmp_path, parts):
    tmp_path.mkdir(parents=True, exist_ok=True)
    source = sr.project({"task": sr.span("task", date(2026, 2, 2), 30)})
    return sr.render(tmp_path, source, presentation=parts, detail=DETAIL)


def _svg_rect(rendered, scene_id):
    root = ElementTree.fromstring(rendered.artifact.content)
    return next(node for node in root.iter()
                if node.tag.endswith("rect") and node.attrib.get("data-scene-id") == scene_id)


def _pre_1198_mark_geometry(self, role):
    """Independent copy of mark_geometry at baseline ff333f820a368f9bfef7b9825d329b1fa89a6464."""
    height = self.number(role, "markHeight")
    offset = self.optional_number(role, "markOffset")
    order = self.number(role, "markPaintOrder")
    corner_radius = self.number(role, "markCornerRadius")
    if (height <= 0 or height > 1 or (offset is not None and (offset < 0 or offset + height > 1))
            or corner_radius < 0 or corner_radius > Decimal("0.5") or order != order.to_integral_value()):
        raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/markHeight")
    return height, offset, int(order), corner_radius


@pytest.mark.parametrize("radius", [0, 3, "capsule"], ids=["zero", "three-px", "capsule"])
def test_physical_only_mark_radius_reaches_completed_mark_legend_and_svg(tmp_path, radius):
    rendered = _render(tmp_path, _parts(physical_radius=radius, remove_legacy=True))
    mark = next(item for item in rendered.surface.primitives
                if item.scene_id.startswith("planned:") and item.source_ref == "task")
    swatch = next(item for item in rendered.surface.primitives
                  if item.scene_id == "legend-swatch:planned")
    expected_mark = min(mark.bounds[2:]) / 2 if radius == "capsule" else radius
    expected_swatch = min(swatch.bounds[2:]) / 2 if radius == "capsule" else radius
    assert mark.corner_radius == pytest.approx(expected_mark)
    assert float(swatch.corner_radius or 0.0) == pytest.approx(expected_swatch)

    svg_mark = _svg_rect(rendered, mark.scene_id)
    svg_swatch = _svg_rect(rendered, swatch.scene_id)
    assert float(svg_mark.attrib.get("rx", 0)) == pytest.approx(expected_mark)
    assert float(svg_swatch.attrib.get("rx", 0)) == pytest.approx(expected_swatch)


def test_legacy_only_mark_radius_keeps_pre1198_scene_and_svg_bytes(tmp_path, monkeypatch):
    source_parts = sr.bundle()
    legacy_only = deepcopy(source_parts)
    planned = legacy_only["theme"]["body"]["roles"]["planned"]
    planned.pop("cornerRadius", None)
    assert "markCornerRadius" in planned
    with monkeypatch.context() as historical:
        historical.setattr(ThemeTokenView, "mark_geometry", _pre_1198_mark_geometry)
        baseline = _render(tmp_path / "baseline", source_parts)
    legacy = _render(tmp_path / "legacy-only", legacy_only)
    assert list(legacy.surface.primitives) == list(baseline.surface.primitives)
    assert scene_document(legacy.scene) == scene_document(baseline.scene)
    assert serialize_scene(legacy.scene) == serialize_scene(baseline.scene)
    assert legacy.artifact.content == baseline.artifact.content


def test_neither_radius_keeps_the_same_required_binding_error_from_render(tmp_path):
    parts = _parts(remove_legacy=True)
    with pytest.raises(RenderFailed) as error:
        _render(tmp_path, parts)
    assert error.value.code == "E_THEME_ROLE_REQUIRED"
    assert error.value.source_ref == "/body/roles/planned/markCornerRadius"
