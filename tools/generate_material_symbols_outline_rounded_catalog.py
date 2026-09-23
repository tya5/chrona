#!/usr/bin/env python3
"""Regenerate Chrona's bounded Material Symbols Outline Rounded catalog.

The npm archive is an authoring-only input.  Runtime uses only the generated
catalog and notice below ``src/chrona/resources/icons``.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

from chrona.presentation.icons.importer import import_iconify


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "@iconify-json/material-symbols@1.2.93"
RESOURCES = ROOT / "src/chrona/resources/icons"
MANIFEST = RESOURCES / "material-symbols-outline-rounded-v2026-09-22.manifest"
CATALOG = RESOURCES / "material-symbols-outline-rounded-v2026-09-22.yaml"
NOTICE = RESOURCES / "material-symbols-outline-rounded.NOTICE"


def main() -> None:
    if shutil.which("npm") is None:
        raise SystemExit("npm is required only to regenerate this catalog")
    RESOURCES.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        temporary_path = Path(temporary)
        subprocess.run(["npm", "pack", "--silent", PACKAGE, "--pack-destination", temporary], check=True)
        archive, = temporary_path.glob("*.tgz")
        with tarfile.open(archive) as source:
            source.extractall(temporary_path / "package", filter="data")
        collection = temporary_path / "package/package/icons.json"
        parsed = json.loads(collection.read_text(encoding="utf-8"))
        names = sorted(name for name in parsed["icons"] if name.endswith("-outline-rounded"))
        if len(names) != 2336:
            raise SystemExit(f"unexpected Material Symbols Outline Rounded count: {len(names)}")
        MANIFEST.write_text("# Material Symbols Outline Rounded; generated from " + PACKAGE + "\n" + "\n".join(names) + "\n", encoding="utf-8")
        import_iconify(collection, CATALOG, set_name="material", aliases=("material-symbols",),
                       license_spdx="Apache-2.0", notice_path=NOTICE, include_path=MANIFEST)
        print(json.dumps({"sourceContentIdentity": "sha256:" + sha256(collection.read_bytes()).hexdigest(),
                          "selectionCount": len(names), "catalog": str(CATALOG.relative_to(ROOT))}, sort_keys=True))


if __name__ == "__main__":
    main()
