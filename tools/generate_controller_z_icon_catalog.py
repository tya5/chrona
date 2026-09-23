#!/usr/bin/env python3
"""Regenerate Controller Z's importer-provenanced vector/raster icon fixture."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import struct
import zlib

import yaml

from chrona.presentation.icons.importer import import_iconify


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/controller-z"
ASSETS = EXAMPLE / "assets"
CATALOG = EXAMPLE / "icons.yaml"


def _png() -> bytes:
    """A 24px purpose-built programme mark, not a scaled review screenshot."""
    rows = bytearray()
    for y in range(24):
        rows.append(0)
        for x in range(24):
            active = 3 <= x <= 20 and 3 <= y <= 20
            accent = active and ((x + y) % 7 in {0, 1})
            rows.extend((91, 67, 166, 255) if active and not accent else
                        (243, 178, 75, 255) if accent else (0, 0, 0, 0))
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 24, 24, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(bytes(rows), 9)) + chunk(b"IEND", b"")


def main() -> None:
    raster = _png()
    raster_path = ASSETS / "programme-mark.png"
    raster_path.write_bytes(raster)
    import_iconify(ASSETS / "icons-source.json", CATALOG, set_name="chrona", license_spdx="CC0-1.0",
                   notice_path=ASSETS / "icons.NOTICE")
    value = yaml.load(CATALOG.read_bytes(), Loader=yaml.CSafeLoader)
    value["id"] = "controller-z-icons"
    value["body"]["icons"]["programme"] = {
        "kind": "raster", "source": {"address": "assets/programme-mark.png", "contentIdentity": "sha256:" + sha256(raster).hexdigest()},
        "viewport": {"inlineSize": 24, "blockSize": 24}, "alternative": "Programme overview",
    }
    CATALOG.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    main()
