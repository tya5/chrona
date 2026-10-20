from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

import pytest
import yaml

from chrona.presentation.scene.serialization import SceneSerializationError, serialize_scene
from chrona.presentation.layout.relation_hints import propose_hint
from chrona.presentation.layout.surface_quality import MarkerGeometry, PathCommand
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from chrona.usecases.previous_scene import _hint_marks, decode_previous_scene
from chrona.core.ports import SnapshotReadError
from chrona.presentation.contracts import ArtifactPin, freeze
from chrona.presentation.model.closure import ClosureError, _read_previous_scene
from chrona.storage.revision_store import LocalSnapshotReader, snapshot_directory
from chrona.usecases.materialize import _OverlayBuilder
from chrona.usecases.failure_report import report_failure
from chrona.resources import default_preset_resource, default_preset_root
from chrona.presentation.model.info_diagnostics import RelationHintReceipt, RelationHintSummary


@pytest.fixture(scope="module")
def previous_bytes():
    project = Path(__file__).resolve().parents[3] / "fixtures/routing_revision/project-v1.yaml"
    return serialize_scene(render_draft(DraftRenderRequest(project, "svg")).rendered.scene)


def test_neutral_pin_capture_checks_exact_bytes_even_with_injected_reader(previous_bytes):
    pin = ArtifactPin(freeze({"provider": "local", "identity": "prior"}),
                      "prior.scene.json", "revision-1", f"sha256:{sha256(previous_bytes).hexdigest()}")
    class Reader:
        def read(self, reference):
            assert "id" not in reference and "kind" not in reference
            assert reference == pin.as_reader_reference()
            return previous_bytes
    assert _read_previous_scene(pin, Reader()) == previous_bytes
    class CorruptReader:
        def read(self, reference):
            return previous_bytes + b" "
    with pytest.raises(ClosureError) as error:
        _read_previous_scene(pin, CorruptReader())
    assert error.value.diagnostic_id == "E_CONTENT_IDENTITY"
    assert error.value.source_ref == "/body/inputs/previousScene"


def test_neutral_pin_reader_failure_keeps_store_code():
    pin = ArtifactPin(freeze({"provider": "local", "identity": "prior"}),
                      "prior.scene.json", "revision-1", "sha256:" + "0" * 64)
    class MissingReader:
        def read(self, reference):
            raise SnapshotReadError("E_STORE_REFERENCE", "missing immutable bytes")
    with pytest.raises(ClosureError) as error:
        _read_previous_scene(pin, MissingReader())
    assert error.value.diagnostic_id == "E_STORE_REFERENCE"


def test_real_store_and_execution_overlay_read_identity_neutral_pin(tmp_path, previous_bytes):
    pin = ArtifactPin(freeze({"provider": "local", "identity": "prior"}),
                      "prior.scene.json", "revision-1", f"sha256:{sha256(previous_bytes).hexdigest()}")
    root = tmp_path / "store"
    revision = snapshot_directory(root, pin.revision_token)
    revision.mkdir(parents=True)
    (revision / pin.address).write_bytes(previous_bytes)
    assert _read_previous_scene(pin, LocalSnapshotReader(root, "prior")) == previous_bytes
    staging = tmp_path / "overlay"
    staging.mkdir()
    builder = _OverlayBuilder(staging)
    builder.add_reference(pin.as_reader_reference(), previous_bytes)
    overlay = builder.finish()
    assert _read_previous_scene(pin, overlay) == previous_bytes
    altered = dict(pin.as_reader_reference())
    altered["revision"] = {"token": "different-revision"}
    with pytest.raises(SnapshotReadError, match="E_STORE_REFERENCE"):
        overlay.read(altered)


def test_same_project_accepts_prior_revision_and_freezes_input(previous_bytes):
    result = decode_previous_scene(previous_bytes, "nimbus-launch")
    assert result.value["kind"] == "scene"
    with pytest.raises(TypeError):
        result.value["kind"] = "changed"


def test_forecast_primary_mark_is_decoded_without_purpose_aliasing(previous_bytes):
    value = json.loads(previous_bytes)
    mark = next(primitive for surface in value["surfaces"]
                for primitive in surface["primitives"]
                if primitive.get("purpose") == "planned" and primitive.get("kind") in {"Rect", "Symbol"})
    mark["purpose"] = "forecast"

    decoded = decode_previous_scene(json.dumps(value).encode(), "nimbus-launch")
    host = next(item for surface in decoded.route_hints.surfaces
                for item in surface.marks if item.placement_id == mark["id"])
    assert host.purpose == "forecast"
    assert host.kind == mark["kind"]
    assert host.source_ref == mark["sourceRef"]


