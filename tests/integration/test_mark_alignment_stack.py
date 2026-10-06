"""Synthetic public #1149 acceptance: aligned point marks and declared span-band stacks."""
from __future__ import annotations

import json
from html import escape
import re
from datetime import date
from pathlib import Path

import pytest

from chrona.presentation.scene.serialization import serialize_scene
from tests.support import synthetic_review as sr


AS_OF = "2026-03-15"
BAR = "bar"


def _actual_set(observations=()):
    return {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed", "body": {
        "asOf": AS_OF, "observations": list(observations)}}


def _observation(object_id=BAR):
    return {"id": f"obs-{object_id}", "sequence": 1, "projectObjectId": object_id,
            "actual": {"start": "2026-02-05", "finish": "2026-02-20"}}


def _gate_observation():
    return {"id": "obs-gate", "sequence": 1, "projectObjectId": "gate",
            "actual": {"at": "2026-02-14"}}


def _point_source():
    # The anchor span makes the temporal window non-degenerate without sharing the gate's row.
    return {"gate": sr.point("gate", date(2026, 2, 13)),
            "anchor": sr.span("anchor", date(2026, 2, 1), 30, owner="b")}


def _set_height(parts, role: str, height: float) -> None:
    token = f"issue1149-{role}-height"
    parts["theme"]["body"]["values"][token] = {"type": "number", "value": height}
    parts["theme"]["body"]["roles"][role]["markHeight"] = token


def _align_parts(*, rows: str, align: str | None, explicit_symbol: tuple[float, float] | None = None):
    parts = sr.bundle()
    if rows == "automatic":
        parts["view"]["body"]["rows"] = {"mode": "automatic"}
    if align is None:
        parts["theme"]["body"]["roles"]["planned"].pop("align", None)
    else:
        parts["theme"]["body"]["roles"]["planned"]["align"] = align
    parts["theme"]["body"]["roles"]["planned"].pop("markOffset", None)
    _set_height(parts, "planned", 0.5)
    if explicit_symbol is not None:
        height, offset = explicit_symbol
        for prop, value in (("symbolHeight", height), ("symbolOffset", offset)):
            token = f"issue1149-planned-{prop}"
            parts["theme"]["body"]["values"][token] = {"type": "number", "value": value}
            parts["theme"]["body"]["roles"]["planned"][prop] = token
    return parts


def _stack_parts(*, rows: str, heights: dict[str, float], gap: float,
                 frame_roles: tuple[str, ...] = ()):
    parts = sr.bundle()
    if rows == "automatic":
        parts["view"]["body"]["rows"] = {"mode": "automatic"}
    for role, height in heights.items():
        _set_height(parts, role, height)
        parts["theme"]["body"]["roles"][role].pop("markOffset", None)
    gap_token = "issue1149-stack-gap"
    parts["theme"]["body"]["values"][gap_token] = {"type": "number", "value": gap}
    declaration = {"members": [["planned", "missing-actual"], ["actual"]], "gap": gap_token}
    if frame_roles:
        padding_token = "issue1149-frame-padding"
        parts["theme"]["body"]["values"][padding_token] = {"type": "number", "value": 2}
        declaration["frame"] = {"roles": list(frame_roles), "padding": padding_token}
        for role in frame_roles:
            parts["theme"]["body"]["roles"][role].pop("markOffset", None)
    parts["theme"]["body"]["markStack"] = declaration
    return parts


def _render(tmp_path: Path, parts, objects, *, actual=None, viewport=(1000, None)):
    tmp_path.mkdir(parents=True, exist_ok=True)
    return sr.render(tmp_path, sr.project(objects), presentation=parts, actual=actual, viewport=viewport)


def _surface(rendered):
    # serialize_scene validates the public Scene against the published schema.
    document = json.loads(serialize_scene(rendered.scene))
    return document, document["surfaces"][0]


def _primitive(surface, purpose: str, object_id: str):
    matches = [item for item in surface["primitives"]
               if item["purpose"] == purpose and item["sourceRef"] == object_id]
    assert len(matches) == 1, (purpose, object_id, [item["id"] for item in matches])
    return matches[0]


