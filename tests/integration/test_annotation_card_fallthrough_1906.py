"""Rail cards keep their declared leaders; true box exhaustion uses an explicit list."""
from __future__ import annotations

import json
from xml.etree import ElementTree
from pathlib import Path

import pytest

from chrona.presentation.layout import surface_annotations, surface_composer
from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
)
from chrona.presentation.layout.annotation_card_measurement import suffix_block_capacity
from chrona.presentation.model.render_progress import RenderProgress
from chrona.usecases.render_review import RenderFailed
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr

OBSTACLES = ["mark", "text", "label-visual", "dependency-route", "leader-route",
             "annotation-box", "port", "rule"]
BODY = "Required callout body remains complete through safe fallback."


def test_ordered_rail_capacity_reserves_unequal_suffix_only_when_stack_fits():
    # The first card is taller than the route note in the roadmap case; both
    # complete Theme frames fit in this synthetic rail.
    assert suffix_block_capacity((('route-note', 82.925), ('signoff-note', 126.35)), 623.05) == {
        "route-note": 126.35, "signoff-note": 0.0,
    }
    # True infeasibility keeps the existing candidate exhaustion path, and a
    # plot-first policy contributes no rail demand at all.
    assert suffix_block_capacity((('route-note', 300.0), ('signoff-note', 350.0)), 623.05) == {}
    assert suffix_block_capacity((), 623.05) == {}


def _candidate(candidate_id: str, connector: str) -> dict:
    return {
        "id": candidate_id,
        "region": {"kind": "slot", "source": "annotations"},
        "search": {"kind": "row-aligned"},
        "obstacles": {"classes": list(OBSTACLES)},
        "connector": {"kind": connector},
    }


def _fixture():
    source = ak.project(kinds=("risk",), text=BODY)
    parts = sr.bundle()
    sr.with_note_rail(parts, width=360)
    ak.with_view_notes(parts, source)
    kinds = {key: dict(value) for key, value in ak.KINDS.items()}
    kinds["risk"]["heading"] = "Launch window opens"
    ak.with_kind_theme(parts, kinds=kinds)
    theme = parts["theme"]["body"]
    theme["roles"]["annotation-heading"] = {
        **theme["roles"]["annotation-kind-label"],
        "fontSize": "kind-heading-size", "lineHeight": "kind-heading-line",
    }
    theme["values"].update({"kind-heading-size": {"type": "number", "value": 24},
                            "kind-heading-line": {"type": "number", "value": 1.3}})
    theme["colorBindings"]["annotation-heading.fill"] = "text"
    parts["view"]["body"]["annotations"][0]["candidates"] = [
        _candidate("preferred", "leader"),
        _candidate("declared-list", "none"),
    ]
    return source, parts


def _svg_ids(rendered):
    root = ElementTree.fromstring(rendered.artifact.content)
    return {item.get("data-scene-id"): item for item in root.iter()
            if item.get("data-scene-id")}


def _two_card_fixture(*, plot_first: bool = False):
    source = ak.project(kinds=("risk", "note"), text="Short complete card text.")
    # Give both cards the same low physical anchor; source order is the tie break.
    source["annotations"]["n0"]["anchor"]["object"] = "t2"
    source["annotations"]["n1"]["anchor"]["object"] = "t2"
    parts = sr.bundle()
    sr.with_note_rail(parts, width=360)
    ak.with_view_notes(parts, source)
    kinds = {key: dict(value) for key, value in ak.KINDS.items()}
    kinds["risk"]["heading"] = "Launch window opens"
    ak.with_kind_theme(parts, kinds=kinds)
    theme = parts["theme"]["body"]
    theme["roles"]["annotation-heading"] = {
        **theme["roles"]["annotation-kind-label"],
        "fontSize": "kind-heading-size", "lineHeight": "kind-heading-line",
    }
    theme["values"].update({"kind-heading-size": {"type": "number", "value": 24},
                            "kind-heading-line": {"type": "number", "value": 1.3}})
    theme["colorBindings"]["annotation-heading.fill"] = "text"
    parts["view"]["body"]["annotations"][0]["candidates"] = [
        *([sr.candidate("plot-first", connector="none", max_positions=1)] if plot_first else []),
        _candidate("card", "none"), _candidate("terminal-list", "none"),
    ]
    parts["view"]["body"]["annotations"][1]["candidates"] = [
        *([sr.candidate("plot-first", connector="none", max_positions=1)] if plot_first else []),
        _candidate("card", "none"), _candidate("terminal-list", "none"),
    ]
    return source, parts


