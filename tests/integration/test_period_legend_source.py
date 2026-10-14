"""Source-bound period legend entries retain independent identity through a public render."""
from __future__ import annotations

from datetime import date
import xml.etree.ElementTree as ET
from pathlib import Path
from copy import deepcopy

import pytest

from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
STARTER_CATALOG = ROOT / "src/chrona/resources/icons/chrona-theme-starter-v2026-10-09.yaml"


def _render(directory, entries=None, *, treatment="fill", wording=False, slot=True,
            preset="executive-light", pattern=False, catalogs=(), variant=None):
    directory.mkdir()
    parts = sr.bundle(preset)
    theme = parts["theme"]["body"]
    theme["colorBindings"].pop("period-band.fill", None)
    theme["colorBindings"].pop("period-band.stroke", None)
    theme["values"]["legend-period-edge-width"] = {"type": "number", "value": 1}
    band_role = {"backgroundTreatment": treatment, "backgroundPaintOrder": 11}
    if treatment != "none":
        band_role.update({"opacity": "opacity.axis-band", "edgeRules": {"top": "single"},
                          "strokeWidth": "legend-period-edge-width"})
    if pattern:
        band_role["pattern"] = "starter-halftone"
    theme["roles"]["period-band"] = band_role
    if treatment == "fill":
        theme["colorBindings"]["period-band.fill"] = "accent"
    if treatment != "none":
        theme["colorBindings"]["period-band.stroke"] = "text"
    theme["roles"]["legend-swatch"] = {"swatchInlineSize": "legend-swatch-width",
                                         "swatchBlockSize": "legend-swatch-height"}
    theme["values"]["legend-swatch-width"] = {"type": "number", "value": 22}
    theme["values"]["legend-swatch-height"] = {"type": "number", "value": 12}
    parts["view"]["body"]["window"] = {
        "mode": "explicit", "start": "2026-01-01", "end": "2026-04-01"}
    parts["view"]["body"]["periods"] = [
        {"id": "launch", **({"variant": variant} if variant else {})}, {"id": "handoff"}]
    if variant:
        theme["roles"][f"period-band:{variant}"] = deepcopy(band_role)
        if treatment == "fill":
            theme["colorBindings"][f"period-band:{variant}.fill"] = "accent"
        if treatment != "none":
            theme["colorBindings"][f"period-band:{variant}.stroke"] = "text"
    if wording:
        parts["view"]["body"]["wording"] = {"legend": {"period-band": "Shared period"}}
    if not slot:
        def without_legend(node):
            children = node.get("children")
            if not isinstance(children, list):
                return
            node["children"] = [child for child in children if child.get("id") != "legend"]
            for child in node["children"]:
                without_legend(child)
        without_legend(parts["layout"]["root"])
    source = sr.project({"a": sr.span("a", date(2026, 1, 5), 40)})
    source["periods"] = {
        "launch": {"start": "2026-01-10", "end": "2026-02-10"},
        "handoff": {"start": "2026-02-10", "end": "2026-03-10"},
    }
    detail = {"version": "chrona/review-detail-profile/v0.1", "id": "period-legend",
              "body": {"legend": entries if entries is not None else [
                  {"role": "period-band", "label": "Launch", "sourceRef": "launch"},
                  {"role": "period-band", "label": "Handoff", "sourceRef": "handoff"},
                  *([{"role": "period-band", "label": "All periods"}]
                    if treatment == "fill" else []),
              ]}}
    return sr.render(directory, source, presentation=parts, detail=detail, icon_catalogs=tuple(catalogs))


@pytest.mark.parametrize("treatment", ("fill", "outline"))
def test_selected_period_legend_entries_keep_source_identity_and_reuse_edge_decoration(tmp_path, treatment):
    rendered = _render(tmp_path / "render", treatment=treatment)
    primitives = rendered.surface.primitives
    ids = {item.scene_id for item in primitives}

    assert {"legend-period:launch", "legend-period:handoff"} <= ids
    if treatment == "fill":
        assert "legend:period-band" in ids
    if treatment == "fill":
        assert {"legend-period-swatch:launch", "legend-period-swatch:handoff"} <= ids
    for period_id in ("launch", "handoff"):
        host_id = f"legend-period-swatch:{period_id}"
        edge_id = f"period-edge:{len(host_id)}:{host_id}:top:0"
        edge = next(item for item in primitives if item.scene_id == edge_id)
        assert edge.source_ref == period_id
        assert edge.visual_role == "period-band"
        assert edge.paint.fill is None and edge.paint.stroke
        if treatment == "fill":
            host = next(item for item in primitives if item.scene_id == f"legend-period-swatch:{period_id}")
            assert host.source_ref == period_id
            assert host.visual_role == "period-band"
            assert host.paint.fill and host.paint.stroke is None
            assert host.bounds[2:] == (22.0, 12.0)
        else:
            assert f"legend-period-swatch:{period_id}" not in ids

    labels = {item.scene_id: item for item in primitives if item.scene_id.startswith("legend-period:")}
    assert labels["legend-period:launch"].source_ref == "launch"
    assert labels["legend-period:handoff"].source_ref == "handoff"
    svg = ET.fromstring(rendered.artifact.content)
    svg_nodes = {node.get("data-scene-id"): node for node in svg.iter()
                 if node.get("data-scene-id") is not None}
    for period_id in ("launch", "handoff"):
        assert f"legend-period:{period_id}" in svg_nodes
        if treatment == "fill":
            assert f"legend-period-swatch:{period_id}" in svg_nodes
        assert edge_id in svg_nodes


