import json
from hashlib import sha256

import pytest
import yaml
from pathlib import Path

from chrona.presentation.icons.importer import IconImportError, copy_material_symbols_outline_rounded_catalog, import_iconify, import_theme_assets
from chrona.presentation.contracts.resources import ClosureIdentity, parse_contract


def _collection(body: str) -> dict:
    return {"prefix": "sample", "icons": {"sample": {"body": body, "width": 24, "height": 24}}}


def _iconify_error(tmp_path, collection, *, license_spdx="MIT", include_names=None, raw_json=None):
    source, output, notice, include = (tmp_path / "case.json", tmp_path / "case.yaml",
                                       tmp_path / "NOTICE", tmp_path / "include.txt")
    source.write_text(raw_json if raw_json is not None else json.dumps(collection), encoding="utf-8")
    notice.write_text("MIT notice\n", encoding="utf-8")
    kwargs = {"license_spdx": license_spdx, "notice_path": notice}
    if include_names is not None:
        include.write_text(include_names, encoding="utf-8")
        kwargs["include_path"] = include
    with pytest.raises(IconImportError) as error:
        import_iconify(source, output, **kwargs)
    return error.value


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
    catalog = yaml.safe_load(output.read_text(encoding="utf-8"))
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
    assert "got 'mask'" in error.value.detail
    assert output.read_text(encoding="utf-8") == "preserved\n"


def test_importer_applies_iconify_quarter_turn_metadata(tmp_path):
    source, output, notice = tmp_path / "icons.json", tmp_path / "icons.yaml", tmp_path / "LICENSE"
    value = _collection('<path d="M1 2L3 4"/>'); value["icons"]["sample"].update({"width": 20, "height": 10, "rotate": 1})
    source.write_text(json.dumps(value)); notice.write_text("MIT notice\n")
    import_iconify(source, output, license_spdx="MIT", notice_path=notice)
    icon = yaml.safe_load(output.read_text(encoding="utf-8"))["body"]["icons"]["sample"]
    assert icon["viewport"] == {"inlineSize": 10, "blockSize": 20}
    assert icon["paths"][0]["data"].split()[:3] == ["M", "8", "1"]


def test_importer_normalizes_transform_bearing_alias_to_its_own_entry(tmp_path):
    source, output, notice = tmp_path / "icons.json", tmp_path / "icons.yaml", tmp_path / "LICENSE"
    value = _collection('<path d="M1 2L3 4"/>'); value["aliases"] = {"turned": {"parent": "sample", "rotate": 1}}
    source.write_text(json.dumps(value)); notice.write_text("MIT notice\n")
    import_iconify(source, output, license_spdx="MIT", notice_path=notice)
    body = yaml.safe_load(output.read_text(encoding="utf-8"))["body"]
    assert "turned" in body["icons"] and "turned" not in body["entryAliases"]


def test_importer_selects_only_the_explicit_local_manifest(tmp_path):
    source, output, notice, include = (tmp_path / "icons.json", tmp_path / "icons.yaml",
                                       tmp_path / "LICENSE", tmp_path / "include.txt")
    value = _collection('<path d="M1 2L3 4"/>')
    value["icons"]["other"] = {"body": '<path d="M2 3L4 5"/>', "width": 24, "height": 24}
    source.write_text(json.dumps(value)); notice.write_text("MIT notice\n"); include.write_text("sample\n")

    result = import_iconify(source, output, license_spdx="MIT", notice_path=notice, include_path=include)

    assert result["icons"] == 1
    assert set(yaml.safe_load(output.read_text(encoding="utf-8"))["body"]["icons"]) == {"sample"}


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

    body = yaml.safe_load(output.read_text(encoding="utf-8"))["body"]
    assert body["entryAliases"] == {"warning": "sample", "warning-copy": "sample"}
    assert "turned" in body["icons"] and "other-copy" not in body["entryAliases"]


