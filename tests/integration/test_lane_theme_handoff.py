"""Two-Theme lane membership and icon handoff regression for #467 B3."""
from pathlib import Path
from dataclasses import replace
import re
import xml.etree.ElementTree as ET

import yaml
import pytest

from chrona.presentation.layout import surface_composer
from chrona.presentation.layout.labels import LabelRect
from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.presentation.scene.serialization import serialize_scene
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderRequest, render_review


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def _edge_gap(left, right):
    left_inline, left_block, left_width, left_height = left
    right_inline, right_block, right_width, right_height = right
    inline = max(0.0, left_inline - (right_inline + right_width),
                 right_inline - (left_inline + left_width))
    block = max(0.0, left_block - (right_block + right_height),
                right_block - (left_block + left_height))
    return (inline ** 2 + block ** 2) ** 0.5


def _on_perimeter(point, bounds):
    x, y = point
    inline, block, width, height = bounds
    inline_end, block_end = inline + width, block + height
    return ((abs(x - inline) < 0.01 or abs(x - inline_end) < 0.01)
            and block - 0.01 <= y <= block_end + 0.01
            or (abs(y - block) < 0.01 or abs(y - block_end) < 0.01)
            and inline - 0.01 <= x <= inline_end + 0.01)


def _assert_member_label_associations(primitives):
    marks = [item for item in primitives if item.purpose in {"planned", "actual", "snapshot"}]
    labels = [item for item in primitives if item.purpose == "member-label"]
    leaders = {item.scene_id.removeprefix("member-label-leader:"): item
               for item in primitives if item.purpose == "member-label-leader"}
    sides = set()
    for label in labels:
        host_options = [mark for mark in marks if mark.lane_row_id == label.lane_row_id
                        and mark.lane_member_id == label.lane_member_id
                        and mark.source_ref == label.source_ref]
        assert host_options, label.scene_id
        leader = leaders.get(label.scene_id)
        host = (next((mark for mark in host_options if _on_perimeter(
            leader.points[-1], mark.bounds)), None) if leader is not None else None)
        if host is None:
            host = min(host_options, key=lambda mark: _edge_gap(label.text_layout.bounds,
                                                               (mark.bounds[0], mark.bounds[1],
                                                                mark.bounds[2], mark.bounds[3])))
        host_bounds = (host.bounds[0], host.bounds[1], host.bounds[2], host.bounds[3])
        distance = _edge_gap(label.text_layout.bounds, host_bounds)
        label_inline, _label_block, label_width, _label_height = label.text_layout.bounds
        mark_inline, _mark_block, mark_width, _mark_height = host_bounds
        if label_inline >= mark_inline + mark_width:
            sides.add("end")
        elif label_inline + label_width <= mark_inline:
            sides.add("start")
        else:
            sides.add("stagger")
        if distance > 2 * label.text_layout.font_size + 0.01:
            assert leader is not None, label.scene_id
        if leader is not None:
            assert leader.scene_id == f"member-label-leader:{label.scene_id}"
            assert leader.source_ref == label.source_ref
            assert leader.lane_row_id == label.lane_row_id
            assert leader.lane_member_id == label.lane_member_id
            assert len(leader.points) >= 2
            assert _on_perimeter(leader.points[0], label.text_layout.bounds)
            assert _on_perimeter(leader.points[-1], host_bounds)
    return sides


def _theme_variant(source: Path, destination: Path, *, family: str, size: int,
                   icon_scale: int, symbol: str, stroke_width: int) -> Path:
    theme = yaml.safe_load(source.read_text(encoding="utf-8"))
    values = theme["body"]["values"]
    values["editorial"]["value"] = family
    values["text-size"]["value"] = size
    values["icon-scale"]["value"] = icon_scale
    values["milestone-symbol"]["value"]["shape"] = symbol
    values["stroke-width"]["value"] = stroke_width
    # The lane summary uses numeric typography; the source Theme predates that
    # required role, so derive it from the same Theme text treatment.
    theme["body"]["roles"]["numeric"] = dict(theme["body"]["roles"]["text"])
    destination.write_text(yaml.safe_dump(theme, sort_keys=False), encoding="utf-8")
    return destination


