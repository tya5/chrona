"""The wheel preset closes the same visible assets after copy and by name."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image
import pytest
import resvg_py
import yaml

from chrona.app.cli import main
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility
from chrona.usecases.preset_library import copy_builtin_preset


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "examples/controller-z/project.yaml"
FONTS = ROOT / "src/chrona/resources/fonts"


def _render(monkeypatch, project: Path, preset: str, output: Path,
            *, scene: Path | None = None, profile: str | None = None) -> None:
    args = ["chrona", "render", str(project), "--preset", preset]
    if profile is not None:
        args.extend(("--visual-profile", profile))
    args.extend(("--output", str(output)))
    if scene is not None:
        args.extend(("--emit-scene", str(scene)))
    monkeypatch.setattr(sys, "argv", args)
    main()


def test_builtin_catalogue_copy_and_no_asset_flag_render_are_visible_in_svg_and_png(tmp_path, monkeypatch):
    copied = copy_builtin_preset("technical-print", tmp_path / "copied")
    named_svg = tmp_path / "named.svg"
    copied_svg = tmp_path / "copied.svg"
    scene_path = tmp_path / "named.scene.json"
    _render(monkeypatch, PROJECT, "technical-print", named_svg, scene=scene_path)
    _render(monkeypatch, PROJECT, str(copied), copied_svg)

    svg = named_svg.read_bytes()
    assert svg == copied_svg.read_bytes()
    assert b"<pattern " in svg and b'patternTransform="translate(' in svg
    assert b"Planned" in svg and b"Actual" in svg
    scene = json.loads(scene_path.read_bytes())
    assert scene["version"] == "chrona/scene/v0.7"
    primitives = [item for surface in scene["surfaces"] for item in surface["primitives"]]
    assert any(item.get("visualRole") == "axis-band-decoration2" and item.get("pattern") for item in primitives)
    assert any(item.get("id", "").startswith("legend-swatch:milestone") and item.get("kind") == "Symbol"
               and len(item.get("symbol", {}).get("outline", ())) > 8 for item in primitives)  # the key is painted as the planned point (#499)
    assert any(item.get("id", "").startswith("legend-swatch:milestone") for item in primitives)
    pattern_id = next(item["id"] for item in primitives if item.get("visualRole") == "axis-band-decoration2"
                      and item.get("pattern"))
    contrast = [item for item in evaluate_scene_contrast(scene) if item.primitive_id == pattern_id]
    assert {(item.paint_channel, item.ground_kind) for item in contrast} == {
        ("fill", "canvas"), ("stroke", "pattern-substrate"), ("stroke", "canvas")}
    observations = [item for item in evaluate_scene_perceptibility(scene)
                    if item.code == "I_SCENE_PATTERN_PERCEPTIBILITY" and item.primitive_ids == (pattern_id,)]
    assert len(observations) == 1
    assert dict(observations[0].measured_facts)["densityBasisPoints"] == 1279

    png = tmp_path / "named.png"
    _render(monkeypatch, PROJECT, "technical-print", png,
            profile="chrona-output/visual/v0.7-png")
    rasterized_svg = resvg_py.svg_to_bytes(
        svg_string=svg.decode("utf-8"), dpi=96,
        font_files=[str(FONTS / name) for name in (
            "noto-sans-regular-v1.ttf", "noto-sans-bold-v1.ttf", "noto-sans-mono-regular-v1.ttf")],
        skip_system_fonts=True,
    )
    assert png.read_bytes() == rasterized_svg
    with Image.open(png) as image:
        image.load()
        assert image.width > 1000 and image.height > 500
        pattern_colors = {pixel[:3] for _count, pixel in image.crop((554, 118, 570, 135)).getcolors(maxcolors=100000)}
        assert (242, 242, 242) in pattern_colors and (216, 216, 216) in pattern_colors
        key = next(item for item in primitives if item.get("id", "").startswith("legend-swatch:milestone"))["bounds"]
        legend_glyph = image.crop((int(key["inline"]) - 1, int(key["block"]) - 1, int(key["inline"] + key["inlineSize"]) + 2,
                                   int(key["block"] + key["blockSize"]) + 2))  # located from the Scene: the legend row moves with its keys (#499)
        # the key is the chart's own hollow planned milestone (#499): an ink outline on the white ground, not a solid fill
        ink = sum(count for count, pixel in legend_glyph.getcolors(maxcolors=100000) if sum(pixel[:3]) < 3 * 128)
        assert 40 < ink < 400


def test_missing_preset_glyph_reports_exact_theme_pointer_and_set_name(tmp_path, monkeypatch, capsys):
    preset = copy_builtin_preset("technical-print", tmp_path / "copied")
    theme_path = preset.parent / "theme.yaml"
    theme = yaml.safe_load(theme_path.read_bytes())
    theme["body"]["values"]["milestone-symbol"]["value"]["shape"] = {"catalog": "missing:pin"}
    theme_path.write_text(yaml.safe_dump(theme, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["chrona", "render", str(PROJECT), "--preset", str(preset),
                                      "--output", str(tmp_path / "unwritten.svg")])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 1
    rejected = json.loads(capsys.readouterr().out)
    diagnostic = rejected["diagnostics"][0]
    assert diagnostic["code"] == "E_THEME_ASSET_REFERENCE"
    assert diagnostic["sourceRef"] == "/body/values/milestone-symbol/value/shape/catalog"
    assert "missing:pin" in diagnostic["message"]
    assert not (tmp_path / "unwritten.svg").exists()
