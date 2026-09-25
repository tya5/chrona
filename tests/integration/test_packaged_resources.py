from importlib.resources import files
from pathlib import Path
import gzip
from hashlib import sha256
from time import perf_counter

import yaml

from chrona.resources import schema_resource, template_resource
from chrona.presentation.contracts import ClosureIdentity, IconCatalogContract, parse_contract


ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / "pyproject.toml").is_file())
RESOURCES = files("chrona.resources")
SCHEMAS = (
    "project-v0.7.schema.yaml",
    "profile-v0.3.schema.yaml",
    "revision-store-resource-ref-v0.1.schema.yaml",
    "icon-catalog-v0.3.schema.yaml",
    "render-context-v0.12.schema.yaml",
    "render-context-v0.15.schema.yaml",
    "render-context-v0.16.schema.yaml",
    "view-v0.15.schema.yaml",
    "view-v0.19.schema.yaml",
    "view-v0.20.schema.yaml",
    "view-v0.21.schema.yaml",
    "layout-profile-v0.3.schema.yaml",
    "layout-profile-v0.4.schema.yaml",
    "layout-profile-v0.5.schema.yaml",
    "layout-profile-v0.9.schema.yaml",
    "scene-v0.6.schema.yaml",
    "review-detail-profile-v0.1.schema.yaml",
    "actual-intake-batch-v0.2.schema.yaml",
    "actual-set-v0.3.schema.yaml",
    "authoring-command-result-v0.1.schema.yaml",
    "command-request-v0.2.schema.yaml",
    "automation-result-v0.1.schema.yaml",
    "snapshot-ref-v0.2.schema.yaml",
    "store-config-v0.1.schema.yaml",
    "theme-v0.9.schema.yaml",
    "theme-v0.10.schema.yaml",
    "theme-v0.11.schema.yaml",
)


def test_schema_resources_resolve_to_the_source_authority():
    for name in SCHEMAS:
        assert schema_resource(name).read_bytes() == (ROOT / "schemas" / name).read_bytes()


def test_init_template_resolves_to_the_single_source_authority():
    template = template_resource("halcyon-1")

    assert template.joinpath("manifest.yaml").read_bytes() == (ROOT / "examples" / "halcyon-1" / "manifest.yaml").read_bytes()


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
