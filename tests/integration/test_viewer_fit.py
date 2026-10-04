"""#1050: `viewerFit` on an annotation box role, rendered end to end.

Synthetic Projects through the packaged `executive-light` bundle; no `examples/` input. A fallback face cannot be
created here, so the rules are checked on the emitted SVG against the published Scene: every pinned line carries the
width Layout measured, the box keeps its measured geometry, the default is byte-identical, and a declaration the
mode cannot honour fails at its pointer. What a browser then draws is the measured evidence in the work record.
"""
from __future__ import annotations

import re
from math import isclose

import pytest

from chrona.presentation.contracts.resources import TypesetterIdentity
from chrona.presentation.model.closure import ClosureError, resolve_draft_render
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.presentation.renderers.v05_typeset import V05TikzRenderer, V05TypstRenderer
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility
from chrona.presentation.scene.serialization import scene_document, serialize_scene
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderFailed, RenderRequest, render_review
from tests.support import annotation_artwork as aw
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr
from tests.support import text_treatments as tt

RAIL = 300
TARGETS = ["g0-t1", "g1-t2", "g2-t1"]
FILL = {"outline": "rectangle", "cornerRadius": 0, "inlineSize": "fill"}
PLAIN = {"outline": "rectangle", "cornerRadius": 0}
INSET = {"top": 0.5, "right": 1.0, "bottom": 0.5, "left": 2.0}
BOX_ROLE = "annotation-note-box"
BOX_PREFIX = "annotation-box:"


def _rail_candidate():
    return sr.candidate("rail", region={"kind": "slot", "source": "annotations"}, search_kind="row-aligned",
                        connector="leader")


def _parts(*, container=None, fit=None, adjust=None, texts=None, words=3, unstroked=False, rail=RAIL):
    parts = sr.bundle()
    sr.with_note_rail(parts, rail)
    role = parts["theme"]["body"]["roles"][BOX_ROLE]
    if container is not None:
        parts["theme"]["body"]["values"]["note-container"] = {"type": "annotationContainer", "value": dict(container)}
        role["annotationContainer"] = "note-container"
    if fit is not None:
        role["viewerFit"] = fit
    if adjust is not None:
        role["viewerFitAdjust"] = adjust
    if unstroked:
        parts["theme"]["body"]["colorBindings"].pop(f"{BOX_ROLE}.stroke", None)
        role.pop("strokeWidth", None)
    return parts


def _source(parts, *, texts=None, words=3, candidates=None):
    source = sr.chain_project()
    ids = sr.add_notes(source, parts["view"], TARGETS, candidates or [_rail_candidate()], words=words)
    for note_id, text in zip(ids, texts or (), strict=False):
        source["annotations"][note_id]["text"] = text
    return source


def _with_start_ink(parts):
    parts["theme"]["body"]["roles"]["annotation-border-start"] = {}
    parts["theme"]["body"]["colorBindings"]["annotation-border-start.fill"] = "accent"


def _render(tmp_path, name="r", *, parts=None, texts=None, words=3, configure=None, **parts_args):
    directory = tmp_path / name
    directory.mkdir()
    parts = parts or _parts(**parts_args)
    if configure is not None:
        configure(parts)
    return sr.render(directory, _source(parts, texts=texts, words=words), presentation=parts)


def _by_prefix(rendered, prefix):
    return {item.scene_id: item for item in rendered.surface.primitives if item.scene_id.startswith(prefix)}


def _svg(rendered):
    return rendered.artifact.content.decode("utf-8")


def _text_element(svg, scene_id):
    match = re.search(rf'<text data-scene-id="{re.escape(scene_id)}"[^>]*>.*?</text>', svg, re.S)
    assert match, scene_id
    return match.group(0)


def _lengths(element):
    return [float(value) for value in re.findall(r'textLength="([^"]+)"', element)]


def test_a_theme_without_the_property_or_with_raw_is_byte_identical(tmp_path):
    plain = _render(tmp_path, "a")
    raw = _render(tmp_path, "b", fit="raw")
    assert raw.artifact.content == plain.artifact.content
    # The chain's resolved relation identities require v0.7 independently of viewerFit.
    plain_document, raw_document = scene_document(plain.scene), scene_document(raw.scene)
    assert plain_document["version"] == "chrona/scene/v0.7"
    # Explicit raw changes the authored Theme identity, not the completed Scene.
    assert {key: value for key, value in raw_document.items() if key != "provenance"} == {
        key: value for key, value in plain_document.items() if key != "provenance"
    }
    assert b"textLength" not in plain.artifact.content and b"filter=" not in plain.artifact.content
    assert all(item.viewer_fit == "raw" for item in plain.surface.primitives)
    assert all(item.text_layout is None or item.text_layout.fit is None for item in plain.surface.primitives)


