"""`preset copy` writes the bundled default and plain YAML (#1305)."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from chrona.usecases.preset_library import DEFAULT_PRESET_ID, list_builtin_presets


def _chrona(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-c", "from chrona.app.cli import main; main()", *args], cwd=cwd,
                          capture_output=True, text=True, timeout=300)


@pytest.fixture(scope="module")
def starter(tmp_path_factory):
    root = tmp_path_factory.mktemp("presets")
    assert _chrona(root, "init", "p").returncode == 0
    return root


def _render(root: Path, name: str, *preset: str) -> bytes:
    result = _chrona(root, "render", "p/project.yaml", "--actual", "p/actual.yaml", *preset, "--output", f"{name}.svg")
    assert result.returncode == 0, result.stdout
    return (root / f"{name}.svg").read_bytes()


def test_the_bundled_default_is_listed_as_the_default(starter):
    listed = json.loads(_chrona(starter, "preset", "list").stdout)

    assert listed["default"] == DEFAULT_PRESET_ID
    assert DEFAULT_PRESET_ID in [item["id"] for item in listed["presets"]]


def test_the_copied_default_renders_byte_identically_to_a_render_without_a_preset(starter):
    copied = _chrona(starter, "preset", "copy", DEFAULT_PRESET_ID, "--output", "mine")
    assert copied.returncode == 0, copied.stdout

    assert _render(starter, "copy", "--preset", "mine/preset.yaml") == _render(starter, "plain")


@pytest.mark.parametrize("identifier", [item["id"] for item in list_builtin_presets()])
def test_every_builtin_copy_is_plain_yaml_and_renders_like_the_id(starter, identifier):
    target = f"copy-{identifier}"
    assert _chrona(starter, "preset", "copy", identifier, "--output", target).returncode == 0

    for path in sorted((starter / target).glob("*.yaml")):
        events = list(yaml.parse(path.read_text(encoding="utf-8")))
        assert not [event for event in events if isinstance(event, yaml.AliasEvent)
                    or getattr(event, "anchor", None) is not None], path.name
    assert _render(starter, f"by-copy-{identifier}", "--preset", f"{target}/preset.yaml") == _render(
        starter, f"by-id-{identifier}", "--preset", identifier)
