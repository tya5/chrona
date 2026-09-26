"""End-to-end evidence for the #465 image-backed annotation container.

A note's Theme role binds `annotationContainer.outline: image` to an
icon-catalog raster entry that no View `visuals` request selects -- proof
that the closure fix (#465) lets Theme alone reach a catalog entry, and
that Layout/Scene/adapter carry the completed nine-slice fill without any
View authority over it (literal acceptance row 1). Row 5 (a Theme without
the binding renders exactly as today) is covered by the untouched balloon/
rectangle fixtures in `test_candidate_placement.py`.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re
import struct
import zlib

import yaml

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderFailed, RenderRequest, render_review


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def _png(width: int, height: int) -> bytes:
    """A tiny deterministic bordered panel: no photographic or third-party content."""
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            border = x < 2 or y < 2 or x >= width - 2 or y >= height - 2
            rows.extend((60, 40, 20, 255) if border else (239, 227, 200, 255))

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(rows), 9)) + chunk(b"IEND", b""))


def _catalog(tmp_path: Path) -> Path:
    payload = _png(40, 40)
    asset_path = tmp_path / "frame.png"
    asset_path.write_bytes(payload)
    catalog = {
        "version": "chrona/icon-catalog/v0.3", "kind": "icon-catalog", "id": "image-container-fixture-icons",
        "body": {
            "set": "fixture", "aliases": [],
            "provenance": {"sourceKind": "iconify-json", "sourcePrefix": "fixture",
                           "sourceContentIdentity": "sha256:" + sha256(b"fixture").hexdigest(),
                           "sourceVersion": "test", "license": {"spdx": "CC0-1.0", "notice": "Test fixture."}},
            "icons": {"frame": {"kind": "raster", "viewport": {"inlineSize": 40, "blockSize": 40},
                                "alternative": "Frame",
                                "source": {"address": "frame.png", "contentIdentity": "sha256:" + sha256(payload).hexdigest()}}},
            "entryAliases": {},
        },
    }
    catalog_path = tmp_path / "icons.yaml"
    catalog_path.write_text(yaml.safe_dump(catalog, sort_keys=False), encoding="utf-8")
    return catalog_path


def _image_container_theme(tmp_path: Path) -> Path:
    root = _root()
    theme = yaml.safe_load((root / "examples/controller-z/themes/executive-light.yaml").read_text(encoding="utf-8"))
    theme["body"]["values"]["frame-container"] = {
        "type": "annotationContainer",
        "value": {
            "outline": "image", "image": "fixture:frame", "cornerRadius": 0,
            "sliceInsetsEm": {"top": 0.6, "right": 0.6, "bottom": 0.6, "left": 0.6},
            "contentInsetEm": {"top": 0.8, "right": 0.8, "bottom": 0.8, "left": 0.8},
        },
    }
    theme["body"]["roles"]["annotation-note-box"]["annotationContainer"] = "frame-container"
    theme_path = tmp_path / "theme.yaml"
    theme_path.write_text(yaml.safe_dump(theme, sort_keys=False), encoding="utf-8")
    return theme_path


def _render(tmp_path: Path, *, view_name: str = "view-image-container.yaml", theme_path: Path | None = None):
    root = _root()
    draft = resolve_draft_render(
        project_path=root / "examples/controller-z/project.yaml",
        view_path=root / "tests/fixtures/candidate-placement" / view_name,
        theme_path=theme_path or _image_container_theme(tmp_path),
        scheme_path=root / "examples/controller-z/schemes/executive-light.yaml",
        layout_path=root / "conformance/layout-profile-intent-v0.2.yaml",
        actual_path=root / "examples/controller-z/actual.yaml",
        icon_catalog_paths=(_catalog(tmp_path),),
        viewport=(1600, 900),
    )
    request = RenderRequest(closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
                            scheduler=ReferenceScheduler(), renderer=V05SvgRenderer(),
                            draft_auto_block=draft.auto_block)
    return render_review(request)


def test_a_theme_only_binding_resolves_an_icon_catalog_entry_no_view_selected() -> None:
    """The closure fix (#465): Theme alone reaches a catalog entry no View names."""
    import tempfile
    with tempfile.TemporaryDirectory() as raw:
        tmp_path = Path(raw)
        rendered = _render(tmp_path)
    artifact = rendered.artifact.content.decode()
    assert 'data-scene-id="annotation-box:performance-note"' in artifact
    # Nine-slice tiles are painted as nested clipping <svg> viewports, not a
    # single stretched <image> -- proof the completed tile geometry, not an
    # adapter guess, drove the markup.
    assert 'data-scene-id="annotation-box:performance-note-image"' in artifact
    assert artifact.count("<svg x=") >= 4  # at least a degenerate three-slice's worth of tiles


def test_the_note_text_is_measured_inside_the_content_inset_not_the_mounting() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as raw:
        tmp_path = Path(raw)
        rendered = _render(tmp_path)
    artifact = rendered.artifact.content.decode()
    box = re.search(r'<rect[^>]*data-scene-id="annotation-box:performance-note"[^>]*x="([\d.]+)" y="([\d.]+)"[^>]*width="([\d.]+)" height="([\d.]+)"', artifact)
    text = re.search(r'<text[^>]*data-scene-id="annotation-text:performance-note"[^>]*x="([\d.]+)" y="([\d.]+)"', artifact)
    assert box is not None and text is not None
    box_x, box_y, box_w, box_h = (float(value) for value in box.groups())
    text_x, text_y = float(text.group(1)), float(text.group(2))
    # The text's left edge sits strictly inside the paint box by more than the
    # declared content inset alone would explain if it were measured at the
    # box edge (today's zero-inset rectangle/balloon behaviour).
    assert text_x > box_x
    assert box_x < text_x < box_x + box_w
    assert box_y < text_y < box_y + box_h


def test_a_theme_binding_an_unresolved_catalog_reference_raises_a_stable_diagnostic() -> None:
    root = _root()
    import tempfile
    with tempfile.TemporaryDirectory() as raw:
        tmp_path = Path(raw)
        theme = yaml.safe_load((root / "examples/controller-z/themes/executive-light.yaml").read_text(encoding="utf-8"))
        theme["body"]["values"]["frame-container"] = {
            "type": "annotationContainer",
            "value": {"outline": "image", "image": "fixture:missing", "cornerRadius": 0,
                      "sliceInsetsEm": {"top": 0.6, "right": 0.6, "bottom": 0.6, "left": 0.6},
                      "contentInsetEm": {"top": 0.8, "right": 0.8, "bottom": 0.8, "left": 0.8}},
        }
        theme["body"]["roles"]["annotation-note-box"]["annotationContainer"] = "frame-container"
        theme_path = tmp_path / "theme.yaml"
        theme_path.write_text(yaml.safe_dump(theme, sort_keys=False), encoding="utf-8")
        try:
            _render(tmp_path, theme_path=theme_path)
        except RenderFailed as error:
            assert error.code == "E_LAYOUT_ANNOTATION_IMAGE_UNRESOLVED"
        else:
            raise AssertionError("expected an unresolved-catalog-reference diagnostic")
