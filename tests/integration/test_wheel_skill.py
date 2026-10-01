"""The skill resolves from the source tree, and the wheel is configured to carry the same tree (#142, S2)."""
from __future__ import annotations

from importlib.resources import files
from pathlib import Path
import tomllib

import pytest

from chrona import resources
from chrona.resources import skill_resource

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def _tree(root) -> dict[str, bytes]:
    found: dict[str, bytes] = {}

    def visit(node, prefix: str) -> None:
        for child in node.iterdir():
            name = prefix + child.name
            if child.is_dir():
                visit(child, name + "/")
            else:
                found[name] = child.read_bytes()

    visit(root, "")
    return found


def _source_tree() -> dict[str, bytes]:
    return {path.relative_to(ROOT / "skills" / "chrona").as_posix(): path.read_bytes()
            for path in (ROOT / "skills" / "chrona").rglob("*") if path.is_file()}


def test_a_development_install_resolves_the_source_tree():
    assert not files("chrona.resources").joinpath("skills", "chrona").is_dir(), "a source checkout carries no second copy"
    assert _tree(skill_resource()) == _source_tree()


def test_the_wheel_force_includes_exactly_the_skill_directory_once():
    forced = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]

    assert forced["skills/chrona"] == "chrona/resources/skills/chrona"
    assert list(forced.values()).count("chrona/resources/skills/chrona") == 1


def test_a_packaged_tree_wins_over_the_source_tree(tmp_path, monkeypatch):
    packaged = tmp_path / "skills" / "chrona"
    packaged.mkdir(parents=True)
    (packaged / "SKILL.md").write_text("packaged", encoding="utf-8")
    real_files = resources.files
    monkeypatch.setattr(resources, "files", lambda package: tmp_path if package == "chrona.resources" else real_files(package))

    assert skill_resource().joinpath("SKILL.md").read_bytes() == b"packaged"


def test_no_skill_anywhere_is_a_stable_error(tmp_path, monkeypatch):
    monkeypatch.setattr(resources, "files", lambda package: tmp_path)

    with pytest.raises(ValueError, match="E_SKILL_RESOURCE"):
        skill_resource()
