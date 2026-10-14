"""The actual PDF contains the selected installed face's glyphs, not a fallback."""
from hashlib import sha256
from importlib.metadata import version
from io import BytesIO

from fontTools.ttLib import TTFont
from pypdf import PdfReader
import pytest
import yaml

from chrona.presentation.fonts.installed import InstalledFontIndex, use_installed_fonts
from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.model.font_metrics import FontFile
from chrona.presentation.renderers.pdf_fonts import pdf_font_bytes
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderRequest, render_review
from tests.support import synthetic_review as sr
from tests.support.cff_fonts import write_cff_collection, write_cff_font


@pytest.mark.parametrize("kind", ["cff", "cff2", "variable", "collection"])
@pytest.mark.parametrize("header_text", ["A", "H", "AH"])
def test_installed_cff_role_embeds_exact_selected_glyph_in_pdf(tmp_path, kind, header_text):
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    if kind == "collection":
        path = write_cff_collection(fonts / "proof.ttc")
        index = 1
    else:
        path = write_cff_font(fonts / "proof.otf", family="CFF Proof",
                              outline="cff" if kind == "cff" else "cff2", variable=kind == "variable")
        index = 0
    source_bytes = path.read_bytes()
    source_identity = "sha256:" + sha256(source_bytes).hexdigest()
    parts = sr.bundle()
    theme = parts["theme"]["body"]
    theme["values"]["cff.family"] = {"type": "fontFamily", "value": "CFF Proof"}
    theme["roles"]["groupHeader"]["fontFamily"] = "cff.family"
    source = sr.bunched_project(groups=1, per_group=1)
    source["entities"]["team-0"]["title"] = header_text
    documents = {**parts, "project": source}
    paths = {}
    for name, document in documents.items():
        paths[name] = tmp_path / f"{name}.yaml"
        paths[name].write_text(yaml.safe_dump(document, sort_keys=False))
    with use_installed_fonts(InstalledFontIndex([fonts])):
        draft = resolve_draft_render(project_path=paths["project"], view_path=paths["view"],
                                     theme_path=paths["theme"], scheme_path=paths["scheme"],
                                     layout_path=paths["layout"], target_kind="pdf", viewport=(1600, 900))
        rendered = render_review(RenderRequest(draft.closure, draft.asset_root, ReferenceScheduler(),
                                               asset_root=draft.asset_root, draft_auto_block=draft.auto_block,
                                               draft_font_resolution=draft.font_resolution))
    header = next(item for item in rendered.surface.primitives if item.scene_id == "group-header:team-0")
    assert header.text_layout.family == "CFF Proof"
    assert "cff-cu2qu-v1" in rendered.artifact.adapter_identity
    assert f"pdf-closed-face-v1-fonttools-{version('fonttools')}" in rendered.artifact.adapter_identity
    assert source_identity.removeprefix("sha256:") in rendered.artifact.adapter_identity
    reader = PdfReader(BytesIO(rendered.artifact.content))
    assert header_text in reader.pages[0].extract_text()
    resources = reader.pages[0]["/Resources"]["/Font"]
    selected = []
    for reference in resources.values():
        face = reference.get_object()
        descriptor = face.get("/FontDescriptor")
        if descriptor is None or "/FontFile2" not in descriptor:
            continue
        embedded = TTFont(BytesIO(descriptor["/FontFile2"].get_data()))
        if embedded["name"].getDebugName(1) == "CFF Proof":
            selected.append(embedded)
    assert selected, "PDF must embed the resolved CFF face, not a packaged substitute"
    expected_bytes = pdf_font_bytes(FontFile(path, source_identity, "CFF Proof", 400, index),
                                   frozenset(map(ord, header_text)))
    expected = TTFont(BytesIO(expected_bytes))
    for embedded in selected:
        for codepoint in map(ord, header_text):
            glyph_name = next(table.cmap[codepoint] for table in embedded["cmap"].tables if codepoint in table.cmap)
            expected_name = expected.getBestCmap()[codepoint]
            assert embedded["hmtx"].metrics[glyph_name][0] == expected["hmtx"].metrics[expected_name][0]
            glyph = embedded["glyf"][glyph_name]
            assert glyph.numberOfContours > 0
            assert list(glyph.coordinates) == list(expected["glyf"][expected_name].coordinates)
    assert path.read_bytes() == source_bytes
