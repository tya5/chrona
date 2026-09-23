import json

import pytest
import yaml
from pathlib import Path

from chrona.presentation.icons.importer import IconImportError, copy_material_symbols_outline_rounded_catalog, import_iconify


def _collection(body: str) -> dict:
    return {"prefix": "sample", "icons": {"sample": {"body": body, "width": 24, "height": 24}}}


@pytest.mark.parametrize("body,paint", [
    ('<path fill="currentColor" d="M5 21V4h9l.4 2H20v10h-7l-.4-2H7v7z"/>', "fill"),  # Material Symbols flag
    ('<g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v4m0 4h.01"/></g>', "stroke"),  # Lucide circle-alert
    ('<path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12a9 9 0 1 0 18 0a9 9 0 1 0-18 0"/>', "stroke"),  # Tabler circle
])
def test_importer_normalizes_monochrome_iconify_artwork(tmp_path, body, paint):
    source, output, notice = tmp_path / "icons.json", tmp_path / "icons.yaml", tmp_path / "LICENSE"
    source.write_text(json.dumps(_collection(body)))
    notice.write_text("MIT notice\n")
    result = import_iconify(source, output, license_spdx="MIT", notice_path=notice)
    catalog = yaml.safe_load(output.read_text())
    assert result["set"] == "sample"
    assert catalog["body"]["icons"]["sample"]["paths"][0]["paint"] == paint


def test_importer_never_replaces_output_after_a_collection_error(tmp_path):
    source, output, notice = tmp_path / "icons.json", tmp_path / "icons.yaml", tmp_path / "LICENSE"
    output.write_text("preserved\n")
    source.write_text(json.dumps(_collection('<mask/>')))
    notice.write_text("MIT notice\n")
    with pytest.raises(IconImportError) as error:
        import_iconify(source, output, license_spdx="MIT", notice_path=notice)
    assert error.value.code == "E_ICON_IMPORT_ELEMENT"
    assert error.value.icon == "sample:sample"
    assert error.value.source_ref == "/mask"
    assert output.read_text() == "preserved\n"


def test_importer_applies_iconify_quarter_turn_metadata(tmp_path):
    source, output, notice = tmp_path / "icons.json", tmp_path / "icons.yaml", tmp_path / "LICENSE"
    value = _collection('<path d="M1 2L3 4"/>'); value["icons"]["sample"].update({"width": 20, "height": 10, "rotate": 1})
    source.write_text(json.dumps(value)); notice.write_text("MIT notice\n")
    import_iconify(source, output, license_spdx="MIT", notice_path=notice)
    icon = yaml.safe_load(output.read_text())["body"]["icons"]["sample"]
    assert icon["viewport"] == {"inlineSize": 10, "blockSize": 20}
    assert icon["paths"][0]["data"].split()[:3] == ["M", "8", "1"]


def test_importer_normalizes_transform_bearing_alias_to_its_own_entry(tmp_path):
    source, output, notice = tmp_path / "icons.json", tmp_path / "icons.yaml", tmp_path / "LICENSE"
    value = _collection('<path d="M1 2L3 4"/>'); value["aliases"] = {"turned": {"parent": "sample", "rotate": 1}}
    source.write_text(json.dumps(value)); notice.write_text("MIT notice\n")
    import_iconify(source, output, license_spdx="MIT", notice_path=notice)
    body = yaml.safe_load(output.read_text())["body"]
    assert "turned" in body["icons"] and "turned" not in body["entryAliases"]


def test_importer_selects_only_the_explicit_local_manifest(tmp_path):
    source, output, notice, include = (tmp_path / "icons.json", tmp_path / "icons.yaml",
                                       tmp_path / "LICENSE", tmp_path / "include.txt")
    value = _collection('<path d="M1 2L3 4"/>')
    value["icons"]["other"] = {"body": '<path d="M2 3L4 5"/>', "width": 24, "height": 24}
    source.write_text(json.dumps(value)); notice.write_text("MIT notice\n"); include.write_text("sample\n")

    result = import_iconify(source, output, license_spdx="MIT", notice_path=notice, include_path=include)

    assert result["icons"] == 1
    assert set(yaml.safe_load(output.read_text())["body"]["icons"]) == {"sample"}


def test_importer_retains_aliases_of_selected_canonical_entries_and_resolves_chains(tmp_path):
    source, output, notice, include = (tmp_path / "icons.json", tmp_path / "icons.yaml",
                                       tmp_path / "LICENSE", tmp_path / "include.txt")
    value = _collection('<path d="M1 2L3 4"/>')
    value["icons"]["other"] = {"body": '<path d="M2 3L4 5"/>', "width": 24, "height": 24}
    value["aliases"] = {
        "warning": {"parent": "sample"}, "warning-copy": {"parent": "warning"},
        "turned": {"parent": "warning-copy", "rotate": 1}, "other-copy": {"parent": "other"},
    }
    source.write_text(json.dumps(value)); notice.write_text("MIT notice\n"); include.write_text("sample\n")

    import_iconify(source, output, license_spdx="MIT", notice_path=notice, include_path=include)

    body = yaml.safe_load(output.read_text())["body"]
    assert body["entryAliases"] == {"warning": "sample", "warning-copy": "sample"}
    assert "turned" in body["icons"] and "other-copy" not in body["entryAliases"]


def test_importer_diagnostic_includes_prefix_icon_and_attribute(tmp_path):
    source, output, notice = tmp_path / "icons.json", tmp_path / "icons.yaml", tmp_path / "LICENSE"
    source.write_text(json.dumps(_collection('<path style="fill:red" d="M1 2L3 4"/>')))
    notice.write_text("MIT notice\n")

    with pytest.raises(IconImportError) as error:
        import_iconify(source, output, license_spdx="MIT", notice_path=notice)

    assert error.value.detail == "E_ICON_IMPORT_UNSAFE icon=sample:sample source=/path/@style"


def test_bundled_default_copies_an_explicit_catalog(tmp_path):
    output = tmp_path / "material.yaml"
    result = copy_material_symbols_outline_rounded_catalog(output)

    assert result["set"] == "material"
    assert result["aliases"] == ["material-symbols"]
    assert output.read_bytes()


def test_importer_records_an_explicit_source_version(tmp_path):
    source, output, notice = tmp_path / "icons.json", tmp_path / "icons.yaml", tmp_path / "LICENSE"
    source.write_text(json.dumps(_collection('<path d="M1 2L3 4"/>'))); notice.write_text("MIT notice\n")

    import_iconify(source, output, license_spdx="MIT", notice_path=notice, source_version="9.9.9")

    assert yaml.safe_load(output.read_text())["body"]["provenance"]["sourceVersion"] == "9.9.9"


def test_public_lucide_tabler_fixture_is_reproducible_from_the_cli_inputs(tmp_path):
    root = Path(__file__).resolve().parents[5]
    source = root / "examples/controller-z/assets/lucide-tabler-icons.json"
    notice = root / "examples/controller-z/assets/lucide-tabler.NOTICE"
    output = tmp_path / "imported-icons.yaml"
    import_iconify(source, output, set_name="public-icons", license_spdx="MIT", notice_path=notice)
    assert output.read_bytes() == (root / "examples/controller-z/imported-icons.yaml").read_bytes()