def test_importer_diagnostic_includes_prefix_icon_and_attribute(tmp_path):
    source, output, notice = tmp_path / "icons.json", tmp_path / "icons.yaml", tmp_path / "LICENSE"
    source.write_text(json.dumps(_collection('<path style="fill:red" d="M1 2L3 4"/>')))
    notice.write_text("MIT notice\n")

    with pytest.raises(IconImportError) as error:
        import_iconify(source, output, license_spdx="MIT", notice_path=notice)

    assert error.value.detail == "E_ICON_IMPORT_UNSAFE icon=sample:sample source=/path/@style detail=attribute 'style' is forbidden"


@pytest.mark.parametrize("collection,license_spdx,include_names,code,operand", [
    (_collection('<path fill="chartreuse" d="M1 2L3 4"/>'), "MIT", None, "E_ICON_IMPORT_PAINT", "'chartreuse'"),
    (_collection("<path d='M1 2L3 4'"), "MIT", None, "E_ICON_IMPORT_XML", "malformed SVG fragment at"),
    (_collection("<metadata/>"), "MIT", None, "E_ICON_IMPORT_ELEMENT", "got 'metadata'"),
    (_collection('<path d="M1 2L3 4"/>'), "MIT", "missing-figure\n", "E_ICON_IMPORT_INCLUDE", "missing-figure"),
    (_collection('<path d="M1 2L3 4"/>'), None, None, "E_ICON_IMPORT_LICENSE", "spdx=None"),
])
def test_iconify_diagnostics_name_distinct_operands(tmp_path, collection, license_spdx, include_names, code, operand):
    error = _iconify_error(tmp_path, collection, license_spdx=license_spdx, include_names=include_names)
    assert error.code == code
    assert operand in error.detail


def test_iconify_json_diagnostic_reports_source_and_parse_location(tmp_path):
    error = _iconify_error(tmp_path, {}, raw_json='{"prefix": "sample",')
    assert error.code == "E_ICON_IMPORT_JSON"
    assert error.source_ref.endswith("case.json")
    assert "line=1, column=21" in error.detail


def test_iconify_io_diagnostic_names_missing_collection_path(tmp_path):
    source = tmp_path / "absent-icons.json"
    with pytest.raises(IconImportError) as error:
        import_iconify(source, tmp_path / "out.yaml", license_spdx="MIT", notice_path=tmp_path / "NOTICE")
    assert error.value.code == "E_ICON_IMPORT_IO"
    assert error.value.source_ref == str(source)
    assert "FileNotFoundError" in error.value.detail


def test_iconify_collection_diagnostic_reports_actual_prefix_and_icons_type(tmp_path):
    collection = {"prefix": 17, "icons": []}
    error = _iconify_error(tmp_path, collection)
    assert error.code == "E_ICON_IMPORT_COLLECTION"
    assert "prefix=17" in error.detail and "icons=list" in error.detail


def test_iconify_entry_diagnostic_reports_entry_name_and_body_type(tmp_path):
    collection = {"prefix": "sample", "icons": {"focus-target": {"body": 17}}}
    error = _iconify_error(tmp_path, collection)
    assert error.code == "E_ICON_IMPORT_ENTRY"
    assert error.icon == "focus-target"
    assert "/icons/focus-target" in error.detail and "body=int" in error.detail


def test_iconify_viewport_diagnostic_reports_current_dimensions(tmp_path):
    collection = _collection('<path d="M1 2L3 4"/>')
    collection["icons"]["sample"]["width"] = 0
    error = _iconify_error(tmp_path, collection)
    assert error.code == "E_ICON_IMPORT_VIEWPORT"
    assert "width=0" in error.detail and "1..4096" in error.detail


def test_iconify_transform_diagnostic_reports_invalid_rotation_count(tmp_path):
    collection = _collection('<path d="M1 2L3 4"/>')
    collection["icons"]["sample"]["rotate"] = 7
    error = _iconify_error(tmp_path, collection)
    assert error.code == "E_ICON_IMPORT_TRANSFORM"
    assert "rotate=7" in error.detail and "0..3" in error.detail


