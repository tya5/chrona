from importlib.resources import files
from pathlib import Path
import gzip
from hashlib import sha256
from time import perf_counter

import yaml

from chrona.resources import schema_resource
from chrona.presentation.contracts import ClosureIdentity, IconCatalogContract, parse_contract


ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / "pyproject.toml").is_file())
RESOURCES = files("chrona.resources")
SCHEMAS = (
    "project-v0.6.schema.yaml",
    "profile-v0.2.schema.yaml",
    "revision-store-resource-ref-v0.1.schema.yaml",
    "icon-catalog-v0.3.schema.yaml",
    "render-context-v0.12.schema.yaml",
    "render-context-v0.14.schema.yaml",
    "view-v0.12.schema.yaml",
    "layout-profile-v0.3.schema.yaml",
    "layout-profile-v0.4.schema.yaml",
    "review-detail-profile-v0.1.schema.yaml",
    "actual-intake-batch-v0.2.schema.yaml",
    "actual-set-v0.2.schema.yaml",
    "command-request-v0.2.schema.yaml",
    "automation-result-v0.1.schema.yaml",
    "snapshot-ref-v0.2.schema.yaml",
    "store-config-v0.1.schema.yaml",
)


def test_schema_resources_resolve_to_the_source_authority():
    for name in SCHEMAS:
        assert schema_resource(name).read_bytes() == (ROOT / "schemas" / name).read_bytes()


def test_package_owned_runtime_resources_exist():
    for resource_path in (
        "font_metrics/noto-sans-cjk-jp-regular-v1.json",
        "font_metrics/noto-sans-cjk-jp-bold-v1.json",
        "fonts/noto-sans-cjk-jp-regular-v1.ttf",
        "fonts/noto-sans-cjk-jp-bold-v1.ttf",
        "fonts/NotoSansCJKJP.LICENSE",
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
