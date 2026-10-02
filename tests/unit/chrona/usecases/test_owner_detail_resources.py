"""The raise sites of the init, skill, preset and packaged-resource paths name what they found (#829 S2)."""
from copy import deepcopy
from pathlib import Path

import pytest

from chrona import resources
from chrona.usecases import local_authoring, preset_library, skill_library
from chrona.usecases.diagnostic_messages import is_bare


def _say(call) -> str:
    with pytest.raises(ValueError) as caught:
        call()
    text = str(caught.value)
    code = text.split(":", 1)[0]
    assert code.startswith("E_") and not is_bare(code, text), text
    return text


def test_init_into_a_used_directory_names_the_directory(tmp_path: Path):
    (tmp_path / "used").mkdir()
    (tmp_path / "used" / "file").write_text("x")
    assert str(tmp_path / "used") in _say(lambda: local_authoring.initialize_project(tmp_path / "used"))


def test_store_config_failures_name_the_path_and_the_search(tmp_path: Path):
    missing = tmp_path / "missing-store.yaml"
    assert str(missing) in _say(lambda: local_authoring.discover_store_configuration(explicit=missing))
    text = _say(lambda: local_authoring.discover_store_configuration(start=tmp_path / "outside"))
    assert ".chrona/store.yaml" in text and str(tmp_path / "outside") in text


def test_skill_copy_into_a_used_directory_names_the_directory(tmp_path: Path):
    (tmp_path / "used").mkdir()
    (tmp_path / "used" / "file").write_text("x")
    assert str(tmp_path / "used") in _say(lambda: skill_library.copy_skill(tmp_path / "used"))


@pytest.fixture
def empty_package(monkeypatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(resources, "files", lambda name: tmp_path)
    return tmp_path


@pytest.mark.parametrize("call,needle", [
    (lambda: resources.default_preset_resource(), "presets/default.yaml"),
    (lambda: resources.default_preset_root(), "default.yaml"),
    (lambda: resources.builtin_preset_library_resource(), "presets/library.yaml"),
    (lambda: resources.axis_name_tables_resource(), "axis-name-tables-v0.1.yaml"),
    (lambda: resources.minimal_template_resource(), "templates/minimal"),
    (lambda: resources.builtin_preset_source_root("presets/nowhere"), "'presets/nowhere'"),
    (lambda: resources.builtin_preset_source_root("../escape"), "'../escape'"),
])
def test_a_missing_packaged_resource_names_the_resource(empty_package, call, needle):
    assert needle in _say(call)


def test_an_incomplete_starter_template_lists_what_is_missing(empty_package):
    template = empty_package / "templates" / "minimal"
    template.mkdir(parents=True)
    (template / "project.yaml").write_text("x")
    text = _say(resources.minimal_template_resource)
    assert "actual.yaml" in text and "README.md" in text and "project.yaml" not in text.split("missing", 1)[1]


def test_an_unpackaged_skill_is_named(empty_package, monkeypatch):
    def no_skills(name):
        if name == "skills":
            raise ModuleNotFoundError(name)
        return empty_package
    monkeypatch.setattr(resources, "files", no_skills)
    assert "not packaged" in _say(resources.skill_resource)


def test_a_registered_example_whose_files_are_gone_names_its_path(monkeypatch, empty_package):
    monkeypatch.setattr(resources, "example_registry", lambda: {"gone": {"id": "gone", "path": "examples/gone"}})
    (empty_package / "examples").mkdir()
    assert "examples/gone" in _say(lambda: resources.template_resource("gone"))


def _entry() -> dict:
    return deepcopy(next(item for item in preset_library._library() if item["id"] == "technical-print"))


def test_a_catalogue_address_that_escapes_is_named():
    assert "'../x'" in _say(lambda: preset_library._safe("../x"))


def test_a_preset_without_a_member_names_preset_and_member():
    entry = _entry()
    del entry["members"]["theme"]
    text = _say(lambda: preset_library._member(entry, "theme"))
    assert "technical-print" in text and "'theme'" in text


@pytest.mark.parametrize("change,needle", [
    ({"sourcePath": "nope.yaml"}, "nope.yaml"),
    ({"contentIdentity": "sha256:" + "0" * 64}, "content identity"),
    ({"id": "another-id"}, "another-id"),
    ({"kind": "view"}, "'view'"),
])
def test_a_bad_member_names_the_member_and_what_differs(change, needle):
    member = deepcopy(_entry()["members"]["iconCatalogs"][0])
    member.update(change)
    assert needle in _say(lambda: preset_library._read_member(member))


@pytest.mark.parametrize("change,needle", [
    ({"noticeSourcePath": "missing.NOTICE"}, "missing.NOTICE"),
    ({"noticeContentIdentity": "sha256:" + "0" * 64}, "content identity"),
])
def test_a_bad_notice_names_the_notice(monkeypatch, tmp_path, change, needle):
    entry = _entry()
    entry["members"]["iconCatalogs"][0].update(change)
    monkeypatch.setattr(preset_library, "_library", lambda: [entry])
    assert needle in _say(lambda: preset_library.copy_builtin_preset("technical-print", tmp_path / "out"))


def test_a_bad_library_names_the_problem(monkeypatch, tmp_path: Path):
    library = tmp_path / "library.yaml"
    monkeypatch.setattr(preset_library, "builtin_preset_library_resource", lambda: library)
    assert "cannot be read" in _say(preset_library._library)
    library.write_text("- not a mapping\n")
    assert "preset-library-v0.2.schema.yaml" in _say(preset_library._library)
