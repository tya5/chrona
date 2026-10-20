"""Actual adapter output for the opt-in deadline caption (#1397 row3)."""
from copy import deepcopy
from xml.etree import ElementTree

import pytest

from chrona.presentation.model.info_diagnostics import DeadlineCaptionsDropped
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document, validate_scene_document
from chrona.usecases.draft_render import warning_payloads
from chrona.usecases.render_review import RenderFailed
from chrona.presentation.renderers.v05_typeset import render_v05_tikz, render_v05_typst
from tests.integration.test_deadline_mark import MIXED, _parts, _render, _source
from tests.support import text_treatments as tt
from tests.support import synthetic_review as sr


def _caption_parts(template="{daysLate} days late", *, text_format=None):
    parts = _parts()
    parts["view"]["body"]["visibility"]["labels"] = {
        "placement": "plot", "content": ["title"], "side": "inside", "overflow": "suppress"}
    parts["view"]["body"]["visibility"]["fallback"]["labels"] = ["inside", "suppress"]
    caption = {"template": template}
    if text_format is not None:
        caption["format"] = text_format
    parts["view"]["body"]["deadlines"]["caption"] = caption
    return parts


def _captions(rendered):
    return [item for item in rendered.surface.primitives if item.purpose == "deadline-caption"]


@pytest.mark.parametrize(("text_format", "expected"), [
    (None, {"a": "8 days late", "g": "10 days late"}),
    ({"form": "english-words"}, {"a": "eight days late", "g": "ten days late"}),
    ({"form": "kanji"}, {"a": "八 days late", "g": "十 days late"}),
    ({"form": "kanji-formal"}, {"a": "捌 days late", "g": "拾 days late"}),
])
def test_actual_svg_has_formatted_core_count_only_for_slipped_deadlines(tmp_path, text_format, expected):
    parts = _caption_parts(text_format=text_format)
    if text_format and text_format["form"].startswith("kanji"):
        if not tt.cjk_available():
            pytest.skip("requires the optional Noto Sans JP package")
        parts["theme"]["body"]["values"]["editorial"]["value"] = "Noto Sans JP, sans-serif"
        rendered = tt.render(tmp_path, _source(**MIXED), parts, cjk=True)
    else:
        rendered = _render(tmp_path, parts=parts)
    captions = _captions(rendered)
    assert {item.source_ref: item.text for item in captions} == expected
    validate_scene_document(scene_document(rendered.scene))
    svg = ElementTree.fromstring(rendered.artifact.content)
    text = ["".join(item.itertext()) for item in svg.iter() if item.tag.endswith("text")]
    assert all(value in text for value in expected.values())
    assert all(item.host_placement_id is None and item.slot_id == "timeline" for item in captions)
    assert not any(isinstance(item, DeadlineCaptionsDropped) for item in rendered.info_diagnostics)
    provenance = {item.primitive_id: item.subjects for item in rendered.surface.primitive_provenance}
    assert all(provenance[item.scene_id][0].source_ref == "/objects/" + item.source_ref for item in captions)


def test_enabled_caption_never_changes_any_existing_primitive(tmp_path):
    parts = _caption_parts()
    bare = deepcopy(parts)
    del bare["view"]["body"]["deadlines"]["caption"]
    before = _render(tmp_path, parts=bare, name="before")
    after = _render(tmp_path, parts=parts, name="after")
    assert before.surface.primitives == tuple(item for item in after.surface.primitives if item.purpose != "deadline-caption")


def test_actual_svg_places_overflow_on_other_side_of_tick(tmp_path):
    source = _source(g="2026-03-10")
    parts = _caption_parts()
    parts["view"]["body"]["window"]["end"] = "2026-03-21"
    rendered = _render(tmp_path, source=source, parts=parts)
    caption, = _captions(rendered)
    tick = next(item for item in rendered.surface.primitives if item.scene_id.startswith("deadline-tick:"))
    assert caption.bounds[0] + caption.bounds[2] < tick.bounds[0]
    assert caption.text == "10 days late" and "10 days late" in rendered.artifact.content.decode()


