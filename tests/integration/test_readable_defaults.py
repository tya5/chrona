"""Readable defaults (#483) and the dashed as-of line (#423), checked on completed paint."""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path

from PIL import Image
import pytest
import yaml

from chrona.app.cli import main
from tests.support.preset_checks import MINIMUM_BAND_CONTRAST, band_contrasts as _band_contrasts, primitives as _primitives

ROOT = Path(__file__).resolve().parents[2]
PUBLIC_SCENES = sorted(ROOT.glob("examples/*/generated/*.scene.json"))
SHIPPED_THEMES = sorted(ROOT.glob("examples/*/themes/*.yaml")) + sorted(
    ROOT.glob("src/chrona/resources/presets/bundles/*/theme.yaml"))


def _assert_marks_inside_timeline(surface: dict) -> None:
    timeline = next(slot for slot in surface["slots"] if slot["id"] == "timeline")["bounds"]
    left, right = timeline["inline"], timeline["inline"] + timeline["inlineSize"]
    scale = surface["scale"]
    assert left <= scale["rangeStart"] < scale["rangeEnd"] <= right
    assert scale["origin"] == scale["rangeStart"]
    marks = [item for item in surface["primitives"]
             if item.get("purpose") in {"planned", "actual", "missingActual"}]
    assert marks
    for mark in marks:
        bounds = mark["bounds"]
        assert bounds["inline"] >= left - 0.01, mark["id"]
        assert bounds["inline"] + bounds["inlineSize"] <= right + 0.01, mark["id"]


def _assert_as_of_label_outside_axis(surface: dict) -> None:
    axis = next(slot for slot in surface["slots"] if slot["id"] == "timeline-axis")["bounds"]
    timeline = next(slot for slot in surface["slots"] if slot["id"] == "timeline")["bounds"]
    label_boxes = [item["bounds"] for item in surface["primitives"]
                   if item.get("id") in {"as-of-label", "chip:as-of-label"}]
    assert label_boxes

    def intersects(left: dict, right: dict) -> bool:
        return (left["inline"] < right["inline"] + right["inlineSize"]
                and right["inline"] < left["inline"] + left["inlineSize"]
                and left["block"] < right["block"] + right["blockSize"]
                and right["block"] < left["block"] + left["blockSize"])

    obstacles = [item for item in surface["primitives"]
                 if item.get("purpose") in {"axis-label", "axis-band", "planned", "actual", "missingActual"}]
    for label in label_boxes:
        assert timeline["inline"] <= label["inline"]
        assert label["inline"] + label["inlineSize"] <= timeline["inline"] + timeline["inlineSize"]
        assert timeline["block"] <= label["block"]
        assert label["block"] + label["blockSize"] <= timeline["block"] + timeline["blockSize"]
        assert not intersects(label, axis), label
        assert not [item["id"] for item in obstacles if intersects(label, item["bounds"])], label


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


@pytest.mark.parametrize("scene_path", PUBLIC_SCENES, ids=lambda path: f"{path.parent.parent.name}/{path.stem}")
def test_public_axis_band_is_distinct_from_group_and_row_bands(scene_path: Path) -> None:
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    weak = [item for item in _band_contrasts(scene) if item[2] < MINIMUM_BAND_CONTRAST]
    assert not weak


CATALOGUE_PRESETS = [entry["id"] for entry in yaml.safe_load(
    (ROOT / "src/chrona/resources/presets/library.yaml").read_text(encoding="utf-8"))["entries"]]


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
    assert _source_terminal_shape(theme_path) in {"circle", "none", None}  # `none` (#1105) is no mark


def test_public_relations_do_not_start_with_their_target_arrowhead() -> None:
    for scene_path in PUBLIC_SCENES:
        scene = json.loads(scene_path.read_text(encoding="utf-8"))
        for primitive in _primitives(scene):
            start, end = primitive.get("markerStart"), primitive.get("markerEnd")
            if start and end:
                assert start["outline"] != end["outline"], (scene_path.name, primitive["id"])


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
    output = capsys.readouterr()
    assert output.err == ""
    envelope = json.loads(output.out)
    assert envelope["status"] == "ok" and envelope["diagnostics"] == []
    warnings = envelope["warnings"]
    collisions = [item for item in warnings if item["code"] == "W_PRESENTATION_SCALE_NOT_SEPARABLE"]
    assert [(item["values"], item["vision"], item["deltaE"]) for item in collisions] == [(["bus", "launch"], "normal", 0.0)]


