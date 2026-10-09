"""Theme-resolved View colour scales paint axis bands by natural interval identity (#490)."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from chrona.presentation.scene.serialization import scene_document
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr


WINDOW = {"mode": "explicit", "start": "2026-01-01", "end": "2026-07-01"}
SLOTS = {
    "parity": {"0": "band-blue", "1": "band-gold"},
    "quarters": {"0": "band-violet", "1": "band-orange"},
    "same": {"0": "band-blue", "1": "band-blue"},
}
COLORS = {
    "band-blue": "#2166AC", "band-gold": "#F4C95D",
    "band-violet": "#7353BA", "band-orange": "#E8793E",
}


def _source() -> dict:
    return sr.project({
        "launch": sr.span("launch", date(2026, 1, 1), 160, title="Synthetic launch window"),
    })


def _parts(*, tiers: list[dict] | None = None, scales: dict | None = None) -> dict:
    parts = sr.bundle("executive-light")
    body = parts["view"]["body"]
    body["window"] = dict(WINDOW)
    if tiers is not None:
        body["axis"] = {"tiers": deepcopy(tiers)}
    if scales is not None:
        theme = parts["theme"]["body"]
        theme["colorScales"] = {
            scale_id: {"slots": dict(mapping)} for scale_id, mapping in scales.items()
        }
        parts["scheme"]["body"]["categories"].update(COLORS)
    return parts


def _alternating_tiers(scale="alternating") -> list[dict]:
    return [{"unit": "month", "every": 1, "role": "band",
             "fillScale": {"scale": scale, "key": "alternating"}}]


def _month_quarter_tiers(*, child_scale="month-parent", parent_scale="quarters") -> list[dict]:
    # The finer tier deliberately references a later declaration; indices remain the natural
    # interval identities even when the window clips the first/last interval.
    return [
        {"unit": "month", "every": 1, "role": "band",
         "fillScale": {"scale": child_scale, "key": "interval", "containingTier": 2}},
        {"unit": "month", "every": 1, "role": "labels",
         "label": {"form": "short-month", "align": "start", "overflow": "thin-with-record",
                   "orientation": "horizontal"}},
        {"unit": "quarter", "every": 1, "role": "band",
         "fillScale": {"scale": parent_scale, "key": "interval"}},
        {"unit": "quarter", "every": 1, "role": "labels",
         "label": {"form": "year-quarter", "align": "center", "overflow": "visible-overflow",
                   "orientation": "horizontal"}},
    ]


def _render(tmp_path, parts):
    return sr.render(tmp_path, _source(), presentation=parts)


def _bands(rendered):
    return {item.scene_id: item for item in rendered.surface.primitives
            if item.scene_id.startswith("axis-band-rect:")}


def _svg_bands(rendered):
    root = ET.fromstring(rendered.artifact.content)
    return {node.attrib["data-scene-id"]: node for node in root.iter()
            if node.attrib.get("data-scene-id", "").startswith("axis-band-rect:")}


def test_alternating_uses_natural_ordinal_parity_in_scene_and_emitted_svg(tmp_path):
    parts = _parts(tiers=_alternating_tiers(), scales={"alternating": SLOTS["parity"]})
    rendered = _render(tmp_path, parts)
    bands, svg_bands = _bands(rendered), _svg_bands(rendered)
    assert tuple(bands) == tuple(f"axis-band-rect:0:{index}" for index in range(6))
    expected = tuple(COLORS[SLOTS["parity"][str(index % 2)]] for index in range(6))
    assert tuple(item.paint.fill for item in bands.values()) == expected
    assert tuple(node.attrib["fill"] for node in svg_bands.values()) == expected


def test_months_inherit_the_exact_later_declared_quarter_parent_and_emit_both_tiers(tmp_path):
    parts = _parts(tiers=_month_quarter_tiers(), scales={
        "month-parent": SLOTS["quarters"], "quarters": SLOTS["quarters"],
    })
    rendered = _render(tmp_path, parts)
    bands, svg_bands = _bands(rendered), _svg_bands(rendered)
    month = tuple(bands[f"axis-band-rect:0:{index}"].paint.fill for index in range(6))
    quarter = tuple(bands[f"axis-band-rect:2:{index}"].paint.fill for index in range(2))
    expected = (COLORS["band-violet"],) * 3 + (COLORS["band-orange"],) * 3
    assert month == expected
    assert quarter == (COLORS["band-violet"], COLORS["band-orange"])
    assert tuple(svg_bands[f"axis-band-rect:0:{index}"].attrib["fill"] for index in range(6)) == expected
    assert tuple(svg_bands[f"axis-band-rect:2:{index}"].attrib["fill"] for index in range(2)) == quarter
    assert {item.scene_id for item in bands.values()} == set(svg_bands)


def test_domain_separability_warning_is_reported_for_mapping_not_repeated_cells(tmp_path):
    rendered = _render(tmp_path, _parts(tiers=_alternating_tiers("same"), scales={"same": SLOTS["same"]}))
    assert len(_bands(rendered)) == 6
    assert [(item.first, item.second) for item in rendered.scale_collisions] == [("0", "1")]
    assert any(item.startswith("W_PRESENTATION_SCALE_NOT_SEPARABLE:same:0:1")
               for item in rendered.scene.diagnostics)


@pytest.mark.parametrize("treatment", ["none", "outline", "gradient"])
def test_fill_scale_rejects_targets_without_a_solid_fill(treatment, tmp_path):
    parts = _parts(tiers=_alternating_tiers(), scales={"alternating": SLOTS["parity"]})
    body = parts["theme"]["body"]
    role = body["roles"]["axis-band-decoration"]
    if treatment in {"none", "outline"}:
        role["backgroundTreatment"] = treatment
    else:
        body["values"].update({
            "axis-gradient-angle": {"type": "number", "value": 0},
        })
        role.update({"gradientAngle": "axis-gradient-angle"})
        body["colorBindings"].update({
            "axis-band-decoration.gradientStart": "category:band-blue",
            "axis-band-decoration.gradientEnd": "category:band-gold",
        })
    with pytest.raises(RenderFailed) as failure:
        _render(tmp_path, parts)
    assert failure.value.code == "E_PRESENTATION_AXIS_SCALE_TARGET"
    assert failure.value.source_ref == "/view/body/axis/tiers/0/fillScale"


def test_missing_exact_slot_mapping_has_stable_scale_mapping_diagnostic(tmp_path):
    parts = _parts(tiers=_alternating_tiers(), scales={"alternating": {"0": "band-blue"}})
    with pytest.raises(RenderFailed) as failure:
        _render(tmp_path, parts)
    assert failure.value.code == "E_PRESENTATION_SCALE_MAPPING"
    assert failure.value.source_ref == "/view/body/axis/tiers/0/fillScale"


def test_an_unused_declared_scale_leaves_scene_and_svg_bytes_unchanged(tmp_path):
    (tmp_path / "unused").mkdir()
    baseline = _render(tmp_path, _parts())
    unused = _render(tmp_path / "unused", _parts(scales={"unused": SLOTS["parity"]}))
    assert unused.artifact.content == baseline.artifact.content
    assert scene_document(unused.scene)["surfaces"] == scene_document(baseline.scene)["surfaces"]
