"""Readable defaults (#483) and the dashed as-of line (#423), checked on completed paint."""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from chrona.app.cli import main

ROOT = Path(__file__).resolve().parents[2]
PUBLIC_SCENES = sorted(ROOT.glob("examples/*/generated/*.scene.json"))
SHIPPED_THEMES = sorted(ROOT.glob("examples/*/themes/*.yaml")) + sorted(
    ROOT.glob("src/chrona/resources/presets/bundles/*/theme.yaml"))
MINIMUM_BAND_CONTRAST = 1.15


def _primitives(scene: dict) -> list[dict]:
    found: list[dict] = []

    def walk(value):
        if isinstance(value, dict):
            if isinstance(value.get("id"), str) and "paint" in value:
                found.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(scene)
    return found


def _rgb(colour: str) -> tuple[float, float, float]:
    colour = colour.lstrip("#")
    red, green, blue = (int(colour[index:index + 2], 16) / 255 for index in (0, 2, 4))
    return red, green, blue


def _composite(paint: dict, canvas: tuple[float, float, float]) -> tuple[float, float, float]:
    opacity = float(paint.get("opacity", 1.0))
    red, green, blue = (opacity * part + (1 - opacity) * ground for part, ground in zip(_rgb(paint["fill"]), canvas))
    return red, green, blue


def _luminance(rgb: tuple[float, float, float]) -> float:
    linear = [part / 12.92 if part <= 0.04045 else ((part + 0.055) / 1.055) ** 2.4 for part in rgb]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
    high, low = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _band_contrasts(scene: dict) -> list[tuple[str, str, float]]:
    results = []
    for surface in scene.get("surfaces", ()):
        canvas = _rgb(surface.get("canvasPaint", {}).get("fill", "#FFFFFF"))
        primitives = _primitives(surface)
        axis = [item for item in primitives if item.get("visualRole") == "axis-band-decoration" and "fill" in item["paint"]]
        bands = [item for item in primitives
                 if item.get("visualRole") in {"group-band", "row-band"} and "fill" in item["paint"]]
        for axis_band in axis:
            for band in bands:
                results.append((axis_band["id"], band["id"], _contrast(_composite(axis_band["paint"], canvas),
                                                                    _composite(band["paint"], canvas))))
    return results


def _render_project(tmp_path: Path, monkeypatch, name: str, project: Path,
                    actual: Path | None = None, *extra: str) -> tuple[dict, Path]:
    scene_path = tmp_path / f"{name}.scene.json"
    argv = ["chrona", "render", str(project)]
    if actual is not None:
        argv.extend(("--actual", str(actual)))
    argv.extend((*extra,
        "--output", str(tmp_path / f"{name}.svg"), "--emit-scene", str(scene_path),
    ))
    monkeypatch.setattr(sys, "argv", argv)
    main()
    return json.loads(scene_path.read_text(encoding="utf-8")), tmp_path / f"{name}.svg"


def _render(tmp_path: Path, monkeypatch, name: str, *extra: str) -> dict:
    scene, _ = _render_project(tmp_path, monkeypatch, name,
                               ROOT / "examples/halcyon-1/project.yaml",
                               ROOT / "examples/halcyon-1/actual.yaml", *extra)
    return scene


def _copied_preset(tmp_path: Path, monkeypatch, preset_id: str) -> Path:
    destination = tmp_path / preset_id
    monkeypatch.setattr(sys, "argv", ["chrona", "preset", "copy", preset_id, "--output", str(destination)])
    main()
    return destination / "preset.yaml"


@pytest.mark.parametrize("scene_path", PUBLIC_SCENES, ids=lambda path: f"{path.parent.parent.name}/{path.stem}")
def test_public_axis_band_is_distinct_from_group_and_row_bands(scene_path: Path) -> None:
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    weak = [item for item in _band_contrasts(scene) if item[2] < MINIMUM_BAND_CONTRAST]
    assert not weak


def test_default_draft_and_presets_draw_a_distinct_axis_band(tmp_path, monkeypatch) -> None:
    library = yaml.safe_load((ROOT / "src/chrona/resources/presets/library.yaml").read_text(encoding="utf-8"))
    scenes = {"default": _render(tmp_path, monkeypatch, "default")}
    for entry in library["entries"]:
        preset = _copied_preset(tmp_path, monkeypatch, entry["id"])
        scenes[entry["id"]] = _render(tmp_path, monkeypatch, entry["id"], "--preset", str(preset))
    for name, scene in scenes.items():
        contrasts = _band_contrasts(scene)
        assert any(axis_id.startswith("axis-band") for axis_id, _, _ in contrasts) or not contrasts, name
        assert all(ratio >= MINIMUM_BAND_CONTRAST for _, _, ratio in contrasts), name