def _scene_with_fan_in(previous_bytes):
    value = json.loads(previous_bytes)
    surface = next(item for item in value["surfaces"] if any(
        primitive.get("sourceKind") == "relation" and primitive.get("markerEnd")
        for primitive in item["primitives"]))
    template = next(primitive for primitive in surface["primitives"]
                    if primitive.get("sourceKind") == "relation" and primitive.get("markerEnd"))
    owner, nonowner = deepcopy(template), deepcopy(template)
    owner.update(id="hint-fan-in-owner", sourceRef="relation:id:hint-fan-in-owner",
                 fromInstanceId="hint-source-owner", toInstanceId="hint-target")
    nonowner.update(id="hint-fan-in-nonowner", sourceRef="relation:id:hint-fan-in-nonowner",
                    fromInstanceId="hint-source-nonowner", toInstanceId="hint-target")
    shared = {"targetPortId": "hint-target:start", "terminalOwnerId": owner["id"]}
    owner["fanIn"] = dict(shared)
    nonowner["fanIn"] = dict(shared)
    nonowner.pop("markerEnd")
    surface["primitives"].extend((owner, nonowner))
    return value, owner, nonowner


def test_fan_in_nonowner_decodes_exact_owner_terminal_without_scene_rewrite(previous_bytes):
    value, owner, nonowner = _scene_with_fan_in(previous_bytes)
    payload = json.dumps(value).encode()

    decoded = decode_previous_scene(payload, "nimbus-launch")
    hint = next(relation for surface in decoded.route_hints.surfaces
                for relation in surface.relations
                if relation.source_ref == nonowner["sourceRef"])
    owner_marker = next(relation.marker_end for surface in decoded.route_hints.surfaces
                        for relation in surface.relations
                        if relation.source_ref == owner["sourceRef"])

    assert hint.marker_end == owner_marker
    assert "markerEnd" not in nonowner
    decoded_nonowner = next(primitive for surface in decoded.value["surfaces"]
                            for primitive in surface["primitives"]
                            if primitive["id"] == nonowner["id"])
    assert "markerEnd" not in decoded_nonowner
    assert decoded_nonowner["fanIn"] == nonowner["fanIn"]
    assert decoded.value == freeze(value)


@pytest.mark.parametrize("corruption", ["missing-owner", "different-owner-port"])
def test_invalid_fan_in_owner_is_rejected_before_hint_decoding(previous_bytes, corruption):
    value, owner, nonowner = _scene_with_fan_in(previous_bytes)
    if corruption == "missing-owner":
        nonowner["fanIn"]["terminalOwnerId"] = "absent-owner"
    else:
        owner["fanIn"]["targetPortId"] = "other-target:start"

    with pytest.raises(SceneSerializationError, match="E_SCENE_SERIALIZATION"):
        decode_previous_scene(json.dumps(value).encode(), "nimbus-launch")


def test_changed_configured_terminal_still_rejects_fan_in_hint(previous_bytes):
    value, _, nonowner = _scene_with_fan_in(previous_bytes)
    decoded = decode_previous_scene(json.dumps(value).encode(), "nimbus-launch")
    relation = next(relation for surface in decoded.route_hints.surfaces
                    for relation in surface.relations
                    if relation.source_ref == nonowner["sourceRef"])
    marker = relation.marker_end
    assert marker is not None
    outline = tuple(PathCommand(kind, points) for kind, points in marker.outline)
    current = MarkerGeometry(outline, marker.head_length, marker.head_width,
                             marker.attachment_offset, marker.paint_mode)
    start_marker = relation.marker_start
    assert start_marker is not None
    current_start = MarkerGeometry(
        tuple(PathCommand(kind, points) for kind, points in start_marker.outline),
        start_marker.head_length, start_marker.head_width,
        start_marker.attachment_offset, start_marker.paint_mode)
    changed_outline = (*outline[:-1], PathCommand(outline[-1].kind,
        tuple((x + 1.0, y) for x, y in outline[-1].points)))
    changed = replace(current, outline=changed_outline)

    proposal = propose_hint(decoded.route_hints, surface_id=next(
        surface.surface_id for surface in decoded.route_hints.surfaces
        if any(item.source_ref == nonowner["sourceRef"] for item in surface.relations)),
        source_ref=nonowner["sourceRef"], source_id=nonowner["fromInstanceId"],
        target_id=nonowner["toInstanceId"], source_mark=None, target_mark=None,
        source_endpoint="start", target_endpoint="finish", source_siblings=(),
        target_siblings=(), port_pairs=(), marker_start=current_start, marker_end=changed,
        stroke_width=1.0)

    assert proposal.disposition == "unusable"
    assert proposal.reason == "terminal-semantics"


