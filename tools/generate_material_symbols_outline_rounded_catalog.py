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

import yaml

from chrona.presentation.icons.importer import import_iconify


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "@iconify-json/material-symbols@1.2.93"
RESOURCES = ROOT / "src/chrona/resources/icons"
MANIFEST = RESOURCES / "material-symbols-outline-rounded-v2026-09-22.manifest"
CATALOG = RESOURCES / "material-symbols-outline-rounded-v2026-09-22.yaml"
NOTICE = RESOURCES / "material-symbols-outline-rounded.NOTICE"
PROJECTION = RESOURCES / "material-symbols-outline-rounded-v2026-09-22.projection.json"
MAX_CATALOG_BYTES = 7_000_000
MAX_GZIP_BYTES = 1_600_000


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
        selected = {name for name in parsed["icons"] if name.endswith("-outline-rounded")}
        if len(selected) != 2336:
            raise SystemExit(f"unexpected Material Symbols Outline Rounded count: {len(selected)}")
        raw_aliases = parsed.get("aliases", {})
        if not isinstance(raw_aliases, dict):
            raise SystemExit("Material Symbols aliases are not an object")
        def terminal(name: str) -> str:
            seen: set[str] = set()
            while name in raw_aliases:
                if name in seen or not isinstance(raw_aliases[name], dict) or not isinstance(raw_aliases[name].get("parent"), str):
                    raise SystemExit(f"invalid Material Symbols alias chain: {name}")
                seen.add(name); name = raw_aliases[name]["parent"]
            if name not in parsed["icons"]:
                raise SystemExit(f"Material Symbols alias has unknown terminal: {name}")
            return name
        variant_aliases = {name: terminal(name) for name in raw_aliases if name.endswith("-outline-rounded")}
        closure = set(variant_aliases.values()) - selected
        names = sorted(selected | closure)
        MANIFEST.write_text(
            "# Material Symbols Outline Rounded; generated from " + PACKAGE + "\n"
            f"# canonicalSelection={len(selected)} aliasParentClosure={len(closure)} "
            f"maxCatalogBytes={MAX_CATALOG_BYTES} maxGzipBytes={MAX_GZIP_BYTES}\n"
            + "\n".join(names) + "\n", encoding="utf-8")
        import_iconify(collection, CATALOG, set_name="material", aliases=("material-symbols",),
                       license_spdx="Apache-2.0", notice_path=NOTICE, include_path=MANIFEST,
                       source_version=PACKAGE.rsplit("@", 1)[1])
        catalog = yaml.load(CATALOG.read_bytes(), Loader=yaml.CSafeLoader)
        body = catalog["body"]
        aliases = body["entryAliases"]
        suffix = "-outline-rounded"
        short_candidates: dict[str, list[str]] = {}
        for name in body["icons"]:
            if name.endswith(suffix):
                short_candidates.setdefault(name.removesuffix(suffix), []).append(name)
        for short, candidates in sorted(short_candidates.items()):
            if len(candidates) == 1 and short not in body["icons"] and short not in aliases:
                aliases[short] = candidates[0]
        catalog_bytes = yaml.safe_dump(catalog, sort_keys=False).encode()
        CATALOG.write_bytes(catalog_bytes)
        projection = {
            "format": "chrona/icon-catalog-projection/v0.1",
            "catalogIdentity": "sha256:" + sha256(catalog_bytes).hexdigest(),
            "id": catalog["id"], "version": catalog["version"], "body": catalog["body"],
        }
        PROJECTION.write_text(json.dumps(projection, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        if len(catalog_bytes) > MAX_CATALOG_BYTES:
            raise SystemExit("Material Symbols catalog exceeded declared byte limit")
        import gzip
        if len(gzip.compress(catalog_bytes, compresslevel=9)) > MAX_GZIP_BYTES:
            raise SystemExit("Material Symbols catalog exceeded declared gzip byte limit")
        print(json.dumps({"sourceContentIdentity": "sha256:" + sha256(collection.read_bytes()).hexdigest(),
                          "selectionCount": len(selected), "aliasParentClosureCount": len(closure),
                          "catalog": str(CATALOG.relative_to(ROOT))}, sort_keys=True))


if __name__ == "__main__":
    main()