def _source_terminal_shape(theme_path: Path) -> str | None:
    body = yaml.safe_load(theme_path.read_text(encoding="utf-8"))["body"]
    role = body.get("roles", {}).get("relationSourceTerminal")
    if role is None:
        base = body.get("extends")
        return _source_terminal_shape(theme_path.parent / base["path"]) if base else None
    token = body["values"][role["marker"]]
    return token["value"]["shape"]


@pytest.mark.parametrize("theme_path", SHIPPED_THEMES, ids=lambda path: f"{path.parent.parent.name}/{path.parent.name}/{path.stem}")
def test_every_shipped_theme_starts_relations_with_a_circle_or_no_mark(theme_path: Path) -> None:
    assert _source_terminal_shape(theme_path) in {"circle", None}


def test_public_relations_do_not_start_with_their_target_arrowhead() -> None:
    for scene_path in PUBLIC_SCENES:
        scene = json.loads(scene_path.read_text(encoding="utf-8"))
        for primitive in _primitives(scene):
            start, end = primitive.get("markerStart"), primitive.get("markerEnd")
            if start and end:
                assert start["outline"] != end["outline"], (scene_path.name, primitive["id"])


def test_print_mono_separates_slips_and_as_of_in_greyscale(tmp_path, monkeypatch) -> None:
    preset = _copied_preset(tmp_path, monkeypatch, "print-mono")
    scene = _render(tmp_path, monkeypatch, "print-mono", "--preset", str(preset))
    primitives = _primitives(scene)
    # Lane Views put signed finish deltas in the member label, so they no
    # longer emit separate variance-* paint primitives. Preserve the user
    # visible slip check against those completed labels.
    deltas = [item for item in primitives if item.get("purpose") == "finish-delta"]
    assert not deltas  # finish deltas are composed into the lane member label
    lane_labels = [item.get("text", "") for item in primitives
                   if item.get("id", "").startswith("member-label:")]
    assert any(text.endswith("d") and ("+" in text or "−" in text or "-" in text)
               for text in lane_labels)
    as_of = [item for item in primitives if item.get("visualRole") == "as-of" and "stroke" in item["paint"]]
    grid = [item for item in primitives if item.get("purpose") == "axis-grid"]
    assert as_of and all(item["paint"]["dash"] for item in as_of)
    assert grid and not any(item["paint"].get("dash") for item in grid)


def test_no_committed_scene_ships_an_inseparable_colour_scale() -> None:
    """#421: every committed colour scale separates its domain."""
    for scene_path in PUBLIC_SCENES:
        diagnostics = json.loads(scene_path.read_text(encoding="utf-8")).get("diagnostics", [])
        assert not [item for item in diagnostics if item.startswith("W_PRESENTATION_SCALE_NOT_SEPARABLE")], scene_path


def test_cli_names_colliding_scale_values(tmp_path, monkeypatch, capsys) -> None:
    scheme = yaml.safe_load((ROOT / "examples/halcyon-1/schemes/control-room-dark.yaml").read_text(encoding="utf-8"))
    scheme["body"]["categories"]["launch"] = scheme["body"]["categories"]["bus"]
    scheme_path = tmp_path / "collide.yaml"
    scheme_path.write_text(yaml.safe_dump(scheme, sort_keys=False), encoding="utf-8")
    capsys.readouterr()
    _render(tmp_path, monkeypatch, "collide", "--view", str(ROOT / "examples/halcyon-1/views/02-programme-board.yaml"),
            "--theme", str(ROOT / "examples/halcyon-1/themes/wallboard.yaml"), "--scheme", str(scheme_path),
            "--layout", str(ROOT / "examples/halcyon-1/layouts/wallboard.yaml"))
    warnings = [json.loads(line) for line in capsys.readouterr().err.splitlines() if line.startswith("{")]
    collisions = [item for item in warnings if item["code"] == "W_PRESENTATION_SCALE_NOT_SEPARABLE"]
    assert [(item["values"], item["vision"], item["deltaE"]) for item in collisions] == [(["bus", "launch"], "normal", 0.0)]


