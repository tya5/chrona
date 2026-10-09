"""#849: actual Yuya YAML transports the exact ordered tile through both gates."""
from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility
from chrona.usecases.materialize import MaterializationError
from tools.materialize_example import materialize


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def test_yuya_launch_window_emits_exact_seigaiha_and_reports_visible_density(tmp_path):
    output = tmp_path / "yuya"
    try:
        materialize(ROOT / "examples/halcyon-1/manifest.yaml", "yuya", output, write=False)
    except MaterializationError as error:
        # Source-only PRs use a CI-owned generated snapshot. Before that snapshot
        # is installed, the intended new picture differs from main's old evidence.
        # Rendering/closure failures are never accepted here; public byte checking
        # remains a separate required release gate.
        assert error.code == "E_MATERIALIZER_MISMATCH"

    document = json.loads((output / "review.scene.json").read_bytes())
    band = next(p for s in document["surfaces"] for p in s["primitives"]
                if p["id"] == "period-band:launch-window")
    expected = [
        {"kind": "circle", "cx": cx, "cy": cy, "radius": radius,
         "fillChannel": "substrate" if radius == 10 else "none", "strokeWidth": 0.8}
        for cx, cy in ((0, 10), (20, 10), (10, 5)) for radius in (10, 7, 4)
    ]
    pattern = band["pattern"]
    assert pattern["primitives"] == expected
    assert (pattern["tileInlineSize"], pattern["tileBlockSize"], pattern["densityBasisPoints"]) == (20, 10, 2606)
    assert pattern["regionBounds"] == pattern["clipBounds"] == band["bounds"]

    svg = ElementTree.parse(output / "review.svg").getroot()
    ns = {"s": "http://www.w3.org/2000/svg"}
    tile = next(p for p in svg.findall(".//s:pattern", ns)
                if len(p.findall("s:circle", ns)) == 9)
    assert (tile.get("width"), tile.get("height")) == ("20", "10")
    for emitted, source in zip(tile.findall("s:circle", ns), expected, strict=True):
        assert [float(emitted.get(k)) for k in ("cx", "cy", "r")] == [source[k] for k in ("cx", "cy", "radius")]
        assert emitted.get("fill") == (band["paint"]["fill"] if source["fillChannel"] == "substrate" else "none")
        assert emitted.get("stroke") == band["paint"]["stroke"]
        assert float(emitted.get("stroke-width")) == 0.8

    contrast = [f for f in evaluate_scene_contrast(document) if f.primitive_id == band["id"]]
    assert contrast and all(f.density_basis_points == 2606 for f in contrast)
    assert all(f.floor == 1.1 for f in contrast)
    perceptibility = next(f for f in evaluate_scene_perceptibility(document)
                          if f.code == "I_SCENE_PATTERN_PERCEPTIBILITY" and band["id"] in f.primitive_ids)
    assert dict(perceptibility.measured_facts)["densityBasisPoints"] == 2606