def test_same_lane_view_under_two_themes_reaches_identical_scene_membership(tmp_path, monkeypatch):
    root = _root()
    example = root / "examples/controller-z"
    view = yaml.safe_load((example / "views/icons.yaml").read_text(encoding="utf-8"))
    view["version"] = "chrona/view/v0.28"
    view_body = view["body"]
    view_body.pop("tableColumns", None)
    view_body["rows"] = {"mode": "lanes", "laneTable": {"label": "group", "count": True}}
    view_body["visibility"]["labels"] = {
        "placement": "plot", "content": ["title"], "side": "end", "overflow": "suppress",
    }
    # A global title icon is not lane-owned; member icons, when present, are
    # closed by the typed Layout-to-Scene inventory.
    view_body["visuals"] = [
        item for item in view_body["visuals"]
        if item.get("target", {}).get("kind") == "title" and item.get("side", "leading") == "leading"
    ]
    view_body["visuals"].append({
        "target": {"kind": "plot-label", "id": "firmware"},
        "ref": "chrona:risk", "side": "leading", "decorative": True,
    })
    view_body["visuals"].append({
        "target": {"kind": "mark", "object": "firmware", "facet": "planned"},
        "ref": "chrona:risk", "side": "leading", "decorative": True,
    })
    view_body["visuals"].append({
        "target": {"kind": "mark", "object": "firmware", "facet": "actual"},
        "ref": "chrona:risk", "side": "leading", "decorative": True,
    })
    view_path = tmp_path / "same-lane-view.yaml"
    view_path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")
    theme_source = example / "themes/executive-light.yaml"
    themes = (
        _theme_variant(theme_source, tmp_path / "theme-a.yaml", family="Noto Sans", size=11,
                       icon_scale=1, symbol="diamond", stroke_width=1),
        _theme_variant(theme_source, tmp_path / "theme-b.yaml", family="Noto Sans Mono", size=13,
                       icon_scale=1.1, symbol="circle", stroke_width=3),
    )

    outputs = []
    for theme_path in themes:
        draft = resolve_draft_render(
            project_path=example / "project.yaml",
            view_path=view_path,
            theme_path=theme_path,
            scheme_path=example / "schemes/executive-light.yaml",
            layout_path=example / "layouts/executive-review.yaml",
            actual_path=example / "actual.yaml",
            viewport=(2800, 1200),
            visual_profile="chrona-output/visual/v0.7-svg",
            icon_catalog_paths=(example / "icons.yaml",),
        )
        request = RenderRequest(
            closure=draft.closure,
            snapshot_root=draft.asset_root,
            asset_root=draft.asset_root,
            scheduler=ReferenceScheduler(),
            renderer=V05SvgRenderer(),
            draft_auto_block=draft.auto_block,
        )
        outputs.append((draft.closure, render_review(request)))

    # Exercise the full-band contact search: crowded lane marks force at least
    # one name away from its own mark by more than the direct-association bound.
    fill_layout = yaml.safe_load((example / "layouts/executive-review.yaml").read_text(encoding="utf-8"))
    fill_layout["reviewSurface"]["rowDistribution"] = "fill"
    fill_layout_path = tmp_path / "fill-lane-layout.yaml"
    fill_layout_path.write_text(yaml.safe_dump(fill_layout, sort_keys=False), encoding="utf-8")
    fill_project = yaml.safe_load((example / "project.yaml").read_text(encoding="utf-8"))
    fill_project["objects"]["firmware"]["title"] = (
        "Firmware feature complete integration readiness and operational validation")
    fill_project_path = tmp_path / "leader-project.yaml"
    fill_project_path.write_text(yaml.safe_dump(fill_project, sort_keys=False), encoding="utf-8")
    fill_draft = resolve_draft_render(
        project_path=fill_project_path, view_path=view_path,
        theme_path=themes[0], scheme_path=example / "schemes/executive-light.yaml",
        layout_path=fill_layout_path, actual_path=example / "actual.yaml",
        viewport=(2800, 1200), visual_profile="chrona-output/visual/v0.7-svg",
        icon_catalog_paths=(example / "icons.yaml",),
    )
    fill_request = RenderRequest(
        closure=fill_draft.closure, snapshot_root=fill_draft.asset_root,
        asset_root=fill_draft.asset_root, scheduler=ReferenceScheduler(),
        renderer=V05SvgRenderer(), draft_auto_block=fill_draft.auto_block,
    )
    original_member_placement = surface_composer.place_member_name
    forced = False

    def displaced_member_placement(*args, **kwargs):
        nonlocal forced
        result = original_member_placement(*args, **kwargs)
        if result is not None and not forced:
            bounds = kwargs["bounds"]
            up_room = result.bounds.y - bounds.y
            down_room = bounds.bottom - result.bounds.bottom
            displacement = min(60.0, max(up_room, down_room))
            if displacement > 0:
                delta = displacement if down_room >= up_room else -displacement
                result = replace(result, bounds=LabelRect(
                    result.bounds.x, result.bounds.y + delta,
                    result.bounds.width, result.bounds.height))
                forced = True
        return result

    monkeypatch.setattr(surface_composer, "place_member_name", displaced_member_placement)
    fill_output = render_review(fill_request)
    assert forced

    first_closure, first = outputs[0]
    second_closure, second = outputs[1]
    assert first_closure.project.identity == second_closure.project.identity
    assert first_closure.view.identity == second_closure.view.identity
    assert first_closure.resource("theme").content_identity != second_closure.resource("theme").content_identity

    first_members = {(item.row_id, item.member_id) for item in first.surface.lane_members}
    second_members = {(item.row_id, item.member_id) for item in second.surface.lane_members}
    assert first_members and first_members == second_members

    first_primitives = {item.scene_id: item for item in first.surface.primitives}
    second_primitives = {item.scene_id: item for item in second.surface.primitives}
    first_sides = _assert_member_label_associations(first.surface.primitives)
    second_sides = _assert_member_label_associations(second.surface.primitives)
    assert first_sides == second_sides
    assert "end" in first_sides
    fill_primitives = fill_output.surface.primitives
    _assert_member_label_associations(fill_primitives)
    leaders = [item for item in fill_primitives if item.purpose == "member-label-leader"]
    assert leaders
    assert b'"class":"leader-route"' in serialize_scene(fill_output.scene)
    svg_root = ET.fromstring(fill_output.artifact.content)
    svg_leaders = {node.attrib.get("data-scene-id"): node for node in svg_root.iter()
                   if node.attrib.get("data-scene-id")}
    for leader in leaders:
        node = svg_leaders[leader.scene_id]
        assert node.tag.endswith("path") and node.attrib.get("data-source-ref") == leader.source_ref
        values = [float(value) for value in re.findall(
            r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?", node.attrib["d"])]
        assert values[:2] == pytest.approx(leader.points[0])
        assert values[-2:] == pytest.approx(leader.points[-1])
    label_ids = {identifier for identifier in first_primitives if identifier.startswith("member-label:")}
    other_label_ids = {identifier for identifier in second_primitives if identifier.startswith("member-label:")}
    assert label_ids and label_ids == other_label_ids
    assert all(not any(item.startswith("W_LAYOUT_LABEL_SUPPRESSED:member-label:")
                       for item in output.scene.diagnostics) for output in (first, second))
    for identifier in label_ids:
        left, right = first_primitives[identifier], second_primitives[identifier]
        assert left.text == right.text
        assert left.text_layout.family != right.text_layout.family
        assert left.text_layout.font_size != right.text_layout.font_size
        assert left.text_layout.bounds[2] != right.text_layout.bounds[2]

    icon_ids = {identifier for identifier, item in first_primitives.items() if item.kind == "Icon"}
    assert icon_ids and icon_ids <= second_primitives.keys()
    assert "visual:title:leading" in icon_ids
    assert first_primitives["visual:title:leading"].lane_row_id is None
    member_icon_ids = icon_ids - {"visual:title:leading"}
    assert member_icon_ids
    assert all(first_primitives[item].lane_row_id is not None for item in member_icon_ids)
    assert member_icon_ids == {
        "visual:" + identifier + (":leading" if identifier.startswith("member-label:") else "")
        for identifier, primitive in first_primitives.items()
        if primitive.source_ref == "firmware"
        and (identifier.startswith("member-label:") or primitive.purpose in {"planned", "actual"})
    }
    assert all(first_primitives[item].lane_member_id == "firmware" for item in member_icon_ids)
    assert any(first_primitives[item].bounds != second_primitives[item].bounds for item in icon_ids)

    planned_ids = {identifier for identifier, item in first_primitives.items() if item.purpose == "planned"}
    assert planned_ids and planned_ids <= second_primitives.keys()
    assert any(first_primitives[item].paint.stroke_width != second_primitives[item].paint.stroke_width
               for item in planned_ids)

    first_symbols = tuple(item.symbol.outline for item in first.surface.primitives if item.symbol is not None)
    second_symbols = tuple(item.symbol.outline for item in second.surface.primitives if item.symbol is not None)
    assert first_symbols != second_symbols