def _assert_automatic_default_keeps_plot_names_and_row_guides(scene: dict, svg: str) -> None:
    surface = scene["surfaces"][0]
    allowed_layout_warnings = {"W_LAYOUT_ACTUAL_INCOMPLETE", "W_LAYOUT_LABEL_SUPPRESSED"}
    assert not [item for item in scene["diagnostics"]
                if item.startswith("W_LAYOUT_")
                and item.split(":", 1)[0] not in allowed_layout_warnings]
    _assert_marks_inside_timeline(surface)
    _assert_as_of_label_outside_axis(surface)
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


def test_as_of_no_fit_keeps_rule_and_omits_label(tmp_path, monkeypatch) -> None:
    import chrona.presentation.layout.asof_label as asof_label

    starter = tmp_path / "starter"
    monkeypatch.setattr(sys, "argv", ["chrona", "init", str(starter)])
    main()
    # The member-label module imports the candidate search at call time, so the patch target is its owner.
    monkeypatch.setattr(asof_label, "find_asof_label_candidate", lambda *args, **kwargs: None)
    scene, svg_path = _render_project(tmp_path, monkeypatch, "as-of-no-fit",
                                      starter / "project.yaml", starter / "actual.yaml")
    primitives = {item["id"]: item for item in _primitives(scene)}
    assert "W_LAYOUT_LABEL_SUPPRESSED:as-of-label" in scene["diagnostics"]
    assert "as-of" in primitives
    assert "as-of-label" not in primitives
    assert "chip:as-of-label" not in primitives
    svg_ids = {value for element in ET.fromstring(svg_path.read_text(encoding="utf-8")).iter()
               for value in (element.get("id"), element.get("data-scene-id")) if value}
    assert "as-of" in svg_ids
    assert "as-of-label" not in svg_ids
    assert "chip:as-of-label" not in svg_ids


@pytest.mark.parametrize("source", ["packaged", "corpus"])
def test_readable_default_views_render_task_and_plan_columns(tmp_path, monkeypatch, source) -> None:
    packaged = ROOT / "src/chrona/resources/presets/bundles/editorial-readable-default/view.yaml"
    mirror = ROOT / "examples/halcyon-1/views/editorial-readable-default.yaml"
    view = packaged if source == "packaged" else mirror
    scene, _ = _render_project(tmp_path, monkeypatch, "halcyon-mirror-default",
                               ROOT / "examples/halcyon-1/project.yaml",
                               ROOT / "examples/halcyon-1/actual.yaml",
                               "--view", str(view))
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


def test_public_halcyon_03_lane_table_uses_member_titles_without_item_count() -> None:
    scene_path = ROOT / "examples/halcyon-1/generated/03-launch-campaign.scene.json"
    svg_path = ROOT / "examples/halcyon-1/generated/03-launch-campaign.svg"
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    primitives = _primitives(scene)
    labels = [item["text"] for item in primitives
              if item.get("purpose") == "table-cell" and item["id"].endswith(":Lane")]
    svg_text = "".join(ET.fromstring(svg_path.read_text(encoding="utf-8")).itertext())
    assert labels
    assert all(label.strip() for label in labels)
    assert all(not label.startswith("Lane ") for label in labels)
    assert len(labels) == len(set(labels))
    assert all(label in svg_text for label in labels)
    assert not any(item.get("purpose") == "table-column-label" and item.get("text") == "Items"
                   for item in primitives)