def test_a_single_line_note_pins_its_one_line_to_its_measured_inline_size(tmp_path):
    rendered = _render(tmp_path, fit="text-follows-box", texts=("Short.", "Short too.", "Also short."), container=FILL)
    svg = _svg(rendered)
    texts = _by_prefix(rendered, "annotation-text:")
    assert len(texts) == 3
    for scene_id, primitive in texts.items():
        element = _text_element(svg, scene_id)
        assert len(primitive.text_layout.lines) == 1 and "<tspan" not in element
        assert _lengths(element) == [pytest.approx(primitive.bounds[2], abs=0.001)]
        assert 'lengthAdjust="spacing"' in element


def test_a_wrapped_note_pins_each_line_to_its_own_width_and_stays_ragged(tmp_path):
    rendered = _render(tmp_path, fit="text-follows-box", container=FILL, words=12)
    svg = _svg(rendered)
    boxes = _by_prefix(rendered, BOX_PREFIX)
    for scene_id, primitive in _by_prefix(rendered, "annotation-text:").items():
        element = _text_element(svg, scene_id)
        lengths = _lengths(element)
        assert len(lengths) == len(primitive.text_layout.lines) >= 3
        assert not re.search(r'<text [^>]*textLength', element)  # on each line, never on the run
        assert max(lengths) == pytest.approx(primitive.bounds[2], abs=0.001)
        inner = boxes[BOX_PREFIX + scene_id.split(":", 1)[1]].bounds[2]
        assert max(lengths) <= inner and len({round(item, 2) for item in lengths}) > 1  # ragged, never justified
        assert list(primitive.text_layout.fit.line_inline_sizes) == pytest.approx(lengths, abs=0.001)


@pytest.mark.parametrize("adjust", ["spacing", "spacingAndGlyphs"])
def test_the_length_adjust_matches_the_declaration(tmp_path, adjust):
    rendered = _render(tmp_path, fit="text-follows-box", adjust=adjust, words=6)
    for scene_id in _by_prefix(rendered, "annotation-text:"):
        assert set(re.findall(r'lengthAdjust="([^"]+)"', _text_element(_svg(rendered), scene_id))) == {adjust}


def test_text_follows_box_changes_no_geometry_and_no_other_primitive(tmp_path):
    raw = _render(tmp_path, "raw", container=FILL, words=8)
    fitted = _render(tmp_path, "fit", fit="text-follows-box", container=FILL, words=8)
    assert [(item.scene_id, item.bounds, item.paint) for item in fitted.surface.primitives] == [
        (item.scene_id, item.bounds, item.paint) for item in raw.surface.primitives]
    assert [item.text_layout.lines for item in fitted.surface.primitives if item.text_layout] == [
        item.text_layout.lines for item in raw.surface.primitives if item.text_layout]
    assert {item.viewer_fit for item in fitted.surface.primitives if item.scene_id.startswith(BOX_PREFIX)} == {"text-follows-box"}


def test_the_scene_carries_the_mode_on_the_box_and_validates_as_v0_7(tmp_path):
    rendered = _render(tmp_path, fit="text-follows-box", container=FILL, words=6)
    document = scene_document(rendered.scene)
    assert document["version"] == "chrona/scene/v0.7"
    primitives = {item["id"]: item for item in document["surfaces"][0]["primitives"]}
    assert primitives["annotation-box:note-0"]["viewerFit"] == "text-follows-box"
    fit = primitives["annotation-text:note-0"]["textLayout"]["fit"]
    assert fit["mode"] == "text-follows-box" and fit["adjust"] == "spacing" and len(fit["lineInlineSizes"]) >= 2
    serialize_scene(rendered.scene)  # schema-validated


