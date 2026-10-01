"""A Store created by `init --example` keeps working where it is moved, and holds no host path (#781).

Inputs come from the real output of `initialize_project`, never from a hand-written path, and nothing decides by the
host's path syntax, so the same assertions hold on Windows (the three-OS run is the evidence there).
"""
import os
import re
import shutil
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest
import yaml

from chrona.app.cli import main
from chrona.operational.store_config import ConfiguredStoreReader, load_store_config
from chrona.usecases.local_authoring import initialize_project

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
GUIDE = ROOT / "docs" / "guides" / "first-project.md"
KEY = ("local", "halcyon-1-example")


def _reference_text() -> str:
    match = re.search(r"cat > \S+ <<'YAML'\n(?P<body>.*?)\nYAML\n", GUIDE.read_text(encoding="utf-8"), re.S)
    assert match is not None
    return match["body"] + "\n"


def _render(monkeypatch, project: Path, output: Path, *, config: Path | None = None) -> bytes:
    reference = project.parent / f"{project.name}-context-reference.yaml"
    reference.write_text(_reference_text(), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["chrona", "render-review", "--context-reference", str(reference), "--store-config",
                                      str(config or project / ".chrona" / "store.yaml"), "--output", str(output)])
    main()
    return output.read_bytes()


def _is_absolute_anywhere(value: str) -> bool:
    return PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute()


def test_the_config_init_writes_holds_a_relative_root_and_no_host_path(tmp_path):
    project = initialize_project(tmp_path / "corpus", example="halcyon-1")
    text = (project / ".chrona" / "store.yaml").read_text(encoding="utf-8")

    [store] = yaml.safe_load(text)["stores"]

    assert store["root"] == "store" and not _is_absolute_anywhere(store["root"])
    assert (project / ".chrona" / store["root"]).is_dir()
    for host in {str(project), project.as_posix(), str(project.resolve()), project.resolve().as_posix(), str(tmp_path), tmp_path.as_posix()}:
        assert host not in text


def test_a_moved_store_still_renders_the_same_bytes_from_any_working_directory(tmp_path, monkeypatch):
    project = initialize_project(tmp_path / "corpus", example="halcyon-1")
    before = _render(monkeypatch, project, tmp_path / "before.svg")
    assert before.startswith(b"<svg")

    moved = tmp_path / "elsewhere" / "deeper" / "renamed"
    moved.parent.mkdir(parents=True)
    shutil.move(str(project), str(moved))
    assert not project.exists()
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)

    assert _render(monkeypatch, moved, tmp_path / "after.svg") == before
    assert load_store_config(str(moved / ".chrona" / "store.yaml")).roots[KEY] == (moved / ".chrona" / "store").resolve()


def test_a_copied_store_works_after_the_original_is_deleted(tmp_path, monkeypatch):
    project = initialize_project(tmp_path / "corpus", example="halcyon-1")
    before = _render(monkeypatch, project, tmp_path / "before.svg")
    copy = tmp_path / "copy"
    shutil.copytree(project, copy)
    shutil.rmtree(project)

    assert _render(monkeypatch, copy, tmp_path / "after.svg") == before


def test_an_absolute_root_still_works(tmp_path, monkeypatch):
    project = initialize_project(tmp_path / "corpus", example="halcyon-1")
    before = _render(monkeypatch, project, tmp_path / "before.svg")
    config = yaml.safe_load((project / ".chrona" / "store.yaml").read_text(encoding="utf-8"))
    config["stores"][0]["root"] = str((project / ".chrona" / "store").resolve())
    assert _is_absolute_anywhere(config["stores"][0]["root"])
    elsewhere = tmp_path / "configs" / "store.yaml"
    elsewhere.parent.mkdir()
    elsewhere.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    assert _render(monkeypatch, project, tmp_path / "after.svg", config=elsewhere) == before
    assert load_store_config(str(elsewhere)).roots[KEY] == (project / ".chrona" / "store").resolve()


def _write_config(path: Path, root: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"version": "chrona/store-config/v0.1",
                                    "stores": [{"provider": "local", "identity": "s", "root": root}]}), encoding="utf-8")
    return path


def test_a_relative_root_is_anchored_at_the_config_directory_not_the_working_directory(tmp_path, monkeypatch):
    config = _write_config(tmp_path / "cfg" / "inner" / "store.yaml", "../data")
    elsewhere = tmp_path / "cwd"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    roots = load_store_config(str(config)).roots

    assert roots[("local", "s")] == (tmp_path / "cfg" / "data").resolve()
    assert os.path.normpath(roots[("local", "s")]) == str(roots[("local", "s")])  # no `..` left in the resolved root


def test_a_reader_built_from_a_mapping_without_a_base_keeps_the_working_directory_meaning():
    reader = ConfiguredStoreReader({"stores": [{"provider": "local", "identity": "s", "root": "relative"}]})

    assert reader.roots[("local", "s")] == Path("relative")


@pytest.mark.parametrize("root", ["store", "./store", "sub/../store"])
def test_equivalent_relative_spellings_resolve_to_one_root(tmp_path, root):
    config = _write_config(tmp_path / ".chrona" / "store.yaml", root)

    assert load_store_config(str(config)).roots[("local", "s")] == (tmp_path / ".chrona" / "store").resolve()