def _card_extent(svg_item):
    return float(svg_item.get("y")), float(svg_item.get("height"))


def test_failed_leader_keeps_full_card_and_emits_diagnosed_hairline(tmp_path, monkeypatch):
    source, parts = _fixture()

    def fail_route_with_named_crossing(start, end, obstacles, **kwargs):
        # The provisional card overlay delegates to the shared accepted index.
        # Add a synthetic mark centered on the eventual direct hairline after
        # card placement, so only the fallback crossing query sees it.
        base = obstacles._base
        midpoint_x = (start[0] + end[0]) / 2
        midpoint_y = (start[1] + end[1]) / 2
        if not base.has("mark:synthetic-crossing"):
            base.add(SurfaceObstacle(
                "mark:synthetic-crossing", "mark", "timeline",
                ObstacleRect(midpoint_x - 2, midpoint_y - 2, midpoint_x + 2, midpoint_y + 2)))
        return None

    monkeypatch.setattr(surface_annotations, "route_annotation_candidate", fail_route_with_named_crossing)

    rendered = ak.render(tmp_path, source, parts)

    ids = {item.scene_id: item for item in rendered.surface.primitives}
    svg = _svg_ids(rendered)
    assert "annotation-box:view-n0" in ids and "annotation-box:view-n0" in svg
    assert ids["annotation-kind-text:view-n0:0"].text == "RISK · Task 0"
    assert ids["annotation-kind-text:view-n0:1"].text == "WARNING"
    assert "annotation-heading:view-n0" in ids
    assert ids["annotation-heading:view-n0"].text == "Launch window opens"
    assert BODY in ids["annotation-text:view-n0"].text
    assert ids["annotation-text:view-n0"].text_layout is not None
    assert "annotation-list:view-n0" not in ids
    assert "annotation-leader:view-n0" in ids and "annotation-leader:view-n0" in svg
    assert "annotation-kind-text:view-n0:0" in svg
    assert "annotation-kind-text:view-n0:1" in svg
    assert "annotation-heading:view-n0" in svg
    assert "annotation-text:view-n0" in svg
    assert "annotation-list:view-n0" not in svg
    heading_text = " ".join(" ".join(svg["annotation-heading:view-n0"].itertext()).split())
    body_text = " ".join(" ".join(svg["annotation-text:view-n0"].itertext()).split())
    assert heading_text == "Launch window opens"
    assert BODY in body_text
    diagnostics = [item for item in rendered.scene.diagnostics
                   if item.startswith("W_LAYOUT_ANNOTATION_LEADER_FALLBACK:")]
    assert len(diagnostics) == 1
    detail = json.loads(diagnostics[0].split(":", 1)[1])
    assert detail["annotationId"] == "view-n0"
    assert detail["candidateId"] == "preferred"
    assert detail["crossings"] == [{
        "placementId": "mark:synthetic-crossing",
        "obstacleClass": "mark",
        "regionId": "timeline",
    }]