def _composite_symbol_parts():
    base = "planned:milestone:milestone"
    shared = {"sourceRef": "milestone", "kind": "Symbol", "purpose": "forecast",
              "bounds": {"inline": 3, "block": 5, "inlineSize": 7, "blockSize": 9}}
    first = {"id": f"{base}:part0", **shared, "bounds": dict(shared["bounds"])}
    second = {"id": f"{base}:part1", **shared, "bounds": dict(shared["bounds"])}
    return base, first, second


def test_exact_composite_symbol_siblings_recover_one_forecast_placement():
    base, first, second = _composite_symbol_parts()
    marks = _hint_marks((first, second))
    matches = [mark for mark in marks if mark.placement_id == base]

    assert len(matches) == 1
    assert matches[0].kind == "Symbol"
    assert matches[0].purpose == "forecast"
    assert matches[0].source_ref == first["sourceRef"] == second["sourceRef"]
    assert matches[0].bounds == tuple(float(first["bounds"][key])
                                      for key in ("inline", "block", "inlineSize", "blockSize"))
    assert not any(mark.placement_id in {first["id"], second["id"]} for mark in marks)


@pytest.mark.parametrize("conflict", ["sourceRef", "purpose", "bounds"])
def test_conflicting_composite_symbol_siblings_are_not_coalesced(conflict):
    base, first, second = _composite_symbol_parts()
    if conflict == "sourceRef":
        second["sourceRef"] = "different-source"
    elif conflict == "purpose":
        second["purpose"] = "actual"
    else:
        second["bounds"]["inlineSize"] += 1

    marks = _hint_marks((first, second))
    ids = {mark.placement_id for mark in marks}

    assert base not in ids
    assert {first["id"], second["id"]} <= ids


def test_unsuffixed_composite_symbol_collision_is_not_decoded_as_a_host():
    base, first, second = _composite_symbol_parts()
    first["id"] = base

    marks = _hint_marks((first, second))
    ids = {mark.placement_id for mark in marks}

    assert not ({base, second["id"]} & ids)


@pytest.mark.parametrize("indices", [(1,), (0, 2), (0, 0)])
def test_incomplete_or_duplicate_symbol_part_indices_do_not_recover_host(indices):
    base, first, second = _composite_symbol_parts()
    parts = {0: first, 1: second, 2: {**second, "id": f"{base}:part2"}}
    values = [dict(parts[index]) for index in indices]
    marks = _hint_marks(values)

    assert all(mark.placement_id != base for mark in marks)


@pytest.mark.parametrize("payload", [b"not-json", b"[]", b"\xff", b'{"version":"chrona/scene/v999"}'])
def test_malformed_or_unsupported_previous_scene_fails_ingress(payload):
    with pytest.raises(SceneSerializationError, match="E_SCENE_SERIALIZATION"):
        decode_previous_scene(payload, "nimbus-launch")


def test_wrong_project_fails_before_hint_matching(previous_bytes):
    with pytest.raises(SceneSerializationError, match="current primary Project"):
        decode_previous_scene(previous_bytes, "different-project")


def test_wrong_project_maps_to_stable_transport_failure(previous_bytes):
    try:
        decode_previous_scene(previous_bytes, "different-project")
    except SceneSerializationError as error:
        failure = report_failure(error)
    assert failure.diagnostics[0]["code"] == "E_SCENE_SERIALIZATION"


def test_draft_captures_prior_bytes_without_modifying_file(tmp_path, previous_bytes):
    project = Path(__file__).resolve().parents[3] / "fixtures/routing_revision/project-v1.yaml"
    previous = tmp_path / "prior.scene.json"
    previous.write_bytes(previous_bytes)
    result = render_draft(DraftRenderRequest(project, "svg", previous_scene=previous)).rendered
    assert result.scene.provenance.mode == "draft"
    assert previous.read_bytes() == previous_bytes
    summary = next(item for item in result.info_diagnostics if isinstance(item, RelationHintSummary))
    assert summary.payload()["actualSearch"] == 0
    assert summary.payload()["accepted"] == summary.payload()["relationInstances"], summary.payload()


def test_draft_refuses_wrong_project_input(tmp_path, previous_bytes):
    project = Path(__file__).resolve().parents[3] / "fixtures/routing_revision/project-v1.yaml"
    previous = tmp_path / "prior.scene.json"
    value = json.loads(previous_bytes)
    next(item for item in value["provenance"]["resources"]
         if item["kind"] == "project")["id"] = "other-project"
    previous.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(SceneSerializationError, match="current primary Project"):
        render_draft(DraftRenderRequest(project, "svg", previous_scene=previous))