def _svg_rect(rendered, scene_id: str) -> dict[str, float]:
    svg = rendered.artifact.content.decode()
    node = re.search(rf'<rect\b(?=[^>]*data-scene-id="{re.escape(escape(scene_id, quote=True))}")[^>]*>', svg)
    assert node is not None, scene_id
    attrs = {name: float(value) for name, value in
             re.findall(r'\b(x|y|width|height)="([0-9.+-]+)"', node.group(0))}
    assert set(attrs) == {"x", "y", "width", "height"}, node.group(0)
    return attrs


@pytest.mark.parametrize("rows", ["automatic", "lanes"])
@pytest.mark.parametrize("track_size", [10, 16, 30])
def test_offset_free_point_defaults_to_center_without_align_or_stack(tmp_path, rows, track_size):
    source = _point_source()
    baseline_parts = sr.bundle()
    aligned_parts = _align_parts(rows=rows, align=None)
    for parts in (baseline_parts, aligned_parts):
        token = parts["theme"]["body"]["metrics"]["timeline.mark.blockSize"]
        parts["theme"]["body"]["values"][token]["value"] = track_size
        if rows == "automatic":
            parts["view"]["body"]["rows"] = {"mode": "automatic"}
    baseline = _render(tmp_path / "baseline", baseline_parts, source)
    aligned = _render(tmp_path / "aligned", aligned_parts, source)
    _, base_surface = _surface(baseline)
    _, aligned_surface = _surface(aligned)
    track = _primitive(base_surface, "planned", "gate")["bounds"]
    symbol = _primitive(aligned_surface, "planned", "gate")["bounds"]
    assert symbol["block"] + symbol["blockSize"] / 2 == pytest.approx(
        track["block"] + track["blockSize"] / 2, abs=0.01)
    assert aligned_surface["primitives"]


def test_folded_header_point_uses_centered_completed_track(tmp_path):
    parts = sr.bundle()
    parts["view"]["body"]["rows"] = {"mode": "automatic", "points": "group-header"}
    parts["view"]["body"]["grouping"] = {
        "by": "field", "field": "owner", "missing": "ungrouped", "presentation": "header",
    }
    parts["theme"]["body"]["roles"]["planned"].pop("markOffset", None)
    _set_height(parts, "planned", 0.5)
    source = {"gate": sr.point("gate", date(2026, 2, 13), owner="b"),
              "anchor": sr.span("anchor", date(2026, 2, 1), 30, owner="b")}
    rendered = _render(tmp_path, parts, source)
    _, surface = _surface(rendered)
    mark = _primitive(surface, "planned", "gate")["bounds"]
    header = next(group["headerBounds"] for group in surface["groups"] if group["id"] == "b")
    assert mark["block"] + mark["blockSize"] / 2 == pytest.approx(
        header["block"] + header["blockSize"] / 2, abs=0.01)


@pytest.mark.parametrize(("alignment", "fraction"), [("start", 0), ("center", 0.25), ("end", 0.5)])
def test_explicit_point_alignment_uses_resolved_track_start_center_and_end(tmp_path, alignment, fraction):
    source = _point_source()
    baseline = _render(tmp_path / "baseline", sr.bundle(), source)
    rendered = _render(tmp_path / alignment,
                       _align_parts(rows="automatic", align=alignment), source)
    _, base_surface = _surface(baseline)
    _, surface = _surface(rendered)
    track = _primitive(base_surface, "planned", "gate")["bounds"]
    symbol = _primitive(surface, "planned", "gate")["bounds"]
    assert symbol["blockSize"] == pytest.approx(track["blockSize"] * 0.5)
    assert symbol["block"] == pytest.approx(track["block"] + track["blockSize"] * fraction, abs=0.01)


