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
from chrona.resources import schema_resource
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
    assert schema_resource("layout-profile-v0.3.schema.yaml").is_file()
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
        draft.write_text(json.dumps(PROJECT), encoding="utf-8")
        for arguments in (
            ["init", str(starter)],
            ["render", str(starter / "project.yaml"), "--actual", str(starter / "actual.yaml"), "--output", str(starter_svg)],
            ["init", str(corpus), "--example", "halcyon-1"],
            ["render", str(draft), "--output", str(default_svg)],
            ["materialize", str(corpus / "manifest.yaml"), "--slide", "mission-brief", "--output", str(output)],
            ["icon-catalog", "material-default", "--output", str(catalog)],
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