def _assert_automatic_default_keeps_plot_names_and_row_guides(scene: dict, svg: str) -> None:
    surface = scene["surfaces"][0]
    timeline = next(slot for slot in surface["slots"] if slot["id"] == "timeline")["bounds"]
    rows = {row["id"]: row["bounds"] for row in surface["rows"]}
    primitives = {item["id"]: item for item in _primitives(scene)}
    bands = {key: item for key, item in primitives.items() if key.startswith("row-band:")}
    planned = {key: item for key, item in primitives.items() if key.startswith("planned:")}
    labels = {key: item for key, item in primitives.items() if key.startswith("member-label:")}
    suppressed = {diagnostic.split("W_LAYOUT_LABEL_SUPPRESSED:", 1)[1]
                  for diagnostic in scene["diagnostics"]
                  if diagnostic.startswith("W_LAYOUT_LABEL_SUPPRESSED:member-label:")}
    assert rows and bands and planned
    assert all(item["bounds"]["inline"] + item["bounds"]["inlineSize"] >=
               timeline["inline"] + timeline["inlineSize"] - 0.01
               for item in bands.values())
    edges = {round(item["bounds"]["block"], 3) for item in bands.values()} | {
        round(item["bounds"]["block"] + item["bounds"]["blockSize"], 3)
        for item in bands.values()
    }
    assert all(round(bounds["block"], 3) in edges or
               round(bounds["block"] + bounds["blockSize"], 3) in edges
               for bounds in rows.values())
    assert len(labels) + len(suppressed) == len(planned)
    assert suppressed.isdisjoint(labels)
    assert svg.count('id="row-band:') == len(bands)
    assert all(f'id="{key}"' in svg for key in labels)
    assert all(f'id="{key}"' not in svg for key in suppressed)


def test_bundled_default_uses_task_and_planned_date_columns(tmp_path, monkeypatch) -> None:
    scene, svg_path = _render_project(
        tmp_path, monkeypatch, "bundled-default",
        ROOT / "examples/halcyon-1/project.yaml",
        ROOT / "examples/halcyon-1/actual.yaml",
    )
    primitives = {item["id"]: item for item in _primitives(scene)}
    svg = svg_path.read_text(encoding="utf-8")
    _assert_automatic_default_keeps_plot_names_and_row_guides(scene, svg)
    svg_ids = {value for element in ET.fromstring(svg).iter()
               for value in (element.get("id"), element.get("data-scene-id")) if value}
    columns = {item["text"] for item in primitives.values()
               if item.get("purpose") == "table-column-label"}
    cells = {item["id"]: item["text"] for item in primitives.values()
             if item.get("purpose") == "table-cell"}
    assert columns == {"Task", "Plan"}
    assert len([key for key in cells if key.endswith(":Task")]) == 26
    assert len([key for key in cells if key.endswith(":Plan")]) == 26
    assert all(cells[key].strip() for key in cells if key.endswith(":Plan"))
    assert "Owner" not in columns
    assert "Launch campaign" in {text for key, text in cells.items() if key.endswith(":Task")}
    assert all(key in svg_ids for key in primitives if key.startswith("cell:"))


def test_init_starter_default_uses_task_and_planned_date_columns(tmp_path, monkeypatch) -> None:
    starter = tmp_path / "starter"
    monkeypatch.setattr(sys, "argv", ["chrona", "init", str(starter)])
    main()
    scene, svg_path = _render_project(tmp_path, monkeypatch, "starter-default",
                                      starter / "project.yaml", starter / "actual.yaml")
    primitives = {item["id"]: item for item in _primitives(scene)}
    svg = svg_path.read_text(encoding="utf-8")
    _assert_automatic_default_keeps_plot_names_and_row_guides(scene, svg)
    svg_ids = {value for element in ET.fromstring(svg).iter()
               for value in (element.get("id"), element.get("data-scene-id")) if value}
    columns = {item["text"] for item in primitives.values()
               if item.get("purpose") == "table-column-label"}
    cells = {item["id"]: item["text"] for item in primitives.values()
             if item.get("purpose") == "table-cell"}
    assert columns == {"Task", "Plan"}
    assert len([key for key in cells if key.endswith(":Task")]) == 3
    assert len([key for key in cells if key.endswith(":Plan")]) == 3
    assert all(key in svg_ids for key in primitives if key.startswith("cell:"))
    assert "Owner" not in svg


