"""#574: the bundled default and every library preset resolve without the examples corpus."""
from __future__ import annotations

from importlib.resources import files as real_files
from pathlib import Path
import sys

import pytest
import yaml

from chrona.app.cli import main
import chrona.resources as resources


ROOT = Path(__file__).resolve().parents[2]
LIBRARY = yaml.safe_load((ROOT / "src/chrona/resources/presets/library.yaml").read_bytes())["entries"]


class _NoExamples:
    """Delegates to a real package root but refuses any path that starts with `examples`."""

    def __init__(self, root):
        self._root = root

    def joinpath(self, *parts):
        if parts and str(parts[0]).split("/")[0] == "examples":
            raise AssertionError(f"examples corpus reached through {parts!r}")
        return self._root.joinpath(*parts)

    def __truediv__(self, part):
        return self.joinpath(part)

    def __getattr__(self, name):
        return getattr(self._root, name)


@pytest.fixture
def examples_absent(monkeypatch):
    def guarded(package, *args, **kwargs):
        if str(package).split(".")[0] == "examples":
            raise AssertionError("the top-level examples package was requested")
        return _NoExamples(real_files(package, *args, **kwargs))

    monkeypatch.setattr(resources, "files", guarded)


def _run(monkeypatch, *argv: str) -> None:
    monkeypatch.setattr(sys, "argv", ["chrona", *argv])
    main()


@pytest.fixture
def synthetic_project(tmp_path, monkeypatch):
    """A starter written from the wheel-owned minimal template, not a corpus example."""
    root = tmp_path / "starter"
    _run(monkeypatch, "init", str(root))
    return root / "project.yaml", root / "actual.yaml"


def test_the_guard_refuses_examples_paths(examples_absent):
    with pytest.raises(AssertionError):
        resources.files("chrona.resources").joinpath("examples", "halcyon-1")
    with pytest.raises(AssertionError):
        resources.files("examples")


def test_bundled_default_renders_without_examples(tmp_path, monkeypatch, synthetic_project, examples_absent):
    project, actual = synthetic_project
    _run(monkeypatch, "render", str(project), "--actual", str(actual), "--output", str(tmp_path / "default.svg"))
    assert (tmp_path / "default.svg").read_text(encoding="utf-8").startswith("<svg")


@pytest.mark.parametrize("preset_id", [entry["id"] for entry in LIBRARY])
def test_every_library_preset_copies_and_renders_without_examples(preset_id, tmp_path, monkeypatch, synthetic_project, examples_absent):
    project, actual = synthetic_project
    preset = tmp_path / "preset"
    _run(monkeypatch, "preset", "copy", preset_id, "--output", str(preset))
    _run(monkeypatch, "render", str(project), "--actual", str(actual), "--preset", str(preset / "preset.yaml"),
         "--output", str(tmp_path / "out.svg"))
    assert (tmp_path / "out.svg").read_text(encoding="utf-8").startswith("<svg")
