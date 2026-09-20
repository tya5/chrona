from importlib.resources import files
from pathlib import Path


ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / "pyproject.toml").is_file())
RESOURCES = files("chrona.resources")

MIRRORS = {
    "schemas/project-v0.1.schema.yaml": ROOT / "schemas/project-v0.1.schema.yaml",
    "schemas/profile-v0.1.schema.yaml": ROOT / "schemas/profile-v0.1.schema.yaml",
    "schemas/revision-store-resource-ref-v0.1.schema.yaml":
        ROOT / "schemas/revision-store-resource-ref-v0.1.schema.yaml",
    "schemas/project-v0.2.schema.yaml": ROOT / "schemas/project-v0.2.schema.yaml",
    "schemas/presentation-settings-v0.2.schema.json":
        ROOT / "schemas/presentation-settings-v0.2.schema.json",
    "schemas/presentation-preset-v0.2.schema.json":
        ROOT / "schemas/presentation-preset-v0.2.schema.json",
    "schemas/layout-profile-v0.1.schema.yaml":
        ROOT / "schemas/layout-profile-v0.1.schema.yaml",
    "schemas/review-detail-profile-v0.1.schema.yaml":
        ROOT / "schemas/review-detail-profile-v0.1.schema.yaml",
    "presets/presentation-settings-executive-v0.2.json":
        ROOT / "conformance/presentation-settings-executive-v0.2.json",
    "font_metrics/nimbus-sans-regular-v1.json":
        ROOT / "docs/assets/font-metrics/nimbus-sans-regular-v1.json",
    "font_metrics/nimbus-sans-bold-v1.json":
        ROOT / "docs/assets/font-metrics/nimbus-sans-bold-v1.json",
}


def test_packaged_runtime_resource_mirrors_are_exact():
    for resource_path, authority in MIRRORS.items():
        packaged = RESOURCES.joinpath(*resource_path.split("/"))
        assert packaged.read_bytes() == authority.read_bytes(), resource_path