def test_halcyon_readable_default_mirror_renders_task_and_plan_columns(tmp_path, monkeypatch) -> None:
    packaged = ROOT / "src/chrona/resources/presets/bundles/editorial-readable-default/view.yaml"
    mirror = ROOT / "examples/halcyon-1/views/editorial-readable-default.yaml"
    assert packaged.read_bytes() == mirror.read_bytes()
    scene, _ = _render_project(tmp_path, monkeypatch, "halcyon-mirror-default",
                               ROOT / "examples/halcyon-1/project.yaml",
                               ROOT / "examples/halcyon-1/actual.yaml",
                               "--view", str(mirror))
    primitives = _primitives(scene)
    columns = {item["text"] for item in primitives
               if item.get("purpose") == "table-column-label"}
    assert columns == {"Task", "Plan"}
    assert "Owner" not in columns


def test_attached_milestones_default_keeps_host_title_visible(tmp_path, monkeypatch) -> None:
    example = ROOT / "examples/attached-milestones"
    scene, svg_path = _render_project(tmp_path, monkeypatch, "attached-default",
                                      example / "project.yaml", example / "actual.yaml")
    primitives = _primitives(scene)
    task_cells = [item["text"] for item in primitives
                  if item.get("purpose") == "table-cell" and item["id"].endswith(":Task")]
    svg_text = "".join(ET.fromstring(svg_path.read_text(encoding="utf-8")).itertext())
    assert "Launch campaign" in task_cells
    assert "Launch campaign" in svg_text


def test_public_halcyon_03_lane_table_uses_stable_nonblank_lane_identity() -> None:
    scene_path = ROOT / "examples/halcyon-1/generated/03-launch-campaign.scene.json"
    svg_path = ROOT / "examples/halcyon-1/generated/03-launch-campaign.svg"
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    primitives = _primitives(scene)
    labels = [item["text"] for item in primitives
              if item.get("purpose") == "table-cell" and item["id"].endswith(":Lane")]
    svg_text = "".join(ET.fromstring(svg_path.read_text(encoding="utf-8")).itertext())
    assert labels
    assert all(label.strip() for label in labels)
    assert all(label.startswith("Lane ") for label in labels)
    assert len(labels) == len(set(labels))
    assert all(label in svg_text for label in labels)


@pytest.mark.parametrize("slide", ("02-programme-board", "12-glyph-gates"))
def test_wallboard_lane_table_keeps_the_bus_test_relation(slide: str) -> None:
    scene = json.loads((ROOT / f"examples/halcyon-1/generated/{slide}.scene.json").read_text(encoding="utf-8"))
    primitives = _primitives(scene)
    lane_labels = [item["text"] for item in primitives
                   if item.get("purpose") == "table-cell" and item["id"].endswith(":Lane")]
    group_headers = {item["text"] for item in primitives if item.get("purpose") == "group-header"}
    route_id = ('relation:bustest-integration:review-lane:["generated","bus","pdr"]:'
                'bus-test:review-lane:["generated","ait","integration"]:integration')
    assert lane_labels and all(label.strip() and label not in group_headers for label in lane_labels)
    assert [item["id"] for item in primitives if item["id"].startswith("relation:bustest-integration:")] == [route_id]
    svg_path = ROOT / f"examples/halcyon-1/generated/{slide}.svg"
    svg_ids = {value for element in ET.fromstring(svg_path.read_text(encoding="utf-8")).iter()
               for value in (element.get("id"), element.get("data-scene-id")) if value}
    assert route_id in svg_ids


def test_programme_board_wallboard_profile_is_context_specific_and_complete() -> None:
    layouts = ROOT / "examples/halcyon-1/layouts"
    shared = yaml.safe_load((layouts / "wallboard.yaml").read_text(encoding="utf-8"))
    programme = yaml.safe_load((layouts / "wallboard-programme-board.yaml").read_text(encoding="utf-8"))
    assert shared["id"] == "wallboard"
    assert shared["root"]["children"][1]["inlineSize"] == {
        "minmax": {"min": "content", "max": {"fr": 2}}
    }
    assert programme["version"] == "chrona/layout-profile/v0.9"
    assert programme["id"] == "wallboard-programme-board"
    assert "root" in programme and "extends" not in programme and "overrides" not in programme
    assert programme["root"]["children"][1]["inlineSize"] == {
        "minmax": {"min": {"fixed": 300}, "max": {"fr": 2}}
    }
    shared_copy = deepcopy(programme)
    shared_copy["id"] = "wallboard"
    shared_copy["root"]["children"][1]["inlineSize"] = {
        "minmax": {"min": "content", "max": {"fr": 2}}
    }
    assert shared_copy == shared

    contexts = ROOT / "examples/halcyon-1/contexts"
    for context_name in ("02-programme-board", "12-glyph-gates"):
        context = yaml.safe_load((contexts / f"{context_name}.yaml").read_text(encoding="utf-8"))
        assert context["body"]["layout"] == {
            "id": "wallboard-programme-board",
            "kind": "layout-profile",
            "store": {"provider": "local", "identity": "halcyon-1-example"},
            "address": "layouts/wallboard-programme-board.yaml",
            "revision": {"token": "example-v1"},
        }
    for context_name in ("04-tvac-slip", "07-replan-baseline", "15-gallery-image-notes"):
        context = yaml.safe_load((contexts / f"{context_name}.yaml").read_text(encoding="utf-8"))
        assert context["body"]["layout"] == {
            "id": "wallboard",
            "kind": "layout-profile",
            "store": {"provider": "local", "identity": "halcyon-1-example"},
            "address": "layouts/wallboard.yaml",
            "revision": {"token": "example-v1"},
        }