def test_explicit_symbol_offset_wins_alignment_and_actual_keeps_1074_planned_inheritance(tmp_path):
    source = _point_source()
    parts = _align_parts(rows="automatic", align="start", explicit_symbol=(0.6, 0.2))
    _set_height(parts, "actual", 0.2)
    # Preserve an explicit non-stack actual band offset; #1074 makes its taller omitted symbol follow planned.
    parts["theme"]["body"]["roles"]["actual"]["markOffset"] = "mark-offset-nested"
    rendered = _render(tmp_path, parts, source, actual=_actual_set([_gate_observation()]))
    _, surface = _surface(rendered)
    planned = _primitive(surface, "planned", "gate")["bounds"]
    track_probe = _render(tmp_path / "probe", sr.bundle(), source)
    _, probe_surface = _surface(track_probe)
    track = _primitive(probe_surface, "planned", "gate")["bounds"]
    # Explicit symbolOffset (0.2) wins even though role alignment asks for start.
    assert planned["block"] == pytest.approx(track["block"] + track["blockSize"] * 0.2, abs=0.01)
    assert planned["blockSize"] == pytest.approx(track["blockSize"] * 0.6)
    actual = _primitive(surface, "actual", "gate")["bounds"]
    assert actual["block"] == pytest.approx(planned["block"], abs=0.01)
    assert actual["blockSize"] == pytest.approx(planned["blockSize"])


def test_explicit_offsets_override_alignment_and_absent_declaration_is_byte_stable(tmp_path):
    source = {"bar": sr.span("bar", date(2026, 2, 2), 20)}
    baseline = _render(tmp_path / "baseline", sr.bundle(), source)
    explicit_align = sr.bundle()
    explicit_align["theme"]["body"]["roles"]["planned"]["align"] = "end"
    rendered = _render(tmp_path / "explicit-align", explicit_align, source)
    base_doc, base_surface = _surface(baseline)
    doc, surface = _surface(rendered)
    assert surface == base_surface  # no content/geometry change from an ignored align beside explicit offset
    assert rendered.artifact.content == baseline.artifact.content
    assert doc["diagnostics"] == base_doc["diagnostics"]


@pytest.mark.parametrize("rows", ["automatic", "lanes"])
def test_stack_order_gap_center_and_missing_actual_reserve_same_slot(tmp_path, rows):
    source = {"bar": sr.span("bar", date(2026, 2, 2), 20)}
    parts = _stack_parts(rows=rows, heights={"planned": 0.3, "missing-actual": 0.3, "actual": 0.2}, gap=4)
    measured_parts = sr.bundle()
    probe = _render(tmp_path / "probe", measured_parts, source)
    _, probe_surface = _surface(probe)
    track = _primitive(probe_surface, "planned", "bar")["bounds"]
    missing_obs = _render(tmp_path / "missing", parts, source, actual=_actual_set())
    observed = _render(tmp_path / "observed", parts, source, actual=_actual_set([_observation()]))
    _, missing_surface = _surface(missing_obs)
    _, observed_surface = _surface(observed)
    planned = _primitive(observed_surface, "planned", "bar")["bounds"]
    actual = _primitive(observed_surface, "actual", "bar")["bounds"]
    missing_planned = _primitive(missing_surface, "planned", "bar")["bounds"]
    assert planned["block"] == pytest.approx(missing_planned["block"], abs=0.01)  # absent actual does not reflow it
    assert actual["block"] - (planned["block"] + planned["blockSize"]) == pytest.approx(4, abs=0.01)
    stack_center = (planned["block"] + actual["block"] + actual["blockSize"]) / 2
    assert stack_center == pytest.approx(track["block"] + track["blockSize"] / 2, abs=0.01)
    assert _svg_rect(observed, _primitive(observed_surface, "planned", "bar")["id"])["y"] == pytest.approx(planned["block"])
    assert _svg_rect(observed, _primitive(observed_surface, "actual", "bar")["id"])["y"] == pytest.approx(actual["block"])


def test_changing_one_stack_height_recentres_stack_without_reordering(tmp_path):
    source = {"bar": sr.span("bar", date(2026, 2, 2), 20)}
    base_parts = _stack_parts(rows="automatic", heights={"planned": 0.25, "missing-actual": 0.25, "actual": 0.2}, gap=3)
    taller_parts = _stack_parts(rows="automatic", heights={"planned": 0.25, "missing-actual": 0.25, "actual": 0.5}, gap=3)
    actual = _actual_set([_observation()])
    base = _render(tmp_path / "base", base_parts, source, actual=actual)
    taller = _render(tmp_path / "taller", taller_parts, source, actual=actual)
    _, base_surface = _surface(base)
    _, taller_surface = _surface(taller)
    before_plan = _primitive(base_surface, "planned", "bar")["bounds"]
    before_actual = _primitive(base_surface, "actual", "bar")["bounds"]
    after_plan = _primitive(taller_surface, "planned", "bar")["bounds"]
    after_actual = _primitive(taller_surface, "actual", "bar")["bounds"]
    assert before_actual["block"] > before_plan["block"]
    assert after_actual["block"] > after_plan["block"]
    assert after_plan["block"] < before_plan["block"]
    assert after_actual["block"] < before_actual["block"]


