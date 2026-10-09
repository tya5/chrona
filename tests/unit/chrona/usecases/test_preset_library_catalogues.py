from copy import deepcopy
from hashlib import sha256
import pytest
import yaml

from chrona import resources
from chrona.usecases import preset_library
from chrona.usecases.failure_report import StableFailure


def test_icons_is_an_explicit_packaged_preset_source_root():
    root = resources.builtin_preset_source_root("icons")
    assert root.joinpath("chrona-theme-starter-v2026-10-09.yaml").is_file()
    assert root.joinpath("chrona-theme-starter.NOTICE").is_file()


def test_technical_print_copies_catalogue_and_notice_with_exact_library_pins(tmp_path):
    entry = next(item for item in preset_library._library() if item["id"] == "technical-print")
    member = entry["members"]["iconCatalogs"][0]
    source = resources.builtin_preset_source_root(member["sourceRoot"])
    catalogue = source.joinpath(member["sourcePath"]).read_bytes()
    notice = source.joinpath(member["noticeSourcePath"]).read_bytes()
    assert "sha256:" + sha256(catalogue).hexdigest() == member["contentIdentity"]
    assert "sha256:" + sha256(notice).hexdigest() == member["noticeContentIdentity"]

    destination = tmp_path / "preset"
    preset_path = preset_library.copy_builtin_preset("technical-print", destination)
    assert (destination / f"catalogs/{member['id']}.yaml").read_bytes() == catalogue
    assert (destination / f"catalogs/{member['id']}.NOTICE").read_bytes() == notice
    copied_preset = yaml.safe_load(preset_path.read_text(encoding="utf-8"))
    assert copied_preset["body"]["resources"]["iconCatalogs"] == [
        {"id": member["id"], "kind": "icon-catalog", "path": f"catalogs/{member['id']}.yaml"}
    ]
    assert copied_preset["body"]["resources"]["detailProfile"]["path"] == "detail.yaml"


def test_bad_notice_pin_fails_before_destination_creation(monkeypatch, tmp_path):
    entry = next(item for item in preset_library._library() if item["id"] == "technical-print")
    entry = deepcopy(entry)
    entry["members"]["iconCatalogs"][0]["noticeContentIdentity"] = "sha256:" + "0" * 64
    monkeypatch.setattr(preset_library, "_library", lambda: [entry])
    destination = tmp_path / "not-created"
    with pytest.raises(ValueError, match="E_BUILTIN_PRESET_NOTICE"):
        preset_library.copy_builtin_preset("technical-print", destination)
    assert not destination.exists()


@pytest.mark.parametrize("field,value,code", [
    ("sourcePath", "missing-catalog.yaml", "E_BUILTIN_PRESET_RESOURCE"),
    ("contentIdentity", "sha256:" + "0" * 64, "E_BUILTIN_PRESET_RESOURCE"),
    ("noticeSourcePath", "missing-notice.NOTICE", "E_BUILTIN_PRESET_NOTICE"),
])
def test_missing_or_mismatched_catalogue_members_fail_before_copy(
        monkeypatch, tmp_path, field, value, code):
    entry = deepcopy(next(item for item in preset_library._library() if item["id"] == "technical-print"))
    entry["members"]["iconCatalogs"][0][field] = value
    monkeypatch.setattr(preset_library, "_library", lambda: [entry])
    destination = tmp_path / "not-created"
    with pytest.raises(ValueError, match=code):
        preset_library.copy_builtin_preset("technical-print", destination)
    assert not destination.exists()


def test_nonempty_destination_is_never_modified(tmp_path):
    destination = tmp_path / "existing"
    destination.mkdir()
    marker = destination / "owned.txt"
    marker.write_bytes(b"keep")
    with pytest.raises(StableFailure) as refused:
        preset_library.copy_builtin_preset("technical-print", destination)
    assert refused.value.code == "E_BUILTIN_PRESET_OUTPUT_EXISTS" and str(destination) in refused.value.message
    assert tuple(destination.iterdir()) == (marker,)
    assert marker.read_bytes() == b"keep"


def test_legacy_preset_copy_without_catalogues_still_works(tmp_path):
    preset_path = preset_library.copy_builtin_preset("elevated-light", tmp_path / "legacy")
    assert preset_path.is_file()
    copied = yaml.safe_load(preset_path.read_text(encoding="utf-8"))
    assert "iconCatalogs" not in copied["body"]["resources"]


def test_an_unknown_preset_names_the_value_and_lists_exactly_the_valid_ids(tmp_path):
    with pytest.raises(StableFailure) as refused:
        preset_library.copy_builtin_preset("editorail", tmp_path / "out")
    failure = refused.value
    assert (failure.code, failure.component, failure.source_ref, failure.exit_code) == (
        "E_BUILTIN_PRESET_UNKNOWN", "presentation", "/", 1)
    assert "'editorail'" in failure.message
    listed = failure.message.split("valid ids: ", 1)[1].split(" (chrona preset list)", 1)[0].split(", ")
    assert listed == [item["id"] for item in preset_library.list_builtin_presets()]
    assert not (tmp_path / "out").exists()
