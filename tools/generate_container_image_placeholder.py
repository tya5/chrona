#!/usr/bin/env python3
"""Regenerate HALCYON-1's #465 image-backed annotation container fixture.

This is deliberately not a general importer (Specification 64 §7 reuses the
icon catalogue's identity/closure engineering, not its ingestion command):
the artwork is repository-owned, non-photographic (a bordered nine-slice
panel, not a scan or screenshot of a licensed asset), and hand-normalized
into the ordinary ``chrona/icon-catalog/v0.3`` raster-entry shape. Its
content-area colour is chosen to match the wallboard Theme's own
``surfaceRaised`` intent exactly, so the Theme's declared representative
ground colour for contrast/perceptibility (#459, #446) is not a guess.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import struct
import zlib

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/halcyon-1"
ASSETS = EXAMPLE / "assets"
CATALOG = EXAMPLE / "icons.yaml"

VIEWPORT = (40, 40)
BORDER = (60, 63, 94, 255)  # "neutral" #2E3F5E, opaque
CONTENT = (22, 33, 58, 255)  # "surfaceRaised" #16213A, opaque
BORDER_WIDTH = 6


def _panel() -> bytes:
    width, height = VIEWPORT
    rows = bytearray()
    for y in range(height):
        rows.append(0)  # no filter
        for x in range(width):
            on_border = x < BORDER_WIDTH or y < BORDER_WIDTH or x >= width - BORDER_WIDTH or y >= height - BORDER_WIDTH
            rows.extend(BORDER if on_border else CONTENT)

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff)

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(rows), 9))
            + chunk(b"IEND", b""))


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    payload = _panel()
    raster_path = ASSETS / "annotation-container.png"
    raster_path.write_bytes(payload)
    catalog = {
        "version": "chrona/icon-catalog/v0.3", "kind": "icon-catalog", "id": "halcyon-1-icons",
        "body": {
            "set": "halcyon", "aliases": [],
            "provenance": {
                "sourceKind": "iconify-json", "sourcePrefix": "halcyon",
                "sourceContentIdentity": "sha256:" + sha256(b"halcyon-1-purpose-built").hexdigest(),
                "sourceVersion": "halcyon-1-v1",
                "license": {"spdx": "CC0-1.0",
                           "notice": ("HALCYON-1 purpose-built annotation-container artwork.\n"
                                      "Released under CC0-1.0.")},
            },
            "icons": {
                "annotation-container": {
                    "kind": "raster",
                    "source": {"address": "assets/annotation-container.png",
                              "contentIdentity": "sha256:" + sha256(payload).hexdigest()},
                    "viewport": {"inlineSize": VIEWPORT[0], "blockSize": VIEWPORT[1]},
                    "alternative": "Annotation container frame",
                },
            },
            "entryAliases": {},
        },
    }
    CATALOG.write_text(yaml.safe_dump(catalog, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    main()