def test_frame_span_size_is_independent_of_point_symbol_fallback(tmp_path):
    source = {"bar": sr.span("bar", date(2026, 2, 2), 20),
              "gate": sr.point("gate", date(2026, 2, 13))}
    parts = _stack_parts(rows="automatic", heights={"planned": 0.25, "missing-actual": 0.2, "actual": 0.3},
                         gap=2, frame_roles=("planned",))
    parts["theme"]["body"]["markStack"]["members"] = [["actual"]]
    # Frame padding is 2 px on each side; point symbol still uses planned markHeight (0.25 track).
    rendered = _render(tmp_path, parts, source, actual=_actual_set([_observation()]))
    _, surface = _surface(rendered)
    span_frame = _primitive(surface, "planned", "bar")["bounds"]
    point_symbol = _primitive(surface, "planned", "gate")["bounds"]
    actual = _primitive(surface, "actual", "bar")["bounds"]
    assert span_frame["blockSize"] == pytest.approx(actual["blockSize"] + 4, abs=0.01)
    assert point_symbol["blockSize"] != pytest.approx(span_frame["blockSize"])


@pytest.mark.parametrize("rows", ["automatic", "lanes"])
def test_valid_oversized_stack_warns_and_expands_row_pitch_with_completed_bounds(tmp_path, rows):
    source = {"bar": sr.span("bar", date(2026, 2, 2), 20),
              "bar2": sr.span("bar2", date(2026, 2, 2), 20, owner="b")}
    parts = _stack_parts(rows=rows, heights={"planned": 0.9, "missing-actual": 0.8, "actual": 0.9}, gap=8,
                         frame_roles=("snapshot", "scenario"))
    rendered = _render(tmp_path, parts, source, actual=_actual_set([_observation("bar"), _observation("bar2")]))
    document, surface = _surface(rendered)
    assert any(item.startswith("W_LAYOUT_MARK_STACK_OVERFLOW:") for item in document["diagnostics"])
    assert "E_LAYOUT_MARK_OVERFLOW" not in document["diagnostics"]
    for row in surface["rows"]:
        row_bounds = row["bounds"]
        row_marks = [item for item in surface["primitives"]
                     if (item.get("laneRowId") == row["id"] if surface.get("laneMode")
                         else item["sourceRef"] == row["objectId"])
                     and item["purpose"] in {"planned", "actual", "missingActual"}]
        assert row_marks
        assert all(item["bounds"]["block"] >= row_bounds["block"] - 0.01
                   and item["bounds"]["block"] + item["bounds"]["blockSize"]
                   <= row_bounds["block"] + row_bounds["blockSize"] + 0.01 for item in row_marks), (row, row_marks)
    for object_id in ("bar", "bar2"):
        planned = _primitive(surface, "planned", object_id)["bounds"]
        actual = _primitive(surface, "actual", object_id)["bounds"]
        stack_center = (planned["block"] + actual["block"] + actual["blockSize"]) / 2
        row = next(item for item in surface["rows"]
                   if (item["id"] == _primitive(surface, "planned", object_id).get("laneRowId")
                       if surface.get("laneMode") else item["objectId"] == object_id))
        # The oversized declared band expands/recentres row pitch. laneMarkBandBlock is
        # the first completed mark, not the nominal track origin, so use the completed
        # row's center as the invariant instead of comparing with a no-stack probe.
        assert stack_center == pytest.approx(
            row["bounds"]["block"] + row["bounds"]["blockSize"] / 2, abs=0.01)
    for purpose, object_id in (("planned", "bar"), ("actual", "bar"), ("planned", "bar2"), ("actual", "bar2")):
        primitive = _primitive(surface, purpose, object_id)
        assert _svg_rect(rendered, primitive["id"])["y"] == pytest.approx(primitive["bounds"]["block"])