def test_deadline_boundary_at_window_start_keeps_caption(tmp_path):
    rendered = _render(tmp_path, source=_source(a="2025-12-31"), parts=_caption_parts())
    captions = _captions(rendered)
    # The deadline date is outside the window, but the tick is the exclusive
    # boundary after that date and lands exactly at the window start.
    assert len(captions) == 1 and captions[0].source_ref == "a"
    assert captions[0].text == "44 days late"
    assert not any(isinstance(item, DeadlineCaptionsDropped) for item in rendered.info_diagnostics)


def test_outside_window_deadline_does_not_count_as_dropped_caption(tmp_path):
    rendered = _render(tmp_path, source=_source(a="2025-12-30"), parts=_caption_parts())
    assert not _captions(rendered)
    assert "I_LAYOUT_DEADLINE_OUTSIDE_WINDOW:a" in rendered.scene.diagnostics
    assert not any(isinstance(item, DeadlineCaptionsDropped) for item in rendered.info_diagnostics)


def test_cannot_fit_drops_only_caption_with_positive_count_and_cli_payload(tmp_path):
    parts = _caption_parts("{daysLate} " + "wide " * 13)
    theme = parts["theme"]["body"]
    theme["values"]["caption-size"] = {"type": "number", "value": 80}
    theme["roles"]["deadline-caption"] = {
        key: value for key, value in theme["roles"]["text"].items() if not key.startswith("icon")}
    theme["roles"]["deadline-caption"]["fontSize"] = "caption-size"
    rendered = _render(tmp_path, parts=parts)
    assert not _captions(rendered)
    infos = [item for item in rendered.info_diagnostics if isinstance(item, DeadlineCaptionsDropped)]
    assert len(infos) == 1 and infos[0].count == 2
    provenance = next(item for item in rendered.surface.diagnostic_provenance
                      if item.diagnostic == infos[0].scene_diagnostic())
    assert {item.source_ref for item in provenance.subjects} == {"/objects/a", "/objects/g"}
    payload = next(item for item in warning_payloads(rendered) if item["code"] == "I_LAYOUT_DEADLINE_CAPTION_DROPPED")
    assert payload["severity"] == "info" and payload["count"] == 2
    marks = [item for item in rendered.surface.primitives if item.purpose == "deadline-mark"]
    assert len(marks) == 7  # six actual deadline placements and the explicit legend key
    assert sum(item.purpose == "deadline-mark" and item.scene_id.startswith("deadline-")
               for item in rendered.surface.primitives) == 6


def test_caption_uses_ground_text_gate_not_mark_floor(tmp_path):
    rendered = _render(tmp_path, parts=_caption_parts())
    findings = [item for item in evaluate_scene_contrast(scene_document(rendered.scene))
                if item.primitive_id.startswith("deadline-caption:")]
    assert len(findings) == 2
    assert all(item.floor == 4.5 and item.contrast_ratio >= 4.5 for item in findings)


def test_custom_caption_role_is_measured_and_painted_without_changing_body_text(tmp_path):
    parts = _caption_parts()
    theme = parts["theme"]["body"]
    theme["roles"]["deadline-caption"] = {
        key: value for key, value in theme["roles"]["text"].items() if not key.startswith("icon")}
    theme["values"]["caption-size"] = {"type": "number", "value": 18}
    theme["roles"]["deadline-caption"]["fontSize"] = "caption-size"
    theme["colorBindings"]["deadline-caption.fill"] = "text"
    rendered = _render(tmp_path, parts=parts)
    captions = _captions(rendered)
    assert len(captions) == 2 and all(item.text_layout.font_size == 18 for item in captions)
    assert all(item.visual_role == "deadline-caption" for item in captions)
    assert all("deadline-caption" not in item for item in rendered.surface.diagnostics if item.startswith("W_THEME_ROLE_UNREAD"))
    # Source adapters receive the completed text, not a deadline-specific API.
    assert "8 days late" in render_v05_typst(rendered.surface)
    assert "8 days late" in render_v05_tikz(rendered.surface)