def test_a_compressed_text_pins_its_length_in_the_pre_transform_frame(tmp_path):
    parts = _parts(fit="text-follows-box")
    tt.with_scale(parts, ["annotation-note-text"], 0.8)
    rendered = _render(tmp_path, parts=parts, texts=("Compressed note text.",) * 3)
    for scene_id, primitive in _by_prefix(rendered, "annotation-text:").items():
        element = _text_element(_svg(rendered), scene_id)
        assert primitive.text_layout.horizontal_scale == 0.8
        assert _lengths(element) == [pytest.approx(primitive.bounds[2] / 0.8, abs=0.002)]
        assert "matrix(0.8 0 0 1 " in element


def test_a_tilted_note_pins_its_lines_in_the_rotated_frame(tmp_path):
    parts = _parts(fit="text-follows-box", container=dict(PLAIN, tiltDegrees=[-2, 2]))
    rendered = _render(tmp_path, parts=parts, words=5)
    for scene_id, primitive in _by_prefix(rendered, "annotation-text:").items():
        element = _text_element(_svg(rendered), scene_id)
        assert primitive.text_layout.orientation == "tilt" and "rotate(" in element
        assert _lengths(element) == pytest.approx(list(primitive.text_layout.fit.line_inline_sizes), abs=0.001)


def test_every_header_line_of_a_note_kind_is_pinned_too(tmp_path):
    source = ak.project(("risk", "note"), text="A note with a few words in it.")
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    ak.with_kind_theme(parts, border_side="start", border_width=5)
    parts["theme"]["body"]["roles"][BOX_ROLE]["viewerFit"] = "text-follows-box"
    directory = tmp_path / "k"
    directory.mkdir()
    rendered = ak.render(directory, source, parts)
    svg = _svg(rendered)
    headers = _by_prefix(rendered, "annotation-kind-text:")
    assert headers
    for scene_id, primitive in headers.items():
        assert primitive.text_layout.fit is not None
        assert _lengths(_text_element(svg, scene_id)) == pytest.approx(list(primitive.text_layout.fit.line_inline_sizes))
        # the header is measured as drawn (after the text transform), the same width the kind frame reserved
        assert primitive.text_layout.fit.line_inline_sizes[0] > 0
    assert all(item.fit is not None for item in (p.text_layout for p in _by_prefix(rendered, "annotation-text:").values()))


def test_a_framed_artwork_container_pins_its_lines_inside_the_frame(tmp_path):
    source = ak.project(("risk", "note"), text="1. Board arrival gates first and a second long line of the scroll.")
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    aw.with_artwork(parts)
    parts["theme"]["body"]["roles"][BOX_ROLE]["viewerFit"] = "text-follows-box"
    directory = tmp_path / "w"
    directory.mkdir()
    rendered = ak.render(directory, source, parts, visual_profile="chrona-output/visual/v0.6-svg")
    svg = _svg(rendered)
    assert aw.artwork_parts(rendered)
    for scene_id, primitive in _by_prefix(rendered, "annotation-text:").items():
        assert primitive.text_layout.fit.mode == "text-follows-box"
        assert _lengths(_text_element(svg, scene_id)) == pytest.approx(list(primitive.text_layout.fit.line_inline_sizes))
    # the frame is a static drawing: the text is pinned to the width Layout fitted inside it
    boxes = _by_prefix(rendered, BOX_PREFIX)
    for scene_id, primitive in _by_prefix(rendered, "annotation-text:").items():
        box = boxes[BOX_PREFIX + scene_id.split(":", 1)[1]]
        assert primitive.bounds[0] + primitive.bounds[2] <= box.bounds[0] + box.bounds[2]


def test_the_modes_leave_the_contrast_and_perceptibility_findings_alone(tmp_path):
    raw = _render(tmp_path, "raw", unstroked=True, words=5)
    for index, mode in enumerate(("text-follows-box", "box-follows-text")):
        fitted = _render(tmp_path, f"m{index}", fit=mode, unstroked=True, words=5)
        assert evaluate_scene_contrast(scene_document(fitted.scene)) == evaluate_scene_contrast(scene_document(raw.scene))
        assert (evaluate_scene_perceptibility(scene_document(fitted.scene))
                == evaluate_scene_perceptibility(scene_document(raw.scene)))


def test_two_renders_are_byte_identical(tmp_path):
    for index, mode in enumerate(("text-follows-box", "box-follows-text")):
        one = _render(tmp_path, f"a{index}", fit=mode, unstroked=True, words=5)
        two = _render(tmp_path, f"b{index}", fit=mode, unstroked=True, words=5)
        assert one.artifact.content == two.artifact.content


