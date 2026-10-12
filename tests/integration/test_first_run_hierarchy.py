"""Hierarchy rows close content, paint admission and truthful temporal ports."""
from copy import deepcopy
from datetime import date
from math import hypot
from xml.etree import ElementTree

import pytest
import yaml

from chrona.presentation.contracts import ClosureIdentity, ContractError, parse_contract
from chrona.presentation.scene.serialization import scene_document
from chrona.resources import default_preset_resource, default_preset_root
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from tests.support import synthetic_review as sr


def _view():
    preset = yaml.safe_load(default_preset_resource().read_bytes())
    return yaml.safe_load(default_preset_root().joinpath(preset["body"]["resources"]["view"]["path"]).read_bytes())


def _source():
    return sr.project({
        "root": {"type": "group", "title": "Programme", "schedule": {"mode": "rollup"}},
        "nested": {"type": "group", "title": "Subsystem", "parent": "root", "schedule": {"mode": "rollup"}},
        "a": {**sr.span("a", date(2027, 1, 4), 6), "parent": "nested"},
        "b": {**sr.span("b", date(2027, 1, 11), 9), "parent": "root"},
        "after": sr.span("after", date(2027, 2, 1), 9),
    }, [{"id": "programme-after", "type": "dependency", "from": {"object": "root", "endpoint": "end"},
         "to": {"object": "after", "endpoint": "start"}, "lag": "0d"}])


def _render(directory, source, view=None, theme=None, actual=None):
    directory.mkdir()
    path = directory / "project.yaml"
    path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")
    view_path = None
    if view is not None:
        view_path = directory / "view.yaml"
        view_path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")
    theme_path = actual_path = None
    if theme is not None:
        theme_path = directory / "theme.yaml"
        theme_path.write_text(yaml.safe_dump(theme, sort_keys=False), encoding="utf-8")
    if actual is not None:
        actual_path = directory / "actual.yaml"
        actual_path.write_text(yaml.safe_dump(actual, sort_keys=False), encoding="utf-8")
    return render_draft(DraftRenderRequest(project=path, view=view_path, theme=theme_path,
                                          actual=actual_path, target_kind="svg")).rendered


def test_default_renders_all_nested_group_headers_once(tmp_path):
    rendered = _render(tmp_path / "default", _source())
    headers = [item for item in rendered.surface.primitives if item.purpose == "group-header"]
    assert [(item.scene_id, item.text) for item in headers] == [
        ("cell:root:Task", "Programme"), ("cell:nested:Task", "Subsystem")]
    assert all(item.table_row_id is None and item.table_column_id is None for item in headers)
    assert all(item.text_layout.font_size > 0 for item in headers)
    cells = {item.scene_id: item for item in rendered.surface.primitives if item.purpose == "table-cell"}
    assert cells["cell:a:Task"].bounds[0] > headers[1].bounds[0] > headers[0].bounds[0]
    assert cells["cell:root:Plan"].text
    assert cells["cell:root:Plan"].table_row_id == "root"
    assert not any(item.scene_id.startswith((f"planned:{group}:", f"actual:{group}:",
                                            f"member-label:{group}:", f"variance:{group}:"))
                   for group in ("root", "nested") for item in rendered.surface.primitives)
    svg = ElementTree.fromstring(rendered.artifact.content)
    svg_ids = {element.get("data-scene-id", element.get("id")) for element in svg.iter()}
    assert {item.scene_id for item in headers} <= svg_ids


