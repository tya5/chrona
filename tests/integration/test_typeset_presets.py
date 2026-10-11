"""Every bundled appearance reaches the Typst and TikZ adapters, and no mark is dropped silently (#1308).

The `chrona init` starter is rendered with the bundled default and each catalogue preset. A preset that prefers an SVG-only
visual profile is rendered with the baseline profile, as the CLI's own message instructs.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

from chrona.usecases.preset_library import list_builtin_presets

TARGETS = {
    "typst": ("typ", ["--typesetter-engine", "typst", "--typesetter-version", "0.13.1", "--typesetter-adapter-grammar", "chrona-typst/v0.1"]),
    "tikz": ("tex", ["--typesetter-engine", "tectonic", "--typesetter-version", "0.15.0", "--typesetter-adapter-grammar", "chrona-tikz/v0.1"]),
}
SVG_ONLY = {"elevated-light", "technical-print"}  # their preferred profile is the SVG icon profile
PRESETS = [None, *(item["id"] for item in list_builtin_presets())]


def _chrona(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-c", "from chrona.app.cli import main; main()", *args], cwd=cwd,
                          capture_output=True, text=True, timeout=300)


@pytest.fixture(scope="module")
def starter(tmp_path_factory):
    root = tmp_path_factory.mktemp("typeset")
    assert _chrona(root, "init", "p").returncode == 0
    return root


def _render(root: Path, preset: str | None, target: str, name: str):
    suffix, descriptor = TARGETS[target]
    output, scene = f"{name}.{suffix}", f"{name}.scene.json"
    args = ["render", "p/project.yaml", "--actual", "p/actual.yaml", "-o", output, "--emit-scene", scene, *descriptor]
    if preset:
        args += ["--preset", preset]
    if preset in SVG_ONLY:
        args += ["--visual-profile", "chrona-output/visual/v0.5-baseline"]
    return _chrona(root, *args), root / output, root / scene


@pytest.mark.parametrize("target", sorted(TARGETS))
@pytest.mark.parametrize("preset", PRESETS)
def test_every_bundled_appearance_exports_to_the_typeset_targets(starter, preset, target):
    result, output, _scene = _render(starter, preset, target, f"{preset or 'default'}-{target}")
    report = json.loads(result.stdout)
    codes = [item["code"] for item in report["diagnostics"]]

    if preset == "technical-print":  # its axis bands are patterned: refused with the primitive and the role named
        assert codes == ["E_VISUAL_CAPABILITY_UNSUPPORTED"] and result.returncode == 1
        message = report["diagnostics"][0]["message"]
        assert "pattern" in message and "axis-band-rect" in message and "role " in message
        return
    assert "E_VISUAL_CAPABILITY_UNSUPPORTED" not in codes and result.returncode == 0, report
    assert output.read_text(encoding="utf-8")


def _kinds(scene: Path) -> dict[str, int]:
    primitives = json.loads(scene.read_text(encoding="utf-8"))["surfaces"][0]["primitives"]
    counts: dict[str, int] = {}
    for item in primitives:
        counts[item["kind"]] = counts.get(item["kind"], 0) + 1
    counts["total"] = len(primitives)
    return counts


@pytest.mark.parametrize("preset", [None, "executive-light", "mission-light"])
def test_the_typst_output_has_one_element_per_scene_primitive(starter, preset):
    result, output, scene = _render(starter, preset, "typst", f"count-{preset or 'default'}-typst")
    assert result.returncode == 0, result.stdout
    text, kinds = output.read_text(encoding="utf-8"), _kinds(scene)
    markers = len(re.findall(r"^// marker-(?:start|end) of scene-id:", text, re.M))

    assert len(re.findall(r"^// scene-id:", text, re.M)) == kinds["total"]
    assert text.count("#rect(") == kinds.get("Rect", 0) + 1  # + the page background
    assert len(re.findall(r"#text\(", text)) == kinds.get("Text", 0)
    assert text.count("#curve(") == kinds.get("Symbol", 0) + kinds.get("Path", 0) + markers
    assert set(kinds) <= {"Rect", "Text", "Symbol", "Path", "total"}, kinds


@pytest.mark.parametrize("preset", [None, "executive-light", "mission-light"])
def test_the_tikz_output_has_one_element_per_scene_primitive(starter, preset):
    result, output, scene = _render(starter, preset, "tikz", f"count-{preset or 'default'}-tikz")
    assert result.returncode == 0, result.stdout
    text, kinds = output.read_text(encoding="utf-8"), _kinds(scene)
    markers = len(re.findall(r"^% marker-(?:start|end) of scene-id:", text, re.M))

    assert len(re.findall(r"^% scene-id:", text, re.M)) == kinds["total"]
    assert len(re.findall(r"^\\node\[", text, re.M)) == kinds.get("Text", 0)
    assert len(re.findall(r"^\\(?:path|draw)\[", text, re.M)) == 1 + kinds.get("Rect", 0) + kinds.get("Symbol", 0) + kinds.get("Path", 0) + markers


def test_the_help_lists_the_accepted_typesetter_values():
    from chrona.app.cli import _parser
    from tools.check_documented_commands import _options, _subparsers

    render = _subparsers(_parser())["render"]
    engine = _options(render)["--typesetter-engine"].help
    grammar = _options(render)["--typesetter-adapter-grammar"].help
    version = _options(render)["--typesetter-version"].help
    assert "typst" in engine and "tectonic" in engine
    assert "chrona-typst/v0.1" in grammar and "chrona-tikz/v0.1" in grammar
    assert "exact" in version and "never looked up" in version