def test_tilted_rail_hairline_reaches_paper_and_indexes_its_extension(tmp_path, monkeypatch):
    source, parts = _fixture()
    ak.with_tilt(parts, [12])
    registered = []
    original_add = SurfaceObstacleIndex.add

    def capture_leader_segments(index, obstacle):
        original_add(index, obstacle)
        if obstacle.placement_id.startswith("annotation-leader:view-n0:segment:"):
            registered.append(obstacle)

    monkeypatch.setattr(SurfaceObstacleIndex, "add", capture_leader_segments)

    def fail_route_with_named_crossing(start, end, obstacles, **kwargs):
        base = obstacles._base
        midpoint_x = (start[0] + end[0]) / 2
        midpoint_y = (start[1] + end[1]) / 2
        if not base.has("mark:synthetic-crossing"):
            base.add(SurfaceObstacle(
                "mark:synthetic-crossing", "mark", "timeline",
                ObstacleRect(midpoint_x - 2, midpoint_y - 2, midpoint_x + 2, midpoint_y + 2)))
        return None

    monkeypatch.setattr(surface_annotations, "route_annotation_candidate", fail_route_with_named_crossing)
    rendered = ak.render(tmp_path, source, parts)

    primitives = {item.scene_id: item for item in rendered.surface.primitives}
    leader = primitives["annotation-leader:view-n0"]
    frame = primitives["annotation-box:view-n0"]
    assert frame.symbol is not None
    assert len(leader.points) >= 3
    extension = (leader.points[-2], leader.points[-1])
    assert extension[0] != extension[1]

    outline_points = tuple(point for command in frame.symbol.outline for point in command.points)
    outline_edges = tuple(zip(outline_points, (*outline_points[1:], outline_points[0])))

    def lies_on_segment(point, start, end):
        dx, dy = end[0] - start[0], end[1] - start[1]
        cross = (point[0] - start[0]) * dy - (point[1] - start[1]) * dx
        dot = (point[0] - start[0]) * dx + (point[1] - start[1]) * dy
        return abs(cross) <= 1e-6 and -1e-6 <= dot <= dx * dx + dy * dy + 1e-6

    assert any(lies_on_segment(leader.points[-1], start, end)
               for start, end in outline_edges)
    assert any(isinstance(item.geometry, ObstacleSegment)
               and (item.geometry.start, item.geometry.end) == extension
               for item in registered)

    diagnostic = next(item for item in rendered.scene.diagnostics
                      if item.startswith("W_LAYOUT_ANNOTATION_LEADER_FALLBACK:"))
    detail = json.loads(diagnostic.split(":", 1)[1])
    crossings = {item["placementId"] for item in detail["crossings"]}
    assert "mark:synthetic-crossing" in crossings
    assert "annotation-box:view-n0" not in crossings


def test_blocked_card_reaches_explicit_list_with_complete_body_once(tmp_path, monkeypatch):
    source, parts = _fixture()
    monkeypatch.setattr(surface_annotations, "annotation_rail_candidates", lambda *args, **kwargs: ())
    monkeypatch.setattr(surface_annotations, "route_annotation_candidate", lambda *args, **kwargs: None)

    rendered = ak.render(tmp_path, source, parts)

    ids = {item.scene_id: item for item in rendered.surface.primitives}
    svg = _svg_ids(rendered)
    assert "annotation-list:view-n0" in ids and "annotation-list:view-n0" in svg
    assert "annotation-box:view-n0" not in ids
    visible_text = " ".join(" ".join(" ".join(element.itertext()).split()) for element in svg.values())
    assert visible_text.count(BODY) == 1
    overflow = [item for item in rendered.surface.fit_warnings
                if item.placement_id == "annotation-list:view-n0"]
    assert len(overflow) == 1 and overflow[0].behaviour == "visible-overflow"


def test_no_terminal_list_keeps_required_fallback_error(tmp_path, monkeypatch):
    source, parts = _fixture()
    parts["view"]["body"]["annotations"][0]["candidates"] = [_candidate("preferred", "leader")]
    monkeypatch.setattr(surface_annotations, "annotation_rail_candidates", lambda *args, **kwargs: ())
    monkeypatch.setattr(surface_annotations, "route_annotation_candidate", lambda *args, **kwargs: None)

    with pytest.raises(RenderFailed) as failure:
        ak.render(tmp_path, source, parts)

    assert failure.value.code == "E_LAYOUT_ANNOTATION_FALLBACK_REQUIRED"


