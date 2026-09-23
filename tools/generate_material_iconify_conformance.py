#!/usr/bin/env python3
"""Generate offline Material Symbols alias conformance evidence.

This is an authoring-only verifier.  CI reads its committed JSON output and
never requires Node, npm, or a registry.
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


ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / "src/chrona/resources/icons"
CATALOG = RESOURCES / "material-symbols-outline-rounded-v2026-09-22.yaml"
OUTPUT = ROOT / "tests/fixtures/icons/material-symbols-iconify-utils-v3.1.7.json"
MATERIAL_PACKAGE = "@iconify-json/material-symbols@1.2.93"
UTILS_PACKAGE = "@iconify/utils@3.1.7"


def _pack(package: str, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    subprocess.run(["npm", "pack", "--silent", package, "--pack-destination", str(destination)], check=True)
    archive, = destination.glob("*.tgz")
    target = destination / archive.stem
    with tarfile.open(archive) as source:
        source.extractall(target, filter="data")
    return target / "package"


def main() -> None:
    if shutil.which("npm") is None or shutil.which("node") is None:
        raise SystemExit("npm and node are required only to regenerate this fixture")
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        material_root, utils_root = _pack(MATERIAL_PACKAGE, root / "material"), _pack(UTILS_PACKAGE, root / "utils")
        collection_path = material_root / "icons.json"
        collection_bytes = collection_path.read_bytes()
        catalog = yaml.load(CATALOG.read_bytes(), Loader=yaml.CSafeLoader)["body"]
        names = sorted(set(catalog["icons"]) | set(catalog["entryAliases"]))
        names_path, output_path = root / "names.json", root / "resolved.json"
        names_path.write_text(json.dumps(names), encoding="utf-8")
        script = root / "resolve.mjs"
        script.write_text(
            "import {readFile,writeFile} from 'node:fs/promises';\n"
            "import {pathToFileURL} from 'node:url';\n"
            "const [collectionPath,namesPath,utilsPath,out] = process.argv.slice(2);\n"
            "const {getIconData} = await import(pathToFileURL(utilsPath));\n"
            "const collection=JSON.parse(await readFile(collectionPath,'utf8'));\n"
            "const names=JSON.parse(await readFile(namesPath,'utf8'));\n"
            "const pick=(data)=>data&&({body:data.body,width:data.width,height:data.height,left:data.left,top:data.top,rotate:data.rotate,hFlip:data.hFlip,vFlip:data.vFlip});\n"
            "await writeFile(out,JSON.stringify(Object.fromEntries(names.map(name=>[name,pick(getIconData(collection,name))]))));\n",
            encoding="utf-8",
        )
        subprocess.run(["node", str(script), str(collection_path), str(names_path),
                        str(utils_root / "lib/index.js"), str(output_path)], check=True)
        resolved = json.loads(output_path.read_text(encoding="utf-8"))
    entries = {}
    for name in names:
        data = resolved.get(name)
        if not isinstance(data, dict) or not isinstance(data.get("body"), str):
            raise SystemExit(f"Iconify utils did not resolve bundled name: {name}")
        canonical = str(catalog["entryAliases"].get(name, name))
        entry = catalog["icons"].get(canonical)
        if not isinstance(entry, dict):
            raise SystemExit(f"bundled name has no canonical catalog entry: {name}")
        entries[name] = {
            "canonical": canonical,
            "bodySha256": sha256(data["body"].encode()).hexdigest(),
            "width": data.get("width", 16), "height": data.get("height", 16),
            "rotate": data.get("rotate", 0), "hFlip": bool(data.get("hFlip", False)), "vFlip": bool(data.get("vFlip", False)),
            "catalogViewport": entry["viewport"],
            "catalogGeometrySha256": sha256(json.dumps(entry, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        }
    payload = {
        "format": "chrona/iconify-utils-conformance/v0.1", "utilsPackage": UTILS_PACKAGE,
        "sourcePackage": MATERIAL_PACKAGE,
        "sourceContentIdentity": "sha256:" + sha256(collection_bytes).hexdigest(),
        "entries": entries,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
