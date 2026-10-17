"""Real-adapter regression for completed mixed-script face runs (#1612)."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import sys
from xml.etree import ElementTree as ET

import pytest
from PIL import Image, ImageChops
import yaml

from chrona.presentation.fonts.installed import InstalledFontIndex, use_installed_fonts
from chrona.presentation.model import font_resources
from chrona.presentation.model.font_resources import FontProviderUnavailable
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from chrona.usecases.table_import import import_table
from tests.support import synthetic_review as sr
from tests.support.text_treatments import cjk_available
from tests.integration.test_installed_fonts import renamed

_SVG = "http://www.w3.org/2000/svg"
_ROOT = Path(__file__).resolve().parents[2]
_CJK = _ROOT / "packages/chrona-fonts-noto-cjk/src/chrona_fonts_noto_cjk/fonts"
_PACKAGED = _ROOT / "src/chrona/resources/fonts"
_HIRAGINO = (Path("/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc"),
             Path("/System/Library/Fonts/ヒラギノ角ゴシック W7.ttc"))


def _resource(path: Path, value: object) -> Path:
    return sr._write(path, value)


def _crop(image: Image.Image, primitive: object) -> Image.Image:
    layout = primitive.text_layout
    latin = next(run for line in layout.runs for run in line if run.text.startswith("UX"))
    x, y = primitive.baseline
    return image.crop((max(0, int(x) - 1), max(0, int(y - latin.font_size) - 2),
                       min(image.width, int(x + latin.inline_size) + 2), min(image.height, int(y) + 3)))


def _font_weight(font: object) -> int | None:
    from fontTools.ttLib import TTFont

    font = font.get_object()
    candidates = [font]
    candidates.extend(item.get_object() for item in font.get("/DescendantFonts", ()))
    for candidate in candidates:
        descriptor = candidate.get("/FontDescriptor")
        if descriptor is None:
            continue
        descriptor = descriptor.get_object()
        stream = descriptor.get("/FontFile2") or descriptor.get("/FontFile3")
        if stream is not None:
            return int(TTFont(BytesIO(stream.get_data()))["OS/2"].usWeightClass)
    return None


@pytest.mark.parametrize("native_cjk", [False, True], ids=["portable-provider-absent", "native-hiragino"])
def test_imported_task_table_and_member_label_keep_completed_mixed_face_weights(tmp_path, monkeypatch, native_cjk):
    """PNG pixels match exact face-weight references; PDF UX uses embedded 400/700 faces."""
    table = ("id,title,type,start,end,owner\n"
             "ux,UXリサーチ,task,2026-10-05,2026-10-10,UXリサーチ\n")
    imported = import_table(table, project_id="mixed-face", title="Mixed face", as_of="2026-10-12",
                            roles=("responsible=owner",))
    assert imported.ok, imported.diagnostics
    project = _resource(tmp_path / "project.yaml", yaml.safe_load(imported.project_yaml))

    parts = sr.bundle("executive-light")
    parts["theme"]["body"]["values"]["member-weight-700"] = {"type": "fontWeight", "value": 700}
    parts["theme"]["body"]["roles"]["groupHeader"]["fontWeight"] = "member-weight-700"
    parts["view"]["body"]["visibility"]["labels"]["textRole"] = "groupHeader"
    paths = {kind: _resource(tmp_path / f"{kind}.yaml", value) for kind, value in parts.items()}
    actual = _resource(tmp_path / "actual.yaml", yaml.safe_load(imported.actual_yaml)) if imported.actual_yaml else None
    request = dict(project=project, actual=actual, **paths)
    fonts = tmp_path / "installed"
    fonts.mkdir()
    if native_cjk:
        if sys.platform != "darwin" or not all(path.is_file() for path in _HIRAGINO):
            pytest.skip("requires the native macOS Hiragino Sans W4/W7 faces")
        native_fonts = []
        for source in _HIRAGINO:
            target = fonts / source.name
            target.symlink_to(source)
            native_fonts.append(target)
    else:
        if not cjk_available():
            pytest.skip("requires optional Noto CJK package for the portable renamed-face fixture")
        renamed(fonts / "hiragino-regular.ttf", _CJK / "noto-sans-jp-regular-v1.ttf", "Hiragino Sans", 400)
        renamed(fonts / "hiragino-bold.ttf", _CJK / "noto-sans-jp-bold-v1.ttf", "Hiragino Sans", 700)
        native_fonts = [fonts / "hiragino-regular.ttf", fonts / "hiragino-bold.ttf"]
    package_root = font_resources._package_root

    def without_optional_cjk(identity):
        if identity == "chrona-fonts-noto-cjk":
            raise FontProviderUnavailable(identity)
        return package_root(identity)

    monkeypatch.setattr(font_resources, "_package_root", without_optional_cjk)
    with use_installed_fonts(InstalledFontIndex([fonts])):
        png_result = render_draft(DraftRenderRequest(target_kind="png", **request))
        pdf_result = render_draft(DraftRenderRequest(target_kind="pdf", **request))

    surface = png_result.rendered.surface
    mixed = [item for item in surface.primitives if item.kind == "Text" and item.text_layout is not None
             and item.text == "UXリサーチ"]
    cell = next(item for item in mixed if item.purpose == "table-cell")
    member = next(item for item in mixed if item.purpose == "member-label")
    cell_runs = [run for line in cell.text_layout.runs for run in line]
    member_runs = [run for line in member.text_layout.runs for run in line]
    assert [(run.family, run.weight) for run in cell_runs][0] == ("Noto Sans", 400)
    assert [(run.family, run.weight) for run in member_runs][0] == ("Noto Sans", 700)
    assert cell_runs[1].weight == 400 and "Hiragino Sans" in cell_runs[1].family
    assert member_runs[1].weight == 700 and "Hiragino Sans" in member_runs[1].family

    # Compare each actual Latin glyph crop with two otherwise identical
    # Latin-only references. This holds the node's own position and size fixed,
    # so the alternate-weight mismatch can only come from face weight.
    svg = V05SvgRenderer(viewer_fit=False).render(surface).content
    import resvg_py
    font_files = [str(path) for path in (_PACKAGED / "noto-sans-regular-v1.ttf",
                                         _PACKAGED / "noto-sans-bold-v1.ttf", *native_fonts)]
    actual_image = Image.open(BytesIO(png_result.artifact.content)).convert("RGB")
    for primitive, intended_weight in ((cell, 400), (member, 700)):
        actual_crop = _crop(actual_image, primitive)
        references = {}
        for weight in (400, 700):
            root = ET.fromstring(svg)
            node = next(item for item in root.iter(f"{{{_SVG}}}text")
                        if item.get("data-scene-id") == primitive.scene_id)
            for child in tuple(node):
                node.remove(child)
            node.text = "UX"
            node.set("font-family", "Noto Sans")
            node.set("font-weight", str(weight))
            node.set("font-size", str(primitive.text_layout.runs[0][0].font_size))
            reference = Image.open(BytesIO(resvg_py.svg_to_bytes(
                svg_string=ET.tostring(root, encoding="unicode"), dpi=96,
                font_files=font_files, skip_system_fonts=True,
            ))).convert("RGB")
            references[weight] = _crop(reference, primitive)
        assert ImageChops.difference(references[400], references[700]).getbbox() is not None
        assert ImageChops.difference(actual_crop, references[intended_weight]).getbbox() is None
        assert ImageChops.difference(actual_crop, references[1100 - intended_weight]).getbbox() is not None

    # Tie extracted UX text to the actual embedded PDF font resources rather
    # than merely asserting that both font programs occur somewhere in the file.
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(pdf_result.artifact.content))
    observed: list[tuple[str, int]] = []

    def visit(text, _cm, _tm, font_dict, _size):
        if "UX" in text:
            weight = _font_weight(font_dict)
            if weight is not None:
                observed.append((text, weight))

    reader.pages[0].extract_text(visitor_text=visit)
    weights = {weight for text, weight in observed if "UX" in text}
    assert {400, 700} <= weights, observed
