"""Readable defaults (#483) and the dashed as-of line (#423), checked on completed paint."""
from __future__ import annotations

import json
import sys
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


def _render(tmp_path: Path, monkeypatch, name: str, *extra: str) -> dict:
    scene_path = tmp_path / f"{name}.scene.json"
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render", str(ROOT / "examples/halcyon-1/project.yaml"),
        "--actual", str(ROOT / "examples/halcyon-1/actual.yaml"), *extra,
        "--output", str(tmp_path / f"{name}.svg"), "--emit-scene", str(scene_path),
    ])
    main()
    return json.loads(scene_path.read_text(encoding="utf-8"))


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
    luminance = {}
    for primitive in primitives:
        role = primitive.get("visualRole", "")
        if role.startswith("variance-") and "fill" in primitive["paint"]:
            luminance.setdefault(role, _luminance(_rgb(primitive["paint"]["fill"])))
    assert {"variance-behind", "variance-on-track"} <= set(luminance)
    values = sorted(luminance.values())
    # Neighbouring states stay apart in greyscale by a WCAG contrast of at least 2.
    assert all((high + 0.05) / (low + 0.05) >= 2 for low, high in zip(values, values[1:]))
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


def test_default_draft_guides_every_bar_across_the_plot_and_names_it_at_its_end(tmp_path, monkeypatch) -> None:
    """#483 item 2: stripes cross the whole plot; names are declared at the bar end, in the row."""
    view = yaml.safe_load((ROOT / "examples/halcyon-1/views/default-draft.yaml").read_text(encoding="utf-8"))["body"]
    labels = view["visibility"]["labels"]
    assert (labels["placement"], labels["side"]) == ("plot", "end")
    assert view["visibility"]["fallback"]["labels"] == ["end", "start", "suppress"]
    assert view["backgroundDecoration"]["rows"] == "alternate"
    scene = _render(tmp_path, monkeypatch, "default")
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
    placed_at_end_in_row = 0
    member_labels = [key for key in primitives if key.startswith("member-label:")]
    for key in member_labels:
        object_id = key.split(":")[1]
        label, row = primitives[key]["bounds"], rows[object_id]
        host = primitives[f"planned:{object_id}:{object_id}"]["bounds"]
        if (row["block"] <= label["block"] and label["block"] + label["blockSize"] <= row["block"] + row["blockSize"] + 0.01
                and label["inline"] >= host["inline"] + host["inlineSize"] - 0.5):
            placed_at_end_in_row += 1
    # Measured at the I483-2 commit: 20 of 28; the rest are the plot-edge start
    # fallback (3) and side-search displacement out of the row (5), tracked by #488.
    assert placed_at_end_in_row >= 20 and len(member_labels) == 28
