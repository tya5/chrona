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


def test_titlecard_copy_includes_the_optional_summary_profile_unchanged(tmp_path):
    entry = next(item for item in preset_library._library() if item["id"] == "titlecard")
    member = entry["members"]["summaryProfile"]
    source = resources.builtin_preset_source_root(member["sourceRoot"]).joinpath(member["sourcePath"]).read_bytes()

    destination = tmp_path / "titlecard"
    preset_path = preset_library.copy_builtin_preset("titlecard", destination)

    assert (destination / "summary.yaml").read_bytes() == source
    copied = yaml.safe_load(preset_path.read_text(encoding="utf-8"))
    assert copied["body"]["resources"]["summaryProfile"] == {
        "id": member["id"], "kind": member["kind"], "path": "summary.yaml",
    }


def test_bad_summary_member_fails_before_destination_creation(monkeypatch, tmp_path):
    entry = deepcopy(next(item for item in preset_library._library() if item["id"] == "titlecard"))
    entry["members"]["summaryProfile"]["contentIdentity"] = "sha256:" + "0" * 64
    monkeypatch.setattr(preset_library, "_library", lambda: [entry])
    destination = tmp_path / "not-created"

    with pytest.raises(ValueError, match="E_BUILTIN_PRESET_RESOURCE"):
        preset_library.copy_builtin_preset("titlecard", destination)

    assert not destination.exists()


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


def test_preset_copy_id_renames_the_preset_and_every_resource_consistently(tmp_path):
    """#1827 row 6: --id NEW writes one name everywhere, and the copy loads without hand edits."""
    import yaml
    from chrona.usecases.preset_library import copy_builtin_preset, list_builtin_presets

    for entry in list_builtin_presets():
        target = copy_builtin_preset(entry["id"], tmp_path / entry["id"], "my-look")
        preset = yaml.safe_load(target.read_text(encoding="utf-8"))
        assert preset["id"] == "my-look"
        resources = preset["body"]["resources"]
        declared = {name: value for name, value in resources.items() if isinstance(value, dict)}
        assert {"view", "theme", "colorScheme", "layout"} <= set(declared)
        for name, value in declared.items():
            document = yaml.safe_load((target.parent / value["path"]).read_text(encoding="utf-8"))
            assert value["id"] == document["id"] == "my-look", (entry["id"], name)
        assert preset["body"]["compatibleColorSchemes"][0]["id"] == "my-look"
        for catalog in resources.get("iconCatalogs", []):
            assert catalog["id"] != "my-look"


def test_preset_copy_id_copy_renders_without_resource_mismatch(tmp_path):
    from chrona.usecases.preset_library import copy_builtin_preset
    from chrona.app.cli import main
    import sys

    for index, new_id in enumerate(("renamed-look", "true", "null", "yes", "a" * 256)):
        target = copy_builtin_preset("target-b", tmp_path / f"look-{index}", new_id)
        output = tmp_path / f"out-{index}.svg"
        argv = ["chrona", "render", "examples/onboarding/01-spans/project.yaml", "--preset", str(target), "--output", str(output)]
        old = sys.argv
        sys.argv = argv
        try:
            try:
                main()
            except SystemExit as exited:
                assert exited.code in (0, None)
        finally:
            sys.argv = old
        assert output.is_file()


def test_preset_copy_id_refuses_an_unusable_name_before_writing(tmp_path):
    import pytest
    from chrona.usecases.failure_report import StableFailure
    from chrona.usecases.preset_library import copy_builtin_preset

    for index, bad in enumerate(("", "1lead", "has space", "-lead", "a/b", "a" * 257)):
        absent = tmp_path / f"absent-{index}"
        with pytest.raises(StableFailure) as caught:
            copy_builtin_preset("target-b", absent, bad)
        assert caught.value.code == "E_BUILTIN_PRESET_NEW_ID"
        assert not absent.exists()

        empty = tmp_path / f"empty-{index}"
        empty.mkdir()
        with pytest.raises(StableFailure) as caught:
            copy_builtin_preset("target-b", empty, bad)
        assert caught.value.code == "E_BUILTIN_PRESET_NEW_ID"
        assert empty.is_dir() and list(empty.iterdir()) == []


def test_preset_copy_id_uses_layout_id_schema_boundary(tmp_path):
    import yaml

    new_id = "a" * 256
    target = preset_library.copy_builtin_preset("target-b", tmp_path / "look", new_id)
    preset = yaml.safe_load(target.read_text(encoding="utf-8"))
    assert preset["id"] == new_id
    for resource in preset["body"]["resources"].values():
        if isinstance(resource, dict):
            document = yaml.safe_load((target.parent / resource["path"]).read_text(encoding="utf-8"))
            assert document["id"] == new_id


@pytest.mark.parametrize("new_id", ["true", "false", "null", "yes", "no", "on", "off", "y", "n"])
def test_preset_copy_id_keeps_yaml_reserved_names_as_strings_for_every_preset(tmp_path, new_id):
    import yaml

    for entry in preset_library.list_builtin_presets():
        target = preset_library.copy_builtin_preset(entry["id"], tmp_path / f"{entry['id']}-{new_id}", new_id)
        preset = yaml.safe_load(target.read_text(encoding="utf-8"))
        assert preset["id"] == new_id
        for resource in preset["body"]["resources"].values():
            if isinstance(resource, dict):
                document = yaml.safe_load((target.parent / resource["path"]).read_text(encoding="utf-8"))
                assert resource["id"] == document["id"] == new_id, (entry["id"], resource["path"])