@pytest.mark.parametrize("slide", ("02-programme-board", "12-glyph-gates"))
def test_wallboard_lane_table_keeps_the_bus_test_relation(slide: str) -> None:
    scene = json.loads((ROOT / f"examples/halcyon-1/generated/{slide}.scene.json").read_text(encoding="utf-8"))
    primitives = _primitives(scene)
    lane_labels = [item["text"] for item in primitives
                   if item.get("purpose") == "table-cell" and item["id"].endswith(":Lane")]
    route_id = ('relation:bustest-integration:review-lane:["generated","bus","pdr"]:'
                'bus-test:review-lane:["generated","ait","integration"]:integration')
    assert lane_labels and all(label.strip() and not label.startswith("Lane ") for label in lane_labels)
    assert [item["id"] for item in primitives if item["id"].startswith("relation:bustest-integration:")] == [route_id]
    svg_path = ROOT / f"examples/halcyon-1/generated/{slide}.svg"
    svg_ids = {value for element in ET.fromstring(svg_path.read_text(encoding="utf-8")).iter()
               for value in (element.get("id"), element.get("data-scene-id")) if value}
    assert route_id in svg_ids


def test_public_wallboard_keeps_station_note_when_title_width_changes() -> None:
    scene = json.loads((ROOT / "examples/halcyon-1/generated/02-programme-board.scene.json").read_text(encoding="utf-8"))
    primitives = _primitives(scene)
    assert any(item.get("id") == "annotation-text:station-note" for item in primitives)
    assert any(item.get("id") == "annotation-box:station-note" for item in primitives)
    assert "W_LAYOUT_ANNOTATION_CANDIDATE_FALLBACK:station-note:plot-no-tail" in scene["diagnostics"]


@pytest.mark.parametrize("slide", ("02-programme-board", "11-overlay-briefing", "12-glyph-gates"))
def test_wallboard_fill_counts_names_that_cannot_stay_near_their_marks(slide: str) -> None:
    scene = json.loads((ROOT / f"examples/halcyon-1/generated/{slide}.scene.json").read_text(encoding="utf-8"))
    surface = scene["surfaces"][0]
    packed = len(surface["laneMembers"])
    names = [item for item in _primitives(scene) if item.get("purpose") == "member-label"]
    shown = len(names)
    suppressed = [item for item in scene["diagnostics"]
                  if item.startswith("W_LAYOUT_LABEL_SUPPRESSED:member-label:")]
    assert packed == shown + len(suppressed)
    assert shown > 0 and len(suppressed) == len(set(suppressed))
    assert not any(item.get("purpose") == "member-label-leader" for item in _primitives(scene))
    for box in (item for item in _primitives(scene) if item["id"].startswith("annotation-box:")):
        left, top = box["bounds"]["inline"], box["bounds"]["block"]
        right = left + box["bounds"]["inlineSize"]
        bottom = top + box["bounds"]["blockSize"]
        for name in names:
            bounds = name["bounds"]
            assert not (left < bounds["inline"] + bounds["inlineSize"]
                        and bounds["inline"] < right
                        and top < bounds["block"] + bounds["blockSize"]
                        and bounds["block"] < bottom), (slide, box["id"], name["id"])


def test_programme_board_wallboard_profile_is_context_specific_and_complete() -> None:
    layouts = ROOT / "examples/halcyon-1/layouts"
    shared = yaml.safe_load((layouts / "wallboard.yaml").read_text(encoding="utf-8"))
    programme = yaml.safe_load((layouts / "wallboard-programme-board.yaml").read_text(encoding="utf-8"))
    assert shared["id"] == "wallboard"
    assert shared["root"]["children"][1]["inlineSize"] == {
        "minmax": {"min": "content", "max": {"fr": 2}}
    }
    assert programme["version"] == "chrona/layout-profile/v0.10"
    assert programme["id"] == "wallboard-programme-board"
    assert "root" in programme and "extends" not in programme and "overrides" not in programme
    assert programme["root"]["children"][1]["inlineSize"] == {
        "minmax": {"min": "content", "max": {"fr": 2}}
    }
    shared_copy = deepcopy(programme)
    shared_copy["id"] = "wallboard"
    assert programme["reviewSurface"]["rowDistribution"] == "fill"
    assert shared["reviewSurface"]["rowDistribution"] == "pack"
    shared_copy["reviewSurface"]["rowDistribution"] = "pack"
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


