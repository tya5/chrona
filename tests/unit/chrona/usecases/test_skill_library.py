"""`copy_skill` copies the packaged skill byte for byte and never overwrites (#142, S2)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from chrona.usecases import skill_library
from chrona.usecases.skill_library import copy_skill
from tests.support.skill_files import SKILL_DIR, run_cli


def _tree(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


class _Node:
    """A minimal `Traversable`: a directory of nodes or a file of bytes."""

    def __init__(self, name: str, content: bytes | list["_Node"]) -> None:
        self.name, self._content = name, content

    def is_dir(self) -> bool:
        return isinstance(self._content, list)

    def is_file(self) -> bool:
        return not self.is_dir()

    def iterdir(self):
        return iter(self._content)

    def read_bytes(self) -> bytes:
        return self._content  # type: ignore[return-value]


def test_copy_equals_the_source_tree_byte_for_byte(tmp_path):
    destination = tmp_path / "skill"

    assert copy_skill(destination) == destination

    assert _tree(destination) == _tree(SKILL_DIR)
    assert "SKILL.md" in _tree(destination)


def test_an_empty_existing_directory_is_accepted(tmp_path):
    (tmp_path / "skill").mkdir()

    copy_skill(tmp_path / "skill")

    assert _tree(tmp_path / "skill") == _tree(SKILL_DIR)


def test_a_non_empty_directory_or_a_file_is_refused_and_left_untouched(tmp_path):
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "mine.txt").write_text("keep", encoding="utf-8")
    a_file = tmp_path / "file"
    a_file.write_text("keep", encoding="utf-8")

    for target in (occupied, a_file):
        with pytest.raises(ValueError, match="E_SKILL_OUTPUT_EXISTS"):
            copy_skill(target)

    assert _tree(occupied) == {"mine.txt": b"keep"}
    assert a_file.read_text(encoding="utf-8") == "keep"


@pytest.mark.parametrize("name", ["..", "a\\b", "C:x", "sp ace.md", "..."])
def test_an_unsafe_member_name_is_refused_before_anything_is_written(tmp_path, monkeypatch, name):
    tree = _Node("chrona", [_Node("SKILL.md", b"x"), _Node(name, b"evil")])
    monkeypatch.setattr(skill_library, "skill_resource", lambda: tree)

    with pytest.raises(ValueError, match="E_SKILL_RESOURCE"):
        copy_skill(tmp_path / "skill")

    assert not (tmp_path / "skill").exists()


def test_a_tree_without_skill_md_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(skill_library, "skill_resource", lambda: _Node("chrona", [_Node("other.md", b"x")]))

    with pytest.raises(ValueError, match="E_SKILL_RESOURCE"):
        copy_skill(tmp_path / "skill")

    assert not (tmp_path / "skill").exists()


def test_the_command_copies_reports_what_it_wrote_and_refuses_a_second_copy(tmp_path, monkeypatch, capsys):
    argv = ("skill", "copy", "--output", str(tmp_path / "out" / "chrona"))

    status, out, err = run_cli(monkeypatch, capsys, *argv)
    report = json.loads(out)
    assert (status, err, report["status"]) == (0, "", "ok") and "SKILL.md" in report["created"]
    status, out, _err = run_cli(monkeypatch, capsys, *argv)

    assert status == 1
    assert json.loads(out)["diagnostics"][0]["code"] == "E_SKILL_OUTPUT_EXISTS"
    assert _tree(tmp_path / "out" / "chrona") == _tree(SKILL_DIR)