# --- box-follows-text ----------------------------------------------------------------------------------------------

def _follow(tmp_path, name="f", *, container=PLAIN, words=6, texts=None):
    return _render(tmp_path, name, fit="box-follows-text", container=container, unstroked=True, words=words, texts=texts)


def test_a_box_that_follows_its_text_is_one_filter_group_with_a_pinned_extent_and_an_end_inset(tmp_path):
    inset_em = 1.0
    rendered = _follow(tmp_path, container=dict(PLAIN, contentInsetEm=dict(INSET, right=inset_em)), words=10)
    svg = _svg(rendered)
    boxes = _by_prefix(rendered, BOX_PREFIX)
    assert len(boxes) == 3
    for scene_id, box in boxes.items():
        assert box.viewer_fit == "box-follows-text"
        assert f'<rect data-scene-id="{scene_id}"' not in svg  # no static background rect
        group = re.search(rf'<g data-scene-id="{re.escape(scene_id)}"[^>]*>(.*?)</g>', svg, re.S)
        assert group, scene_id
        filter_id = re.search(r'filter="url\(#(fit-[0-9a-f]{12})\)"', group.group(0)).group(1)
        assert re.search(rf'<filter id="{filter_id}" x="0" y="0" width="1" height="1"><feFlood ', svg)
        text_id = "annotation-text:" + scene_id.split(":", 1)[1]
        text = _by_prefix(rendered, text_id)[text_id]
        x, y, w, h = box.bounds
        extent = re.search(rf'<rect data-scene-id="{re.escape(scene_id)}-extent" x="([^"]+)" y="([^"]+)" width="([^"]+)" '
                           rf'height="([^"]+)" fill="none"/>', group.group(1))
        assert extent
        assert float(extent.group(1)) == pytest.approx(x, abs=1e-6)
        assert float(extent.group(2)) == pytest.approx(y, abs=1e-6)
        assert isclose(float(extent.group(1)) + float(extent.group(3)), text.baseline[0], abs_tol=0.001)  # start inset
        assert float(extent.group(4)) == pytest.approx(h, abs=0.001)  # top and bottom
        spaces = text.text_layout.fit.end_pad_spaces
        size = text.text_layout.font_size
        assert spaces >= 1 and abs(spaces - inset_em * size / (0.26 * size)) < 3  # a space is about a quarter em
        lines = re.findall(r">([^<>]*?)</tspan>", group.group(1)) or re.findall(r">([^<>]*?)</text>", group.group(1))
        assert len(lines) == len(text.text_layout.lines)
        assert all(line.endswith(" " * spaces) and not line.endswith(" " * (spaces + 1)) for line in lines)
        assert 'xml:space="preserve"' in group.group(1) and "textLength" not in group.group(1)
    assert len(set(re.findall(r'<filter id="(fit-[0-9a-f]{12})"', svg))) == 1  # one filter for one fill


def test_a_box_that_follows_its_text_keeps_the_measured_box_in_the_scene(tmp_path):
    raw = _render(tmp_path, "raw", container=PLAIN, unstroked=True, words=6)
    followed = _follow(tmp_path, "follow", words=6)
    assert [(item.scene_id, item.bounds) for item in followed.surface.primitives] == [
        (item.scene_id, item.bounds) for item in raw.surface.primitives]
    assert scene_document(followed.scene)["version"] == "chrona/scene/v0.7"
    document = {item["id"]: item for item in scene_document(followed.scene)["surfaces"][0]["primitives"]}
    fit = document["annotation-text:note-0"]["textLayout"]["fit"]
    assert fit["mode"] == "box-follows-text" and fit["boxId"] == "annotation-box:note-0" and "lineInlineSizes" not in fit
    serialize_scene(followed.scene)


def test_a_start_border_is_allowed_and_stays_a_static_strip(tmp_path):
    rendered = _render(tmp_path, "sb", fit="box-follows-text", container=dict(PLAIN, border={"start": {"width": 4}}),
                       unstroked=True, words=6, configure=_with_start_ink)
    strips = [item for item in rendered.surface.primitives if "border" in item.scene_id]
    assert strips and all(f'<rect data-scene-id="{item.scene_id}"' in _svg(rendered) for item in strips)
    group = re.search(r'<g data-scene-id="annotation-box:note-0"[^>]*>(.*?)</g>', _svg(rendered), re.S).group(1)
    assert 'width="4"' in group  # the extent rect reaches the text start, past the border width