@pytest.mark.parametrize("mode", ["header", "none", "bar"])
def test_rollup_modes_preserve_relation_date_ports_without_fake_painted_hosts(tmp_path, mode):
    view = _view()
    view["body"]["grouping"]["rollup"] = mode
    theme = None
    if mode == "bar":
        preset = yaml.safe_load(default_preset_resource().read_bytes())
        theme = yaml.safe_load(default_preset_root().joinpath(preset["body"]["resources"]["theme"]["path"]).read_bytes())
        # The default selects headers and does not promise a summary-bar role.
        # Supply that existing role explicitly when testing the bar policy.
        theme["body"]["roles"]["summary-bar"] = {"markHeight": theme["body"]["roles"]["planned"]["markHeight"]}
        theme["body"]["colorBindings"]["summary-bar.fill"] = theme["body"]["colorBindings"]["planned.stroke"]
    rendered = _render(tmp_path / mode, _source(), view, theme)
    root_marks = [item for item in rendered.surface.primitives
                  if item.scene_id.startswith("planned:root:")]
    assert bool(root_marks) == (mode == "bar")
    assert any(item.scene_id == "summary-bar:root" for item in rendered.surface.primitives) == (mode == "bar")
    assert any(item.scene_id == "cell:root:Task" and item.purpose == "group-header"
               for item in rendered.surface.primitives) == (mode == "header")
    if mode != "bar":
        assert not any(item.scene_id.startswith(("member-label:root:", "variance:root:"))
                       for item in rendered.surface.primitives)
    route = next(item for item in rendered.surface.primitives
                 if item.source_kind == "relation" and item.from_instance_id == "root:root")
    last_child = next(item for item in rendered.surface.primitives if item.scene_id == "planned:b:b")
    # The round source marker is centred at the temporal port; its painted
    # tangent, not its centre, is the first completed line point.
    start, following = route.points[:2]
    dx, dy = following[0] - start[0], following[1] - start[1]
    marker = route.marker_start
    assert marker is not None
    offset = marker.head_length - marker.attachment_offset - marker.head_length / 2
    centre = (start[0] - dx / hypot(dx, dy) * offset,
              start[1] - dy / hypot(dx, dy) * offset)
    assert centre[0] == pytest.approx(last_child.bounds[0] + last_child.bounds[2])
    root_row = next(row for row in rendered.surface.rows if row.row_id == "root")
    assert root_row.bounds[1] <= centre[1] <= root_row.bounds[1] + root_row.bounds[3]
    assert not any("E_SCENE_RELATION_THROUGH_MARK" in code for code in rendered.surface.diagnostics)


def test_clipped_unpainted_endpoint_is_not_replaced_by_a_window_edge(tmp_path):
    view = _view()
    view["body"]["window"] = {"mode": "explicit", "start": "2027-01-01", "end": "2027-01-15"}
    rendered = _render(tmp_path / "clipped", _source(), view)
    assert not any(item.source_kind == "relation" and item.from_instance_id == "root:root"
                   for item in rendered.surface.primitives)
    assert any(code.startswith("W_LAYOUT_RELATION_SUPPRESSED:relation:")
               for code in rendered.surface.diagnostics)


def test_header_actual_progress_and_delta_do_not_leak_temporal_paint(tmp_path):
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observations",
              "body": {"asOf": "2027-01-25", "observations": [
                  {"id": "root-progress", "sequence": 1, "projectObjectId": "root",
                   "actual": {"start": "2027-01-04", "finish": "2027-01-22", "progress": 0.5}},
              ]}}
    rendered = _render(tmp_path / "actual", _source(), actual=actual)
    assert any(item.scene_id == "cell:root:Task" for item in rendered.surface.primitives)
    assert not any(item.scene_id.startswith(("planned:root:", "actual:root:", "progress-fill:actual:root:",
                                            "variance:root:", "member-label:root:"))
                   for item in rendered.surface.primitives)


@pytest.mark.parametrize("with_actual", [False, True])
def test_flat_complete_scene_and_svg_are_unchanged_by_hierarchy_policy(tmp_path, with_actual):
    source = sr.project({"b": sr.span("b", date(2027, 2, 1), 9),
                         "a": sr.span("a", date(2027, 1, 4), 6)})
    actual = ({"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observations",
               "body": {"asOf": "2027-01-07", "observations": [
                   {"id": "a-progress", "sequence": 1, "projectObjectId": "a",
                    "actual": {"start": "2027-01-04", "openUntil": "asOf", "progress": 0.5}},
               ]}} if with_actual else None)
    default = _render(tmp_path / "hierarchy", source, actual=actual)
    previous_view = _view()
    previous_view["body"]["grouping"] = {"by": "none"}
    previous_view["body"].pop("hierarchyColumn")
    previous = _render(tmp_path / "flat", source, previous_view, actual=actual)
    documents = [deepcopy(scene_document(rendered.scene)) for rendered in (default, previous)]
    for document in documents:
        document.pop("provenance")
    assert documents[0] == documents[1]
    assert default.artifact.content == previous.artifact.content


@pytest.mark.parametrize("depth", [0, 1, 4, "all"])
def test_depth_ingress_preserves_finite_or_all_policy(depth):
    view = _view()
    view["body"]["grouping"]["depth"] = depth
    parsed = parse_contract(ClosureIdentity("view", view["id"], "test", "sha256:" + "a" * 64), view)
    assert parsed.view.grouping.depth == depth


@pytest.mark.parametrize("depth", [-1, True, None, "unlimited", 1.5])
def test_depth_ingress_rejects_other_values(depth):
    view = _view()
    view["body"]["grouping"]["depth"] = depth
    with pytest.raises(ContractError):
        parse_contract(ClosureIdentity("view", view["id"], "test", "sha256:" + "a" * 64), view)
