"""Folded point deadlines share the ordinary tick/run path and reserve their ink before header packing."""
from __future__ import annotations

from datetime import date

from tests.support import synthetic_review as sr


def _folded_deadline_render(directory):
    directory.mkdir()
    source = sr.project({
        "task": sr.span("task", date(2026, 1, 5), 30, owner="a"),
        "kept": sr.point("kept", date(2026, 2, 12), owner="a", title="K"),
        "slipped": sr.point("slipped", date(2026, 2, 16), owner="a", title="L"),
    })
    source["entities"]["a"]["title"] = "Group A"
    source["objects"]["kept"]["deadline"] = "2026-02-12"
    source["objects"]["slipped"]["deadline"] = "2026-02-10"

    parts = sr.bundle()
    body = parts["view"]["body"]
    body["rows"] = {"mode": "automatic", "points": "group-header"}
    body["window"] = {"mode": "explicit", "start": "2026-01-01", "end": "2026-03-01"}
    body["deadlines"] = {"show": "all", "caption": {"template": "{daysLate} days late"}}
    body["visibility"]["labels"]["side"] = "start"

    theme = parts["theme"]["body"]
    # Give the two packed tracks enough authored block capacity for their full
    # deadline envelopes; overflow behavior remains covered by folded-lane tests.
    theme["values"]["timeline-group-header-size"]["value"] = 100
    theme["values"].update({
        "deadline-outline": {"type": "number", "value": 1},
        "folded-deadline-amplitude": {"type": "number", "value": 4},
        "folded-deadline-wavelength": {"type": "number", "value": 4},
        "folded-deadline-seed": {"type": "number", "value": 1},
        "folded-deadline-fidelity": {"type": "fidelity", "value": "decorative-optional"},
    })
    theme["roles"]["deadline-mark"].update({
        "outlineWidth": "deadline-outline",
        "wobbleAmplitude": "folded-deadline-amplitude",
        "wobbleWavelength": "folded-deadline-wavelength",
        "wobbleSeed": "folded-deadline-seed",
        "wobbleFidelity": "folded-deadline-fidelity",
    })
    return sr.render(directory, source, presentation=parts)


def test_folded_kept_and_slipped_points_reserve_full_deadline_ink(tmp_path):
    rendered = _folded_deadline_render(tmp_path / "folded-deadlines")
    primitives = rendered.surface.primitives
    provenance = {item.primitive_id: item.subjects for item in rendered.surface.primitive_provenance}
    planned = {
        item.source_ref: item for item in primitives
        if item.purpose in {"planned", "forecast"} and item.scene_id.startswith("planned:group-header:")
    }
    ticks = {item.source_ref: item for item in primitives if item.scene_id.startswith("deadline-tick:")}
    runs = {item.source_ref: item for item in primitives if item.scene_id.startswith("deadline-run:")}
    assert set(planned) == set(ticks) == {"kept", "slipped"}
    assert set(runs) == {"slipped"}
    # The slipped run starts before and crosses the other point's date, so its complete
    # footprint—not only the folded mark/title extents—forces a separate header lane.
    assert planned["kept"].bounds[1] != planned["slipped"].bounds[1]
    for object_id, mark in planned.items():
        instance = mark.scene_id.removeprefix("planned:")
        assert ticks[object_id].scene_id == f"deadline-tick:{instance}"
        assert ticks[object_id].source_ref == object_id and ticks[object_id].slot_id == mark.slot_id
        assert provenance[ticks[object_id].scene_id] == provenance[mark.scene_id]
    assert runs["slipped"].scene_id == f"deadline-run:{planned['slipped'].scene_id.removeprefix('planned:')}"
    assert runs["slipped"].source_ref == "slipped"

    outlines = {item.scene_id.removesuffix(":outline"): item for item in primitives
                if item.visual_role == "deadline-mark-outline"}
    folded_tick_ids = {f"deadline-tick:{mark.scene_id.removeprefix('planned:')}" for mark in planned.values()}
    folded_run_ids = {f"deadline-run:{planned['slipped'].scene_id.removeprefix('planned:')}"}
    assert folded_tick_ids | folded_run_ids <= set(outlines)
    for stroke in [*ticks.values(), *runs.values()]:
        ground = outlines[stroke.scene_id]
        assert ground.bounds[0] < stroke.bounds[0]
        assert ground.bounds[0] + ground.bounds[2] > stroke.bounds[0] + stroke.bounds[2]

    captions = [item for item in primitives if item.purpose == "deadline-caption"
                and "group-header" in item.scene_id]
    assert len(captions) == 1 and captions[0].source_ref == "slipped"
    assert "6 days late" in captions[0].text
    assert not any("I_LAYOUT_DEADLINE_CAPTION_DROPPED" in item for item in rendered.scene.diagnostics)

    (group,) = rendered.surface.groups
    _, header_top, _, header_height = group.header_bounds
    for stroke in [*ticks.values(), *runs.values()]:
        if "group-header" not in stroke.scene_id:
            continue
        ground = outlines[stroke.scene_id]
        assert header_top <= ground.bounds[1] + 0.001
        assert header_top + header_height + 0.001 >= ground.bounds[1] + ground.bounds[3]
    assert not any("I_LAYOUT_DEADLINE_FOLDED" in item for item in rendered.scene.diagnostics)
    assert not any("W_LAYOUT_GROUP_HEADER_OVERFLOW" in item for item in rendered.scene.diagnostics)


def test_folded_deadline_outside_the_window_keeps_the_existing_diagnostic(tmp_path):
    source = sr.project({"gate": sr.point("gate", date(2026, 2, 12), owner="a", title="Gate")})
    source["entities"]["a"]["title"] = "Group A"
    source["objects"]["gate"]["deadline"] = "2025-12-01"
    parts = sr.bundle()
    body = parts["view"]["body"]
    body["rows"] = {"mode": "automatic", "points": "group-header"}
    body["window"] = {"mode": "explicit", "start": "2026-01-01", "end": "2026-03-01"}
    body["deadlines"] = {"show": "all"}
    rendered = sr.render(tmp_path, source, presentation=parts)
    assert not any(item.scene_id.startswith("deadline-") for item in rendered.surface.primitives)
    assert "I_LAYOUT_DEADLINE_OUTSIDE_WINDOW:gate" in rendered.scene.diagnostics
    assert not any("I_LAYOUT_DEADLINE_FOLDED" in item for item in rendered.scene.diagnostics)