def test_pinned_default_draft_guides_every_bar_across_the_plot_and_names_it_at_its_end(tmp_path, monkeypatch) -> None:
    """#483 item 2: stripes cross the whole plot; names are declared at the bar end, in the row.

    This is a property of the `default-draft` View file itself, not of
    "whichever preset the wheel currently bundles as default" -- #383/#429
    made Editorial the bundled default, and Editorial deliberately has no
    row stripes (#425: "only the columns carry ground; the rows carry
    none") and places labels in the table rather than the plot. Render
    `default-draft` explicitly against its own original Theme/Layout/Color
    Scheme so this test keeps proving what it always proved.
    """
    view = yaml.safe_load((ROOT / "examples/halcyon-1/views/default-draft.yaml").read_text(encoding="utf-8"))["body"]
    labels = view["visibility"]["labels"]
    assert (labels["placement"], labels["side"]) == ("plot", "end")
    assert view["visibility"]["fallback"]["labels"] == ["end", "start", "suppress"]
    assert view["backgroundDecoration"]["rows"] == "alternate"
    scene = _render(tmp_path, monkeypatch, "default-draft",
                    "--view", str(ROOT / "examples/halcyon-1/views/default-draft.yaml"),
                    "--theme", str(ROOT / "examples/halcyon-1/themes/briefing.yaml"),
                    "--scheme", str(ROOT / "examples/halcyon-1/schemes/mission-light.yaml"),
                    "--layout", str(ROOT / "examples/halcyon-1/layouts/briefing.yaml"))
    surface = scene["surfaces"][0]
    timeline = next(slot for slot in surface["slots"] if slot["id"] == "timeline")["bounds"]
    rows = {row["id"]: row["bounds"] for row in surface["rows"]}
    primitives = {item["id"]: item for item in _primitives(scene)}
    stripes = [item["bounds"] for key, item in primitives.items() if key.startswith("row-band:")]
    assert stripes and all(stripe["inline"] + stripe["inlineSize"] >= timeline["inline"] + timeline["inlineSize"] - 0.01
                           for stripe in stripes)
    # Every row is striped or shares an edge with a stripe, so each bar has a guide to the plot's end.
    edges = {round(stripe["block"], 3) for stripe in stripes} | {round(stripe["block"] + stripe["blockSize"], 3) for stripe in stripes}
    assert all(round(bounds["block"], 3) in edges or round(bounds["block"] + bounds["blockSize"], 3) in edges
               for bounds in rows.values())
    # #488: every member label is at its bar's end or start inside its own
    # row band, or it is reported suppressed; none reads as the adjacent row's.
    suppressed = [item for item in scene["diagnostics"] if item.startswith("W_LAYOUT_LABEL_SUPPRESSED:member-label:")]
    member_labels = [key for key in primitives if key.startswith("member-label:")
                     and f"W_LAYOUT_LABEL_SUPPRESSED:{key}" not in suppressed]
    for key in member_labels:
        object_id = key.split(":")[1]
        label, row = primitives[key]["bounds"], rows[object_id]
        host = primitives[f"planned:{object_id}:{object_id}"]["bounds"]
        assert row["block"] - 0.01 <= label["block"] and label["block"] + label["blockSize"] <= row["block"] + row["blockSize"] + 0.01, key
        assert (label["inline"] >= host["inline"] + host["inlineSize"] - 0.5
                or label["inline"] + label["inlineSize"] <= host["inline"] + 0.5), key
    assert len(member_labels) + len(suppressed) == 29  # every selected item: 28 named before #488, 1 suppressed