def test_bottom_anchored_unequal_cards_reserve_suffix_and_progress_is_byte_stable(tmp_path, monkeypatch):
    source, parts = _two_card_fixture()
    (tmp_path / "quiet").mkdir()
    (tmp_path / "progress").mkdir()
    quiet = ak.render(tmp_path / "quiet", source, parts)
    quiet_svg = _svg_ids(quiet)
    first_y, first_height = _card_extent(quiet_svg["annotation-box:view-n0"])
    second_y, second_height = _card_extent(quiet_svg["annotation-box:view-n1"])
    assert first_height != second_height
    assert first_y + first_height <= second_y
    assert "annotation-list:view-n0" not in quiet_svg
    assert "annotation-list:view-n1" not in quiet_svg

    events = []
    progress = RenderProgress(events.append)
    request_type = ak.RenderRequest
    monkeypatch.setattr(ak, "RenderRequest", lambda **kwargs: request_type(**kwargs, progress=progress))
    observed = ak.render(tmp_path / "progress", source, parts)
    assert observed.artifact.content == quiet.artifact.content
    assert events


def test_plot_first_cards_do_not_reserve_rail_capacity(tmp_path, monkeypatch):
    source, parts = _two_card_fixture(plot_first=True)
    monkeypatch.setattr(surface_annotations, "nearest_free_box", lambda *args, **kwargs: (None, 0))

    def bottom_first(annotation, resolved, *, text_size, rail, connector_kind="leader", **kwargs):
        width, height = text_size
        positions = []
        y = rail.bottom - height
        while y >= rail.y:
            positions.append(surface_annotations.AnnotationBox(
                resolved,
                surface_annotations.LabelPlacement(
                    "rail", surface_annotations.LabelRect(rail.x, y, width, height),
                    width > rail.width),
                connector_kind == "leader"))
            y -= height
        return tuple(positions)

    monkeypatch.setattr(surface_annotations, "annotation_rail_candidates", bottom_first)

    rendered = ak.render(tmp_path, source, parts)

    svg = _svg_ids(rendered)
    # Failed plot-first candidates fall through to the rail greedily; that
    # policy must not receive capacity reserved for the later card rung.
    assert "annotation-box:view-n0" in svg
    assert "annotation-list:view-n1" in svg, sorted(svg)


def test_card_source_witness_keeps_visual_identity_and_text_allocation(tmp_path, monkeypatch):
    source, parts = _two_card_fixture()
    parts["view"]["body"]["visuals"] = [{
        "target": {"kind": "annotation", "id": "view-n0"},
        "ref": "material:10k-outline-rounded", "decorative": True, "side": "leading",
    }]
    material = next(parent for parent in Path(__file__).resolve().parents
                    if (parent / "pyproject.toml").is_file()
                    ) / "src/chrona/resources/icons/material-symbols-outline-rounded-v2026-09-22.yaml"
    captured = []
    original = surface_composer.complete_route_annotations

    def capture(*args, **kwargs):
        batch = original(*args, **kwargs)
        captured.append(batch)
        return batch

    monkeypatch.setattr(surface_composer, "complete_route_annotations", capture)
    rendered = ak.render(tmp_path, source, parts, catalogs=(material,),
                         visual_profile="chrona-output/visual/v0.7-svg")
    card = next(item for batch in captured for item in batch.source_consumers if item.disposition == "card")
    assert len(card.text) >= 1
    assert all(item.available_inline is not None for item in card.text)
    visual_witness = card.treatment[3][-1]
    assert len(visual_witness) == 1
    assert visual_witness[0][:3] == ("/body/visuals/0", "material:10k-outline-rounded", "leading")
    assert visual_witness[0][3] and visual_witness[0][4]
    assert card.text[-1].available_inline == card.text[-1].measurement.inline_size


def test_tilted_card_source_witness_keeps_intrinsic_text(tmp_path, monkeypatch):
    source, parts = _two_card_fixture()
    ak.with_tilt(parts, [7])
    captured = []
    original = surface_composer.complete_route_annotations

    def capture(*args, **kwargs):
        batch = original(*args, **kwargs)
        captured.append(batch)
        return batch

    monkeypatch.setattr(surface_composer, "complete_route_annotations", capture)
    rendered = ak.render(tmp_path, source, parts)
    card = next(item for batch in captured for item in batch.source_consumers if item.disposition == "card")
    body = next(item for item in rendered.surface.primitives
                if item.scene_id == "annotation-text:view-n0")
    assert card.text[-1].measurement.inline_size < body.bounds[2]
