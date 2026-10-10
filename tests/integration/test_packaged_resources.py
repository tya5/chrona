from importlib.resources import files
from pathlib import Path
import gzip
from hashlib import sha256
from time import perf_counter

import pytest
import tomllib
import yaml

from chrona.resources import axis_name_tables_resource, example_ids, example_registry, minimal_template_resource, schema_resource, template_resource
from chrona.resources import SCHEMA_PARTS, schema_registry
from chrona.presentation.contracts import ClosureIdentity, IconCatalogContract, parse_contract


ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / "pyproject.toml").is_file())
RESOURCES = files("chrona.resources")
SCHEMAS = (
    "axis-name-tables-v0.1.schema.yaml",
    "common-v0.1.schema.yaml",
    "graphics-v0.1.schema.yaml",
    "project-v0.7.schema.yaml",
    "profile-v0.3.schema.yaml",
    "revision-store-resource-ref-v0.1.schema.yaml",
    "revision-store-resource-ref-v0.2.schema.yaml",
    "presentation-resource-v0.1.schema.yaml",
    "icon-catalog-v0.3.schema.yaml",
    "icon-catalog-v0.5.schema.yaml",
    "theme-asset-source-v0.2.schema.yaml",
    "render-context-v0.17.schema.yaml",
    "view-v0.28.schema.yaml",
    "vocabulary-v0.1.schema.yaml",
    "layout-profile-v0.10.schema.yaml",
    "scene-v0.6.schema.yaml",
    "scene-v0.7.schema.yaml",
    "review-detail-profile-v0.1.schema.yaml",
    "actual-intake-batch-v0.2.schema.yaml",
    "actual-set-v0.3.schema.yaml",
    "authoring-command-result-v0.1.schema.yaml",
    "command-request-v0.3.schema.yaml",
    "automation-result-v0.2.schema.yaml",
    "snapshot-ref-v0.2.schema.yaml",
    "snapshot-ref-v0.3.schema.yaml",
    "store-config-v0.1.schema.yaml",
    "theme-v0.15.schema.yaml",
    "theme-v0.16.schema.yaml",
    "preset-library-v0.2.schema.yaml",
    "example-registry-v0.1.schema.yaml",
)


def test_schema_resources_resolve_to_the_source_authority():
    for name in SCHEMAS:
        assert schema_resource(name).read_bytes() == (ROOT / "schemas" / name).read_bytes()


def test_every_schema_part_is_packaged_and_registered():
    assert set(SCHEMA_PARTS) <= set(SCHEMAS)
    for name in SCHEMA_PARTS:
        assert schema_resource(name).read_bytes() == (ROOT / "schemas" / name).read_bytes()
        part_id = yaml.safe_load(schema_resource(name).read_bytes())["$id"]
        assert schema_registry().resolver().lookup(part_id).contents["$id"] == part_id


def test_init_template_resolves_to_the_single_source_authority():
    template = template_resource("halcyon-1")

    assert template.joinpath("manifest.yaml").read_bytes() == (ROOT / "examples" / "halcyon-1" / "manifest.yaml").read_bytes()


def test_example_registry_names_exactly_the_examples_the_wheel_ships():
    """#574: `init --example` choices come from the registry, and the wheel ships
    exactly the registered examples (no unregistered corpus rides along)."""
    assert example_ids() == ("halcyon-1", "onboarding")
    for entry in example_registry().values():
        template = template_resource(entry["id"])
        assert template.joinpath("manifest.yaml").is_file() or any(
            child.joinpath("project.yaml").is_file() for child in template.iterdir() if child.is_dir())
    forced = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    shipped = {source for source in forced if source.startswith("examples/")}
    assert shipped == {entry["path"] for entry in example_registry().values()}


def test_unregistered_example_is_rejected_naming_the_available_ids():
    with pytest.raises(ValueError, match=r"E_INIT_EXAMPLE.*'controller-z'.*halcyon-1, onboarding"):
        template_resource("controller-z")


def test_axis_name_table_catalog_is_packaged_from_one_source_authority():
    assert axis_name_tables_resource().read_bytes() == (ROOT / "src/chrona/resources/axis-name-tables-v0.1.yaml").read_bytes()


def test_minimal_init_template_is_a_wheel_owned_non_corpus_resource():
    template = minimal_template_resource()

    assert {item.name for item in template.iterdir()} == {"README.md", "actual.yaml", "project.yaml"}
    assert not template.joinpath("manifest.yaml").is_file()


