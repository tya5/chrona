"""Exercise installed-wheel behavior without reading repository resources."""
from __future__ import annotations

import sys
from pathlib import Path
import subprocess
import tempfile
import json
from unittest.mock import patch

from chrona.app.cli import main
from chrona.core.validation import validate_project
from chrona.resources import (
    SCHEMA_PARTS, builtin_preset_source_root, schema_document, schema_registry, schema_resource, schema_validator,
    skill_resource, validator_for_schema,
)
from chrona.resources import safe_load
from chrona.scheduling.scheduler import schedule


PROJECT = {
    "version": "timeline/v0.7",
    "project": {"id": "wheel-smoke", "title": "Wheel smoke"},
    "objects": {
        "task": {
            "type": "task",
            "title": "Task",
            "schedule": {
                "mode": "fixed-span",
                "start": "2026-01-01",
                "end": "2026-01-02",
            },
        }
    },
}


def run() -> None:
    assert validate_project(PROJECT) == []
    assert schedule(PROJECT).ok
    assert schema_resource("layout-profile-v0.10.schema.yaml").is_file()
    assert schema_resource("render-context-v0.17.schema.yaml").is_file()
    for name in ("command-request-v0.3", "automation-result-v0.2", "snapshot-ref-v0.3"):
        assert schema_resource(name + ".schema.yaml").is_file(), name
    # The registry is built from the installed wheel's own schema parts, and a
    # schema that references a part reaches it without any repository file.
    resolver = schema_registry().resolver()
    for part in SCHEMA_PARTS:
        assert schema_resource(part).is_file(), part
        assert resolver.lookup(schema_document(part)["$id"]).contents["$id"] == schema_document(part)["$id"], part
    assert tuple(schema_validator("view-v0.28.schema.yaml").iter_errors({})), "view schema did not reach its part"
    common_date = validator_for_schema({"$ref": "urn:chrona:common-v0.1#/$defs/isoDate"})
    assert common_date.is_valid("2026-09-30") and not common_date.is_valid("not-a-date"), "common part not reachable"
    vocabulary_profile = validator_for_schema({"$ref": "urn:chrona:vocabulary-v0.1#/$defs/visualProfile"})
    assert (vocabulary_profile.is_valid("chrona-output/visual/v0.5-baseline")
            and not vocabulary_profile.is_valid("chrona-output/visual/v9")), "vocabulary part not reachable"
    graphics_tile = validator_for_schema({"$ref": "urn:chrona:graphics-v0.1#/$defs/tile"})
    assert (graphics_tile.is_valid({"inlineSize": 8, "blockSize": 8})
            and not graphics_tile.is_valid({"inlineSize": 0, "blockSize": 8})), "graphics part not reachable"
    store_address = validator_for_schema({"$ref": "urn:chrona:common-v0.1#/$defs/storeAddress"})
    assert (store_address.is_valid("resources/project.yaml")
            and not store_address.is_valid("C:/x") and not store_address.is_valid("a/../b")), "storeAddress not reachable"
    store_reference = validator_for_schema({"$ref": "urn:chrona:revision-store-resource-ref-v0.2"})
    reference = {"id": "p", "kind": "project", "store": {"provider": "local", "identity": "s"},
                 "address": "projects/main.yaml", "revision": {"token": "main"}}
    assert (store_reference.is_valid(reference)
            and not store_reference.is_valid({**reference, "address": "../x"})), "revision-store-resource-ref v0.2 not reachable"
    icons = builtin_preset_source_root("icons")
    for name in ("chrona-theme-starter-v2026-10-09.source.yaml",
                 "chrona-theme-starter-v2026-10-09.yaml",
                 "chrona-theme-starter-v2026-10-09.manifest",
                 "chrona-theme-starter.NOTICE"):
        assert icons.joinpath(name).is_file(), name
    try:
        with patch.object(sys, "argv", ["chrona", "--help"]):
            main()
    except SystemExit as error:
        assert error.code == 0
    else:
        raise AssertionError("CLI help did not terminate through argparse")
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        starter, corpus = root / "my-chrona-project", root / "my-halcyon-example"
        output = corpus / "out"
        draft = root / "draft-project.yaml"
        default_svg, starter_svg = root / "default.svg", starter / "plan.svg"
        catalog, raster = root / "material.yaml", root / "smoke.png"
        asset_preset, asset_svg = root / "asset-preset", root / "asset-preset.svg"
        skill, skill_svg = root / "agent-skill" / "chrona", root / "skill-example.svg"
        draft.write_text(json.dumps(PROJECT), encoding="utf-8")
        for arguments in (
            ["init", str(starter)],
            ["render", str(starter / "project.yaml"), "--actual", str(starter / "actual.yaml"), "--output", str(starter_svg)],
            ["init", str(corpus), "--example", "halcyon-1"],
            ["render", str(draft), "--output", str(default_svg)],
            ["materialize", str(corpus / "manifest.yaml"), "--slide", "mission-brief", "--output", str(output)],
            ["icon-catalog", "material-default", "--output", str(catalog)],
            ["preset", "copy", "technical-print", "--output", str(asset_preset)],
            ["skill", "copy", "--output", str(skill)],
            ["validate", str(skill / "examples" / "launch.yaml")],
            ["schedule", str(skill / "examples" / "launch.yaml")],
            ["render", str(skill / "examples" / "launch.yaml"), "--output", str(skill_svg)],
            ["render", str(corpus / "project.yaml"), "--preset", "technical-print", "--output", str(asset_svg)],
            ["render", str(corpus / "project.yaml"),
             "--view", str(corpus / "views/01-mission-brief.yaml"),
             "--theme", str(corpus / "themes/briefing.yaml"),
             "--scheme", str(corpus / "schemes/mission-light.yaml"),
             "--layout", str(corpus / "layouts/briefing.yaml"),
             "--actual", str(corpus / "actual.yaml"), "--format", "png",
             "--visual-profile", "chrona-output/visual/v0.6-png", "--output", str(raster)],
        ):
            command = [sys.executable, "-m", "chrona", *arguments]
            completed = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
            if completed.returncode:
                raise AssertionError(f"documented fresh-project command failed: chrona {' '.join(arguments)}\n{completed.stdout}\n{completed.stderr}")
        if not (output / "review.svg").is_file():
            raise AssertionError("documented materialize command did not create its artifact")
        if not default_svg.read_bytes().startswith(b"<svg"):
            raise AssertionError("no-preset Draft render did not use the bundled default")
        if not starter_svg.read_bytes().startswith(b"<svg"):
            raise AssertionError("minimal initialized project did not render with the bundled default")
        if not asset_svg.read_bytes().startswith(b"<svg"):
            raise AssertionError("wheel-owned catalogue preset did not render without asset flags")
        packaged = skill_resource()
        assert packaged.joinpath("SKILL.md").is_file(), "the wheel does not carry the agent skill"
        for relative in ("SKILL.md", "examples/launch.yaml", "references/diagnostics.md"):
            assert (skill / relative).read_bytes() == packaged.joinpath(*relative.split("/")).read_bytes(), relative
        assert (skill / "SKILL.md").read_text(encoding="utf-8").startswith("---\nname: chrona\n"), "skill front matter"
        if not skill_svg.read_bytes().startswith(b"<svg"):
            raise AssertionError("the skill's worked example did not render from the installed copy")
        if not (asset_preset / "catalogs/chrona-theme-starter-v2026-10-09.NOTICE").is_file():
            raise AssertionError("wheel-owned catalogue notice was not copied")
        catalog_value = safe_load(catalog.read_bytes())
        catalog_body = catalog_value.get("body") if isinstance(catalog_value, dict) else None
        if (not isinstance(catalog_value, dict) or catalog_value.get("version") != "chrona/icon-catalog/v0.3"
                or catalog_value.get("kind") != "icon-catalog" or not isinstance(catalog_body, dict)
                or not catalog_body.get("icons")):
            raise AssertionError("bundled Material Symbols catalog was not copied")
        if not raster.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
            raise AssertionError("Draft PNG render did not open bundled font bytes")
    print("Chrona installed-wheel smoke: PASS")


if __name__ == "__main__":
    run()