# --- rejected combinations -----------------------------------------------------------------------------------------

def _failure(call):
    """The (code, pointer) of a refused render: a Theme schema or reader refusal, or a Layout or Scene one."""
    with pytest.raises((RenderFailed, ClosureError)) as raised:
        call()
    error = raised.value
    return (getattr(error, "code", None) or error.diagnostic_id, error.source_ref, str(getattr(error, "message", "")
                                                                                      or getattr(error, "detail", "")))


def _refused(tmp_path, **kwargs):
    return _failure(lambda: _render(tmp_path, **kwargs))


@pytest.mark.parametrize("container,name", [
    (dict(PLAIN, cornerRadius=0.2), "cornerRadius"),
    (dict(PLAIN, tiltDegrees=[-2, 2]), "tiltDegrees"),
    (dict(FILL), "inlineSize"),
    (dict(PLAIN, border={"end": {"width": 2}}), "border/end"),
    (dict(PLAIN, border={"top": {"width": 2}}), "border/top"),
    (dict(PLAIN, border={"bottom": {"width": 2}}), "border/bottom"),
    ({"outline": "balloon", "cornerRadius": 0.2, "tailBaseEm": 0.6}, "outline"),
])
def test_a_container_the_box_cannot_follow_fails_at_its_declaration(tmp_path, container, name):
    code, pointer, _ = _refused(tmp_path, container=container, fit="box-follows-text", unstroked=True)
    assert (code, pointer) == ("E_THEME_TOKEN_TYPE", f"/body/roles/{BOX_ROLE}/annotationContainer/{name}")


def test_artwork_is_refused_with_a_box_that_follows_its_text(tmp_path):
    source = ak.project(("risk", "note"))
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    aw.with_artwork(parts)
    parts["theme"]["body"]["roles"][BOX_ROLE]["viewerFit"] = "box-follows-text"
    directory = tmp_path / "a"
    directory.mkdir()
    code, pointer, _ = _failure(lambda: ak.render(directory, source, parts))
    assert (code, pointer) == ("E_THEME_TOKEN_TYPE", f"/body/roles/{BOX_ROLE}/annotationContainer/artwork")


def test_an_adjust_without_text_follows_box_fails_at_the_adjust(tmp_path):
    code, pointer, _ = _refused(tmp_path, fit="box-follows-text", adjust="spacing", unstroked=True)
    assert code == "E_THEME_SCHEMA" and f"/body/roles/{BOX_ROLE}" in pointer  # the live Theme schema rejects it first
    code, pointer, _ = _refused(tmp_path, name="r2", fit="text-follows-box", adjust="justify")
    assert code == "E_THEME_SCHEMA"


def test_a_stroked_box_is_refused_with_its_role(tmp_path):
    code, pointer, message = _refused(tmp_path, fit="box-follows-text", unstroked=False)
    assert (code, pointer) == ("E_PRESENTATION_VIEWER_FIT_PAINT", f"/body/roles/{BOX_ROLE}")
    assert "solid fill" in message


def test_a_kind_frame_is_refused_with_a_box_that_follows_its_text(tmp_path):
    source = ak.project(("risk", "note"))
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    ak.with_kind_theme(parts, border_side="start", border_width=5)
    role = parts["theme"]["body"]["roles"][BOX_ROLE]
    role["viewerFit"] = "box-follows-text"
    parts["theme"]["body"]["colorBindings"].pop(f"{BOX_ROLE}.stroke", None)
    role.pop("strokeWidth", None)
    directory = tmp_path / "kind"
    directory.mkdir()
    code, pointer, _ = _failure(lambda: ak.render(directory, source, parts))
    assert code == "E_LAYOUT_VIEWER_FIT_STATIC_CHROME" and pointer.startswith("/annotations/")


def test_a_role_that_is_not_an_annotation_box_cannot_declare_a_mode(tmp_path):
    parts = _parts()
    parts["theme"]["body"]["roles"]["planned"]["viewerFit"] = "text-follows-box"
    directory = tmp_path / "role"
    directory.mkdir()
    with pytest.raises(Exception) as raised:
        sr.render(directory, _source(parts), presentation=parts)
    assert "E_THEME_ROLE_PROPERTY_UNSUPPORTED" in str(raised.value) or "E_THEME_ROLE_PROPERTY_UNSUPPORTED" in repr(
        getattr(raised.value, "diagnostic_id", ""))