def test_bundled_default_closed_day_fill_matches_legend_without_outlines(tmp_path, monkeypatch) -> None:
    starter = tmp_path / "starter-closed-day"
    monkeypatch.setattr(sys, "argv", ["chrona", "init", str(starter)])
    main()
    # The starter declares no calendar and so shades no closed day (#893); declare one to see the band.
    project_file = starter / "project.yaml"
    project_file.write_text(project_file.read_text(encoding="utf-8").replace(
        "project: {id: my-first-plan, title: My first plan}",
        "project: {id: my-first-plan, title: My first plan, calendar: standard}\n"
        "calendars: {standard: {working_days: [mon, tue, wed, thu, fri]}}"), encoding="utf-8")
    scene, svg_path = _render_project(tmp_path, monkeypatch, "starter-closed-day",
                                      starter / "project.yaml", starter / "actual.yaml")
    primitives = _primitives(scene)
    closed_days = [item for item in primitives if item.get("visualRole") == "calendar-closed"]
    legend = next(item for item in primitives
                  if item.get("sourceKind") == "legend" and item.get("sourceRef") == "calendar-closed")

    assert closed_days
    assert all("fill" in item["paint"] and "stroke" not in item["paint"] for item in closed_days)
    assert all(item["paint"]["opacity"] == pytest.approx(0.12) for item in closed_days)
    assert legend["paint"].get("fill") == closed_days[0]["paint"]["fill"]
    assert "stroke" not in legend["paint"]
    assert legend["paint"]["opacity"] == pytest.approx(closed_days[0]["paint"]["opacity"])

    svg = svg_path.read_text(encoding="utf-8")
    root = ET.fromstring(svg)
    svg_closed = [element for element in root.iter()
                  if element.get("data-purpose") == "calendar-closed"]
    svg_legend = next(element for element in root.iter()
                      if element.get("data-scene-id", "").startswith("legend-swatch:calendar-closed"))
    assert svg_closed
    assert all(element.get("fill") != "none" and element.get("stroke") is None for element in svg_closed)
    assert all(float(element.get("opacity", "1")) == pytest.approx(0.12) for element in svg_closed)
    assert svg_legend.get("fill") == svg_closed[0].get("fill")
    assert svg_legend.get("stroke") is None
    assert float(svg_legend.get("opacity", "1")) == pytest.approx(0.12)

    png_path = tmp_path / "starter-closed-day.png"
    monkeypatch.setattr(sys, "argv", ["chrona", "render", str(starter / "project.yaml"),
                                       "--actual", str(starter / "actual.yaml"), "--output", str(png_path)])
    main()
    swatch_bounds = legend["bounds"]
    with Image.open(png_path) as raster:
        pixels = raster.convert("RGB")
        samples = (swatch_bounds, closed_days[0]["bounds"])
        observed = [pixels.getpixel((round(bounds["inline"] + bounds["inlineSize"] / 2),
                                     round(bounds["block"] + bounds["blockSize"] / 2)))
                    for bounds in samples]
    canvas = scene["surfaces"][0]["canvasPaint"]["fill"].lstrip("#")
    fill = legend["paint"]["fill"].lstrip("#")
    opacity = legend["paint"]["opacity"]
    expected = tuple(round(opacity * int(fill[index:index + 2], 16)
                           + (1 - opacity) * int(canvas[index:index + 2], 16))
                     for index in (0, 2, 4))
    assert all(all(abs(actual - wanted) <= 2 for actual, wanted in zip(pixel, expected))
               for pixel in observed)

    bundled_theme = yaml.safe_load((ROOT / "src/chrona/resources/presets/bundles/editorial-readable-default/theme.yaml").read_text(encoding="utf-8"))["body"]
    halcyon_theme = yaml.safe_load((ROOT / "examples/halcyon-1/themes/editorial-readable-default.yaml").read_text(encoding="utf-8"))["body"]
    for body in (bundled_theme, halcyon_theme):
        role = body["roles"]["calendar-closed"]
        assert role["backgroundTreatment"] == "fill"
        assert "strokeWidth" not in role
        assert body["values"]["opacity.calendar-closed"]["value"] == pytest.approx(0.12)
        assert "calendar-closed.stroke" not in body["colorBindings"]


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