def test_package_owned_runtime_resources_exist():
    for resource_path in (
        "font_metrics/noto-sans-regular-v1.json",
        "font_metrics/noto-sans-bold-v1.json",
        "fonts/noto-sans-regular-v1.ttf",
        "fonts/noto-sans-bold-v1.ttf",
        "fonts/NotoSans.LICENSE",
        "font_metrics/noto-sans-mono-regular-v2.json",
        "fonts/noto-sans-mono-regular-v1.ttf",
        "fonts/NotoSansMono.LICENSE",
        "font_metrics/noto-color-emoji-check-v1.json",
        "fonts/draft-substitute-font-metrics.yaml",
        "fonts/NotoColorEmoji.LICENSE",
        "icons/chrona-theme-starter-v2026-10-09.source.yaml",
        "icons/chrona-theme-starter-v2026-10-09.yaml",
        "icons/chrona-theme-starter-v2026-10-09.manifest",
        "icons/chrona-theme-starter.NOTICE",
        "presets/library.yaml",
        "presets/bundles/control-room-dark/layout.yaml",
        "presets/bundles/control-room-dark/theme.yaml",
        "presets/bundles/control-room-dark/view.yaml",
        "presets/bundles/elevated-light/layout.yaml",
        "presets/bundles/elevated-light/theme.yaml",
        "presets/bundles/elevated-light/view.yaml",
        "presets/bundles/executive-light/layout.yaml",
        "presets/bundles/executive-light/theme.yaml",
        "presets/bundles/executive-light/view.yaml",
        "presets/bundles/mission-light/layout.yaml",
        "presets/bundles/mission-light/theme.yaml",
        "presets/bundles/mission-light/view.yaml",
        "presets/bundles/print-mono/layout.yaml",
        "presets/bundles/print-mono/theme.yaml",
        "presets/bundles/print-mono/view.yaml",
        "presets/bundles/editorial-readable-default/view.yaml",
        "presets/bundles/editorial/view.yaml",
        "presets/bundles/editorial/view-lanes.yaml",
        "presets/bundles/editorial-readable-default/theme.yaml",
        "presets/bundles/editorial/scheme.yaml",
        "presets/bundles/mission-light/scheme.yaml",
        "presets/bundles/control-room-dark/scheme.yaml",
        "presets/bundles/print-mono/scheme.yaml",
        "presets/bundles/executive-light/scheme.yaml",
        "presets/bundles/elevated-light/scheme.yaml",
    ):
        assert RESOURCES.joinpath(*resource_path.split("/")).is_file(), resource_path


def test_bundled_material_catalog_is_complete_and_size_bounded():
    catalog = RESOURCES.joinpath("icons", "material-symbols-outline-rounded-v2026-09-22.yaml").read_bytes()
    manifest = RESOURCES.joinpath("icons", "material-symbols-outline-rounded-v2026-09-22.manifest").read_text(encoding="utf-8")
    notice = RESOURCES.joinpath("icons", "material-symbols-outline-rounded.NOTICE").read_text(encoding="utf-8")
    names = [line for line in manifest.splitlines() if line and not line.startswith("#")]
    assert "canonicalSelection=2336 aliasParentClosure=1679" in manifest
    assert "maxCatalogBytes=7000000 maxGzipBytes=1600000" in manifest
    assert len(names) == 4015
    assert len(catalog) <= 7_000_000
    assert len(gzip.compress(catalog, compresslevel=9)) <= 1_600_000
    assert catalog.startswith(b'{"body":{"aliases":["material-symbols"]')
    assert "Apache License" in notice
    started = perf_counter()
    value = yaml.load(catalog, Loader=yaml.CSafeLoader)
    contract = parse_contract(ClosureIdentity("icon-catalog", value["id"], "packaged", "sha256:" + sha256(catalog).hexdigest()), value)
    assert isinstance(contract, IconCatalogContract)
    assert len(contract.entry_names) == 4015
    assert contract.provenance["sourceVersion"] == "1.2.93"
    assert contract.entry_aliases["flag"] == "flag-outline-rounded"
    assert contract.entry_aliases["check-outline-rounded"] == "check-rounded"
    assert perf_counter() - started < 10


def test_init_onboarding_copies_the_seven_stages_byte_for_byte_and_writes_no_store(tmp_path):
    from chrona.usecases.local_authoring import initialize_project

    initialize_project(tmp_path / "tutorial", example="onboarding")

    stages = sorted(path.name for path in (tmp_path / "tutorial").iterdir())
    assert stages == sorted(path.name for path in (ROOT / "examples" / "onboarding").iterdir())  # no .chrona Store, no manifest
    for source in (ROOT / "examples" / "onboarding").rglob("*.yaml"):
        assert (tmp_path / "tutorial" / source.relative_to(ROOT / "examples" / "onboarding")).read_bytes() == source.read_bytes()