def test_period_legend_role_wording_overrides_sourced_and_unsourced_labels(tmp_path):
    rendered = _render(tmp_path / "render", wording=True)
    texts = {item.scene_id: item for item in rendered.surface.primitives if item.scene_id.startswith("legend")}

    assert texts["legend-period:launch"].text == "Shared period"
    assert texts["legend-period:handoff"].text == "Shared period"
    assert texts["legend:period-band"].text == "Shared period"


def test_none_period_role_keeps_sourced_labels_and_their_swatch_reservation(tmp_path):
    entries = [{"role": "period-band", "label": "Launch", "sourceRef": "launch"},
               {"role": "period-band", "label": "Handoff", "sourceRef": "handoff"}]
    painted = _render(tmp_path / "painted", entries)
    absent = _render(tmp_path / "absent", entries, treatment="none")
    painted_text = {item.scene_id: item for item in painted.surface.primitives
                    if item.scene_id.startswith("legend-period:")}
    absent_text = {item.scene_id: item for item in absent.surface.primitives
                   if item.scene_id.startswith("legend-period:")}

    assert set(absent_text) == set(painted_text) == {"legend-period:launch", "legend-period:handoff"}
    assert all(absent_text[key].bounds == painted_text[key].bounds for key in absent_text)
    assert not any(item.scene_id.startswith("legend-period-swatch:") for item in absent.surface.primitives)


def test_period_entries_emit_no_legend_primitives_when_layout_has_no_legend_slot(tmp_path):
    rendered = _render(tmp_path / "render", slot=False)

    assert not any(item.slot_id == "legend" for item in rendered.surface.primitives)


def test_patterned_sourced_swatch_keeps_pattern_ink_and_clips_to_the_reserved_area(tmp_path):
    rendered = _render(tmp_path / "render", preset="technical-print", pattern=True,
                       catalogs=(STARTER_CATALOG,))
    host = next(item for item in rendered.surface.primitives
                if item.scene_id == "legend-period-swatch:launch")

    assert host.pattern is not None and host.pattern.primitives
    assert host.paint.fill is not None and host.paint.stroke is not None
    assert tuple(host.pattern.region_bounds) == pytest.approx(host.bounds)
    assert tuple(host.pattern.clip_bounds) == pytest.approx(host.bounds)


def test_patterned_variant_sourced_swatch_matches_chart_pattern_payload(tmp_path):
    rendered = _render(
        tmp_path / "render",
        entries=[{"role": "period-band:release", "label": "Launch", "sourceRef": "launch"},
                 {"role": "period-band", "label": "Handoff", "sourceRef": "handoff"}],
        preset="technical-print", pattern=True, catalogs=(STARTER_CATALOG,), variant="release")
    chart_band = next(item for item in rendered.surface.primitives if item.scene_id == "period-band:launch")
    legend_swatch = next(item for item in rendered.surface.primitives
                         if item.scene_id == "legend-period-swatch:launch")

    assert chart_band.visual_role == legend_swatch.visual_role == "period-band:release"
    assert chart_band.paint.fill == legend_swatch.paint.fill
    assert chart_band.paint.stroke == legend_swatch.paint.stroke
    assert chart_band.pattern is not None and legend_swatch.pattern is not None
    assert chart_band.pattern.primitives == legend_swatch.pattern.primitives


@pytest.mark.parametrize(("entries", "code", "pointer"), [
    ([{"role": "period-band", "label": "Missing", "sourceRef": "unselected"}],
     "E_REVIEW_LEGEND_PERIOD_SOURCE", "/body/legend/0/sourceRef"),
    ([{"role": "period-band:wrong", "label": "Launch", "sourceRef": "launch"}],
     "E_REVIEW_LEGEND_PERIOD_ROLE", "/body/legend/0/role"),
    ([{"role": "period-band", "label": "One", "sourceRef": "launch"},
      {"role": "period-band", "label": "Again", "sourceRef": "launch"}],
     "E_REVIEW_LEGEND_PERIOD_SOURCE", "/body/legend/1/sourceRef"),
])
def test_invalid_period_legend_source_is_rejected_at_the_profile_boundary(tmp_path, entries, code, pointer):
    with pytest.raises(RenderFailed) as raised:
        _render(tmp_path / "render", entries)

    assert (raised.value.code, raised.value.source_ref, raised.value.component) == (
        code, pointer, "review-detail-profile")