@pytest.mark.parametrize("search_policy", ["first-fit", "best"])
def test_both_policies_revalidate_prior_geometry_and_report_receipts(tmp_path, previous_bytes, search_policy):
    project = Path(__file__).resolve().parents[3] / "fixtures/routing_revision/project-v1.yaml"
    preset = yaml.safe_load(default_preset_resource().read_bytes())
    layout = yaml.safe_load((default_preset_root() / preset["body"]["resources"]["layout"]["path"]).read_bytes())
    layout["relationRouting"]["search"] = search_policy
    layout_path = tmp_path / "best.yaml"
    layout_path.write_text(yaml.safe_dump(layout, sort_keys=False), encoding="utf-8")
    previous = tmp_path / "prior.scene.json"
    previous.write_bytes(previous_bytes)
    baseline = render_draft(DraftRenderRequest(project, "svg", layout=layout_path)).rendered
    hinted = render_draft(DraftRenderRequest(project, "svg", layout=layout_path, previous_scene=previous)).rendered
    assert not any(isinstance(item, RelationHintSummary) for item in baseline.info_diagnostics)
    summary, = [item for item in hinted.info_diagnostics if isinstance(item, RelationHintSummary)]
    receipts = [item for item in hinted.info_diagnostics if isinstance(item, RelationHintReceipt)]
    assert summary.payload()["accepted"] > 0
    assert summary.payload()["relationInstances"] == len(receipts)
    prior_routes = {primitive["id"]: primitive["points"]
                    for surface in json.loads(previous_bytes)["surfaces"]
                    for primitive in surface["primitives"] if primitive.get("kind") == "Path"}
    current_routes = {primitive.scene_id: primitive.points for primitive in hinted.surface.primitives
                      if primitive.kind == "Path"}
    for receipt in receipts:
        if receipt.disposition == "accepted":
            assert not receipt.searched
            assert current_routes[receipt.relation_id] == tuple(tuple(point) for point in prior_routes[receipt.relation_id])


@pytest.mark.parametrize("search_policy", ["first-fit", "best"])
@pytest.mark.parametrize("mode", ["overlap", "stub"])
def test_modes_bypassing_normal_routing_explain_unusable_hints(tmp_path, previous_bytes, search_policy, mode):
    project = Path(__file__).resolve().parents[3] / "fixtures/routing_revision/project-v1.yaml"
    preset = yaml.safe_load(default_preset_resource().read_bytes())
    layout = yaml.safe_load((default_preset_root() / preset["body"]["resources"]["layout"]["path"]).read_bytes())
    layout["relationRouting"].update(search=search_policy, unroutable=mode)
    layout_path, previous = tmp_path / "layout.yaml", tmp_path / "prior.scene.json"
    layout_path.write_text(yaml.safe_dump(layout, sort_keys=False), encoding="utf-8")
    previous.write_bytes(previous_bytes)
    view = yaml.safe_load((default_preset_root() / preset["body"]["resources"]["view"]["path"]).read_bytes())
    # Receipt behavior is independent of plot-name packing. The default plot
    # names expose a pre-existing stub/text overlap tracked separately in1763.
    view["body"]["visibility"]["labels"]["placement"] = "table"
    view_path = tmp_path / "table-labels.yaml"
    view_path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")
    hinted = render_draft(DraftRenderRequest(project, "svg", view=view_path, layout=layout_path,
                                           previous_scene=previous)).rendered
    receipts = [item for item in hinted.info_diagnostics if isinstance(item, RelationHintReceipt)]
    summary, = [item for item in hinted.info_diagnostics if isinstance(item, RelationHintSummary)]
    assert receipts
    assert all(item.disposition == "unusable" and item.reason == "mode-bypasses-normal"
               and item.code == "I_LAYOUT_RELATION_HINT" and not item.searched for item in receipts)
    assert summary.payload()["unusable"] == len(receipts)


@pytest.mark.parametrize("duplicate", [False, True])
def test_missing_or_duplicate_primary_project_is_not_a_hint_miss(previous_bytes, duplicate):
    value = json.loads(previous_bytes)
    resources = value["provenance"]["resources"]
    project = next(item for item in resources if item["kind"] == "project")
    value["provenance"]["resources"] = (resources + [project] if duplicate else
                                          [item for item in resources if item["kind"] != "project"])
    with pytest.raises(SceneSerializationError, match="current primary Project"):
        decode_previous_scene(json.dumps(value).encode(), "nimbus-launch")