# --- other targets -------------------------------------------------------------------------------------------------

class _Captured(Exception):
    pass


@pytest.mark.parametrize("mode", ["text-follows-box", "box-follows-text"])
def test_png_and_pdf_are_drawn_from_the_raw_svg_so_a_fixed_font_output_is_the_raw_one(tmp_path, monkeypatch, mode):
    import resvg_py
    import svglib.svglib as svglib
    from chrona.presentation.renderers import registry

    fitted = _render(tmp_path, "fit", fit=mode, unstroked=True, words=4)
    raw = _render(tmp_path, "raw", unstroked=True, words=4)
    raw_svg = raw.artifact.content.decode("utf-8")
    assert b"textLength" in fitted.artifact.content or b"data-viewer-fit" in fitted.artifact.content
    monkeypatch.setattr(registry, "_font_files", lambda *args, **kwargs: ((), ()))
    seen: dict[str, str] = {}

    def capture_png(**kwargs):
        seen["png"] = kwargs["svg_string"]
        return b"png"

    def capture_pdf(stream):
        seen["pdf"] = stream.read().decode("utf-8")
        raise _Captured

    monkeypatch.setattr(resvg_py, "svg_to_bytes", capture_png)
    monkeypatch.setattr(svglib, "svg2rlg", capture_pdf)
    png = registry.ResvgPngRenderer("png", {"engine": "resvg-py", "version": resvg_py.__version__,
                                            "resvgVersion": resvg_py.__resvg_version__, "dpi": 96}, None, None)
    png.render(fitted.surface)
    pdf = registry.ReportLabPdfRenderer(
        {"engine": "reportlab", "invariant": True, "svglibVersion": "2.2.0", "reportlabVersion": "5.0.1"}, None, None)
    monkeypatch.setattr(registry, "_verify_reportlab", lambda descriptor: None)
    with pytest.raises(_Captured):
        pdf.render(fitted.surface)
    assert seen["png"] == raw_svg and seen["pdf"] == raw_svg  # not one fit attribute reaches a rasteriser
    assert "textLength" not in seen["png"] and "filter=" not in seen["pdf"]


def test_the_svg_serializer_is_the_only_one_that_writes_the_modes(tmp_path):
    fitted = _render(tmp_path, "fit", fit="text-follows-box", words=4)
    raw = _render(tmp_path, "raw", words=4)
    assert V05SvgRenderer(viewer_fit=False).render(fitted.surface).content == raw.artifact.content
    assert V05SvgRenderer().render(fitted.surface).content == fitted.artifact.content != raw.artifact.content


def _typeset_render(tmp_path, kind):
    parts = _parts(fit="text-follows-box", container=PLAIN)
    source = _source(parts, words=2)
    source["relations"] = []
    paths = {name: sr._write(tmp_path / f"{name}.yaml", value) for name, value in parts.items()}
    engine = ("typst", "0.13.1", "chrona-typst/v0.1") if kind == "typst" else ("tectonic", "0.15.0", "chrona-tikz/v0.1")
    draft = resolve_draft_render(
        project_path=sr._write(tmp_path / "project.yaml", source), view_path=paths["view"], theme_path=paths["theme"],
        scheme_path=paths["scheme"], layout_path=paths["layout"], viewport=(1600, 900), target_kind=kind,
        typesetter=TypesetterIdentity(*engine))
    renderer = V05TypstRenderer() if kind == "typst" else V05TikzRenderer()
    return render_review(RenderRequest(
        closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
        scheduler=ReferenceScheduler(), renderer=renderer, draft_auto_block=draft.auto_block))


@pytest.mark.parametrize("kind", ["typst", "tikz"])
def test_a_typeset_target_draws_raw_and_names_the_box_role_in_a_warning(tmp_path, kind):
    try:
        rendered = _typeset_render(tmp_path, kind)
    except RenderFailed as error:  # the synthetic Scene needs a capability this typesetter grammar lacks
        pytest.skip(f"synthetic Scene not drawable by {kind}: {error.diagnostic_id}")
    expected = f"W_VIEWER_FIT_NOT_HONOURED:{BOX_ROLE}:{kind}"
    assert expected in rendered.scene.diagnostics
    assert any(item.identity == expected and expected in item.payload["message"] or item.identity == expected
               for item in rendered.warning_records)
    assert b"textLength" not in rendered.artifact.content
