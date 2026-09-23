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
    "view-v0.12.schema.yaml",
    "layout-profile-v0.3.schema.yaml",
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
        "font_metrics/nimbus-sans-regular-v1.json",
        "font_metrics/nimbus-sans-bold-v1.json",
    ):
        assert RESOURCES.joinpath(*resource_path.split("/")).is_file(), resource_path


def test_bundled_material_catalog_is_complete_and_size_bounded():
    catalog = RESOURCES.joinpath("icons", "material-symbols-outline-rounded-v2026-09-22.yaml").read_bytes()
    manifest = RESOURCES.joinpath("icons", "material-symbols-outline-rounded-v2026-09-22.manifest").read_text()
    notice = RESOURCES.joinpath("icons", "material-symbols-outline-rounded.NOTICE").read_text()
    names = [line for line in manifest.splitlines() if line and not line.startswith("#")]
    assert len(names) == 2336
    assert len(catalog) <= 4_000_000
    assert len(gzip.compress(catalog, compresslevel=9)) <= 1_000_000
    assert b"set: material\n" in catalog and b"- material-symbols\n" in catalog
    assert "Apache License" in notice
    started = perf_counter()
    value = yaml.load(catalog, Loader=yaml.CSafeLoader)
    contract = parse_contract(ClosureIdentity("icon-catalog", value["id"], "packaged", "sha256:" + sha256(catalog).hexdigest()), value)
    assert isinstance(contract, IconCatalogContract)
    assert len(contract.entries) == 2336
    assert perf_counter() - started < 10
