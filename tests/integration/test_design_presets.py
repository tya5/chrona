"""The packaged shared designs are selectable catalogue presets that reference their files in place (#429, P429-4)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

from chrona.app.cli import main
from chrona.resources import builtin_preset_source_root, safe_load
from chrona.usecases.preset_library import list_builtin_presets

ROOT = Path(__file__).resolve().parents[2]
RESOURCES = ROOT / "src/chrona/resources"
DESIGNS = ("marquee", "sunday")
MEMBER_FILES = {"theme": "theme.yaml", "colorScheme": "scheme.yaml", "layout": "layout.yaml", "detailProfile": "detail.yaml"}


def _run(monkeypatch, capsys, *argv):
    monkeypatch.setattr(sys, "argv", ["chrona", *argv])
    capsys.readouterr()
    main()
    return capsys.readouterr().out


def _entry(name):
    entries = yaml.safe_load((RESOURCES / "presets/library.yaml").read_text(encoding="utf-8"))["entries"]
    return next(item for item in entries if item["id"] == name)


@pytest.mark.parametrize("name", DESIGNS)
def test_the_design_is_listed(name):
    assert name in [item["id"] for item in list_builtin_presets()]


@pytest.mark.parametrize("name", DESIGNS)
def test_the_entry_references_the_design_in_place_with_the_shared_default_view(name):
    members = _entry(name)["members"]
    assert members["view"]["sourceRoot"] == "presets/bundles/design-default"
    for member, filename in MEMBER_FILES.items():
        assert (members[member]["sourceRoot"], members[member]["sourcePath"]) == (f"designs/{name}", filename)
        assert builtin_preset_source_root(f"designs/{name}").joinpath(filename).is_file()
    assert not (RESOURCES / "presets/bundles" / name).exists()  # no design is copied into presets/bundles


@pytest.mark.parametrize("address", ["designs", "designs/missing", "designs/a/b", "designs/../icons"])
def test_only_a_packaged_design_directory_is_a_designs_source_root(address):
    with pytest.raises(ValueError):
        builtin_preset_source_root(address)


@pytest.mark.parametrize("name", DESIGNS)
def test_copy_writes_the_design_files_unchanged_in_content_and_nothing_else_extra(tmp_path, monkeypatch, capsys, name):
    destination = tmp_path / name
    result = json.loads(_run(monkeypatch, capsys, "preset", "copy", name, "--output", str(destination)))
    assert result["status"] == "ok"
    for filename in MEMBER_FILES.values():  # the same document, written without YAML anchors and aliases
        source = (RESOURCES / "designs" / name / filename).read_bytes()
        assert safe_load(source) == safe_load((destination / filename).read_bytes())
        assert not any(isinstance(event, yaml.AliasEvent) for event in yaml.parse((destination / filename).read_bytes()))
    assert (destination / "view.yaml").read_bytes() == (RESOURCES / "presets/bundles/design-default/view.yaml").read_bytes()
    written = {path.relative_to(destination).as_posix() for path in destination.rglob("*") if path.is_file()}
    catalogs = {f"catalogs/{item['id']}.{suffix}" for item in _entry(name)["members"].get("iconCatalogs", ())
                for suffix in ("yaml", "NOTICE")}
    # the same shape `preset copy` writes for every other preset: view, theme, scheme, layout, detail, preset.yaml, catalogs
    assert written == {"preset.yaml", "view.yaml", *MEMBER_FILES.values(), *catalogs}


@pytest.mark.parametrize("name", DESIGNS)
@pytest.mark.parametrize("project", ["tests/fixtures/controller-z/project.yaml", None])
def test_render_by_name_succeeds_and_equals_the_copy(tmp_path, monkeypatch, capsys, name, project):
    if project is None:
        _run(monkeypatch, capsys, "init", str(tmp_path / "starter"))
        source = tmp_path / "starter" / "project.yaml"
        extra = ["--actual", str(tmp_path / "starter" / "actual.yaml")]
    else:
        source, extra = ROOT / project, []
    by_name, by_path = tmp_path / "name.svg", tmp_path / "path.svg"
    first = json.loads(_run(monkeypatch, capsys, "render", str(source), *extra, "--preset", name, "--output", str(by_name)))
    assert first["status"] == "ok"
    _run(monkeypatch, capsys, "preset", "copy", name, "--output", str(tmp_path / "copy"))
    _run(monkeypatch, capsys, "render", str(source), *extra, "--preset", str(tmp_path / "copy" / "preset.yaml"),
         "--output", str(by_path))
    assert by_name.read_bytes() == by_path.read_bytes()