def test_iconify_alias_diagnostic_reports_cycle_identity(tmp_path):
    collection = _collection('<path d="M1 2L3 4"/>')
    collection["aliases"] = {"focus-a": {"parent": "focus-b"}, "focus-b": {"parent": "focus-a"}}
    error = _iconify_error(tmp_path, collection)
    assert error.code == "E_ICON_IMPORT_ALIAS"
    assert "icon=sample:focus-a" in error.detail
    assert "/aliases/focus-a/parent" in error.detail and "cycle" in error.detail


def test_importer_shape_error_names_bad_attribute_and_expected_numeric_value(tmp_path):
    source, output, notice = tmp_path / "icons.json", tmp_path / "icons.yaml", tmp_path / "LICENSE"
    source.write_text(json.dumps(_collection('<rect width="wide" height="8"/>')))
    notice.write_text("MIT notice\n")

    with pytest.raises(IconImportError) as error:
        import_iconify(source, output, license_spdx="MIT", notice_path=notice)

    assert error.value.code == "E_ICON_IMPORT_PATH"
    assert error.value.icon == "sample:sample"
    assert error.value.source_ref == "/rect/@width"
    assert "got 'wide'" in error.value.detail
    assert "expected numeric" in error.value.detail


def test_importer_alias_error_names_missing_parent_operand(tmp_path):
    source, output, notice = tmp_path / "icons.json", tmp_path / "icons.yaml", tmp_path / "LICENSE"
    value = _collection('<path d="M1 2L3 4"/>')
    value["aliases"] = {"urgent-copy": {"parent": "missing-urgent"}}
    source.write_text(json.dumps(value)); notice.write_text("MIT notice\n")

    with pytest.raises(IconImportError) as error:
        import_iconify(source, output, license_spdx="MIT", notice_path=notice)

    assert error.value.code == "E_ICON_IMPORT_ALIAS"
    assert error.value.source_ref == "/aliases/urgent-copy/parent"
    assert "'missing-urgent'" in error.value.detail


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

    assert yaml.safe_load(output.read_text(encoding="utf-8"))["body"]["provenance"]["sourceVersion"] == "9.9.9"


def test_public_lucide_tabler_fixture_is_reproducible_from_the_cli_inputs(tmp_path):
    root = Path(__file__).resolve().parents[5]
    source = root / "examples/controller-z/assets/lucide-tabler-icons.json"
    notice = root / "examples/controller-z/assets/lucide-tabler.NOTICE"
    output = tmp_path / "imported-icons.yaml"
    import_iconify(source, output, set_name="public-icons", license_spdx="MIT", notice_path=notice)
    assert output.read_bytes() == (root / "examples/controller-z/imported-icons.yaml").read_bytes()


