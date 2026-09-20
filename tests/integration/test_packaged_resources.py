from importlib.resources import files
from pathlib import Path

from chrona.resources import schema_resource


ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / "pyproject.toml").is_file())
RESOURCES = files("chrona.resources")
SCHEMAS = (
    "project-v0.1.schema.yaml",
    "profile-v0.1.schema.yaml",
    "revision-store-resource-ref-v0.1.schema.yaml",
    "project-v0.2.schema.yaml",
    "presentation-settings-v0.2.schema.json",
    "presentation-preset-v0.2.schema.json",
    "layout-profile-v0.1.schema.yaml",
    "review-detail-profile-v0.1.schema.yaml",
)


def test_schema_resources_resolve_to_the_source_authority():
    for name in SCHEMAS:
        assert schema_resource(name).read_bytes() == (ROOT / "schemas" / name).read_bytes()


def test_package_owned_runtime_resources_exist():
    for resource_path in (
        "presets/presentation-settings-executive-v0.2.json",
        "font_metrics/nimbus-sans-regular-v1.json",
        "font_metrics/nimbus-sans-bold-v1.json",
    ):
        assert RESOURCES.joinpath(*resource_path.split("/")).is_file(), resource_path