def test_caption_cannot_borrow_the_mark_contrast_floor(tmp_path):
    rendered = _render(tmp_path, parts=_caption_parts())
    document = scene_document(rendered.scene)
    # Gray is above 3:1 but below 4.5:1 on white; mark admission must not admit caption ink.
    for item in document["surfaces"][0]["primitives"]:
        if item["purpose"] == "deadline-caption":
            item["paint"]["fill"] = "#888888"
    findings = [item for item in evaluate_scene_contrast(document)
                if item.primitive_id.startswith("deadline-caption:")]
    assert len(findings) == 2
    assert all(item.floor == 4.5 and 3 < item.contrast_ratio < 4.5 and item.severity == "error" for item in findings)


def test_unavailable_caption_glyphs_use_existing_typed_font_failure(tmp_path, monkeypatch):
    from chrona.presentation.fonts.installed import InstalledFontIndex, use_installed_fonts
    from chrona.presentation.model import font_resources
    from chrona.presentation.model.font_resources import FontProviderUnavailable

    original = font_resources._package_root
    def without_cjk(identity):
        if identity == "chrona-fonts-noto-cjk":
            raise FontProviderUnavailable(identity)
        return original(identity)
    monkeypatch.setattr(font_resources, "_package_root", without_cjk)
    empty = tmp_path / "empty-font-index"
    empty.mkdir()
    (tmp_path / "render").mkdir()
    with pytest.raises(RenderFailed) as raised:
        with use_installed_fonts(InstalledFontIndex([empty])):
            _render(tmp_path / "render", parts=_caption_parts(text_format={"form": "kanji"}))
    assert raised.value.code == "E_FONT_GLYPH_UNAVAILABLE"


def test_caption_uses_available_cjk_fallback_with_informational_substitution(tmp_path):
    from tests.support import text_treatments as tt

    if not tt.cjk_available():
        pytest.skip("requires the optional chrona-fonts-noto-cjk package")
    rendered = _render(tmp_path, parts=_caption_parts(text_format={"form": "kanji"}))
    captions = _captions(rendered)
    assert len(captions) == 2
    assert {item.source_ref: item.text for item in captions} == {
        "a": "八 days late", "g": "十 days late",
    }
    substitutions = [item for item in rendered.info_diagnostics if item.code == "I_FONT_GLYPH_SUBSTITUTED"]
    assert substitutions


def test_actual_pdf_carries_caption_copy_without_deadline_specific_adapter_logic(tmp_path):
    from io import BytesIO
    from pypdf import PdfReader
    from chrona.presentation.model.closure import resolve_draft_render
    from chrona.scheduling.scheduler import ReferenceScheduler
    from chrona.usecases.render_review import RenderRequest, render_review
    from tests.support import synthetic_review as sr

    documents = {**_caption_parts(), "project": _source(**MIXED)}
    paths = {name: sr._write(tmp_path / (name + ".yaml"), value) for name, value in documents.items()}
    draft = resolve_draft_render(project_path=paths["project"], view_path=paths["view"],
        theme_path=paths["theme"], scheme_path=paths["scheme"], layout_path=paths["layout"],
        target_kind="pdf", viewport=(1600, 900))
    rendered = render_review(RenderRequest(draft.closure, draft.asset_root, ReferenceScheduler(),
        asset_root=draft.asset_root, draft_auto_block=draft.auto_block, draft_font_resolution=draft.font_resolution))
    text = PdfReader(BytesIO(rendered.artifact.content)).pages[0].extract_text()
    assert "8 days late" in text and "10 days late" in text