def test_bundled_material_catalog_matches_the_offline_iconify_utils_conformance_fixture():
    root = Path(__file__).resolve().parents[5]
    fixture = json.loads((root / "tests/fixtures/icons/material-symbols-iconify-utils-v3.1.7.json").read_text(encoding="utf-8"))
    catalog = yaml.load((root / "src/chrona/resources/icons/material-symbols-outline-rounded-v2026-09-22.yaml").read_bytes(), Loader=yaml.CSafeLoader)
    body = catalog["body"]
    assert fixture["format"] == "chrona/iconify-utils-conformance/v0.1"
    assert fixture["utilsPackage"] == "@iconify/utils@3.1.7"
    assert fixture["sourcePackage"] == "@iconify-json/material-symbols@1.2.93"
    assert fixture["sourceContentIdentity"] == body["provenance"]["sourceContentIdentity"]
    assert set(fixture["entries"]) == set(body["icons"]) | set(body["entryAliases"])
    for name, expected in fixture["entries"].items():
        canonical = body["entryAliases"].get(name, name)
        entry = body["icons"][canonical]
        expected_width, expected_height = expected["width"], expected["height"]
        if expected["rotate"] % 2:
            expected_width, expected_height = expected_height, expected_width
        assert canonical == expected["canonical"]
        assert entry["viewport"] == {"inlineSize": expected_width, "blockSize": expected_height}
        assert sha256(json.dumps(entry, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == expected["catalogGeometrySha256"]


def test_theme_assets_import_emits_canonical_v05_catalogue_with_license_and_exact_densities(tmp_path):
    root = Path(__file__).resolve().parents[5]
    source = root / "tests/fixtures/icons/theme-assets-valid.yaml"
    first, second = tmp_path / "one.yaml", tmp_path / "two.yaml"

    result = import_theme_assets(source, first)
    repeated = import_theme_assets(source, second)
    catalog = yaml.safe_load(first.read_bytes())
    body = catalog["body"]

    assert catalog["version"] == "chrona/icon-catalog/v0.5"
    assert body["provenance"]["sourceKind"] == "theme-asset-source"
    assert body["provenance"]["sourceContentIdentity"] == "sha256:" + sha256(source.read_bytes()).hexdigest()
    assert body["provenance"]["license"] == {
        "spdx": "MIT",
        "notice": "Test fixture notice for normalization and import behavior.",
    }
    assert {name: entry["densityBasisPoints"] for name, entry in body["patterns"].items()
            if name.startswith("dither-")} == {"dither-12-5": 1250, "dither-25": 2500, "dither-50": 5000}
    assert body["glyphs"]["pin"]["parts"][0]["data"].startswith("M 12 1 Q 5 1 5 8")
    parsed = parse_contract(ClosureIdentity("icon-catalog", catalog["id"], "r1", result["contentIdentity"]), catalog)
    assert parsed.version == "chrona/icon-catalog/v0.5"
    assert first.read_bytes() == second.read_bytes()
    assert first.read_bytes() == (root / "tests/fixtures/icons/theme-assets-valid.normalized-v0.5.yaml").read_bytes()
    assert result["contentIdentity"] == repeated["contentIdentity"]


def test_theme_assets_import_refuses_retired_source_without_replacing_output(tmp_path):
    root = Path(__file__).resolve().parents[5]
    value = yaml.safe_load((root / "tests/fixtures/icons/theme-assets-valid.yaml").read_bytes())
    value["version"] = "chrona/theme-asset-source/v0.1"
    source = tmp_path / "retired.yaml"
    source.write_text(yaml.safe_dump(value), encoding="utf-8")
    output = tmp_path / "existing.yaml"
    output.write_bytes(b"keep")
    with pytest.raises(IconImportError) as error:
        import_theme_assets(source, output)
    assert error.value.code == "E_THEME_ASSET_SOURCE_SCHEMA"
    assert error.value.source_ref == "/version"
    assert "v0.1" in error.value.detail and "v0.2" in error.value.detail
    assert output.read_bytes() == b"keep"


def test_theme_assets_import_rejects_mismatched_density_without_replacing_output(tmp_path):
    root = Path(__file__).resolve().parents[5]
    source = root / "tests/fixtures/icons/theme-assets-invalid-density.yaml"
    output = tmp_path / "existing.yaml"
    output.write_text("keep this output\n", encoding="utf-8")

    with pytest.raises(IconImportError) as error:
        import_theme_assets(source, output)

    assert error.value.code == "E_THEME_ASSET_SOURCE_DENSITY"
    assert error.value.source_ref == "/body/patterns/dither-12-5"
    assert "densityBasisPoints=1300" in error.value.detail and "derived density=1250" in error.value.detail
    assert output.read_text(encoding="utf-8") == "keep this output\n"


@pytest.mark.parametrize("change,source_ref,code,operand", [
    (lambda source: source["body"].update(aliases=["fixture"]), "/body/aliases", "E_THEME_ASSET_SOURCE_ALIAS", "fixture"),
    (lambda source: source["body"]["patterns"].update(pin=source["body"]["patterns"]["dither-12-5"]), "/body/patterns/pin", "E_THEME_ASSET_SOURCE_NAME", "'pin'"),
    (lambda source: source["body"]["license"].update(notice="   "), "/body/license", "E_THEME_ASSET_SOURCE_LICENSE", "notice_nonblank=False"),
])
def test_theme_assets_import_rejects_namespace_and_provenance_errors(tmp_path, change, source_ref, code, operand):
    root = Path(__file__).resolve().parents[5]
    source_value = yaml.safe_load((root / "tests/fixtures/icons/theme-assets-valid.yaml").read_text(encoding="utf-8"))
    change(source_value)
    source = tmp_path / "invalid.yaml"
    source.write_text(yaml.safe_dump(source_value, sort_keys=False), encoding="utf-8")
    with pytest.raises(IconImportError) as error:
        import_theme_assets(source, tmp_path / "catalog.yaml")
    assert error.value.code == code
    assert error.value.source_ref == source_ref
    assert operand in error.value.detail


@pytest.mark.parametrize("change,source_ref,operand", [
    (lambda source: source["body"].update(aliases=["bad alias"]), "/body/aliases/0", "'bad alias'"),
    (lambda source: source["body"]["license"].update(notice="   "), "/body/license", "notice_nonblank=False"),
    (lambda source: source["body"]["patterns"].update(pin=source["body"]["patterns"]["dither-12-5"]),
     "/body/patterns/pin", "'pin'"),
])
def test_theme_source_diagnostics_name_alias_license_and_collision_operands(tmp_path, change, source_ref, operand):
    root = Path(__file__).resolve().parents[5]
    value = yaml.safe_load((root / "tests/fixtures/icons/theme-assets-valid.yaml").read_text(encoding="utf-8"))
    change(value)
    source = tmp_path / "invalid-source.yaml"
    source.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    with pytest.raises(IconImportError) as error:
        import_theme_assets(source, tmp_path / "catalog.yaml")
    assert error.value.source_ref == source_ref
    assert operand in error.value.detail


@pytest.mark.parametrize("source_bytes,code,operand", [
    (b"kind: [unterminated\n", "E_THEME_ASSET_SOURCE_YAML", "invalid.yaml"),
    (b"[]\n", "E_THEME_ASSET_SOURCE_SCHEMA", "root object fields"),
])
def test_theme_source_parse_diagnostics_name_source_or_expected_root(tmp_path, source_bytes, code, operand):
    source = tmp_path / "invalid.yaml"
    source.write_bytes(source_bytes)
    with pytest.raises(IconImportError) as error:
        import_theme_assets(source, tmp_path / "catalog.yaml")
    assert error.value.code == code
    assert operand in error.value.detail


def test_theme_source_root_diagnostic_bounds_untrusted_key_sample(tmp_path):
    source = tmp_path / "many-keys.yaml"
    value = {"version": "wrong", "kind": "bad", "id": "bad", "body": {},
             **{f"unexpected-key-{index:04d}": index for index in range(1200)}}
    source.write_text(yaml.safe_dump(value, sort_keys=True), encoding="utf-8")
    with pytest.raises(IconImportError) as error:
        import_theme_assets(source, tmp_path / "catalog.yaml")
    assert error.value.code == "E_THEME_ASSET_SOURCE_SCHEMA"
    assert "count=1204" in error.value.detail
    assert "unexpected-key-0000" in error.value.detail
    assert len(error.value.detail) < 300


def test_theme_source_io_diagnostic_names_missing_path(tmp_path):
    source = tmp_path / "missing-theme-source.yaml"
    with pytest.raises(IconImportError) as error:
        import_theme_assets(source, tmp_path / "catalog.yaml")
    assert error.value.code == "E_THEME_ASSET_SOURCE_IO"
    assert error.value.source_ref == str(source)
    assert "FileNotFoundError" in error.value.detail


def test_theme_source_limit_diagnostic_reports_actual_source_byte_length(tmp_path):
    source = tmp_path / "oversize-theme-source.yaml"
    source.write_bytes(b"x" * 4_000_001)
    with pytest.raises(IconImportError) as error:
        import_theme_assets(source, tmp_path / "catalog.yaml")
    assert error.value.code == "E_THEME_ASSET_SOURCE_LIMIT"
    assert "4000001" in error.value.detail and "1..4000000" in error.value.detail
