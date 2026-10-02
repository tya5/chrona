"""#584: Theme resolution of `annotationKinds`, the kind roles and the kind header text contrast gate."""
from __future__ import annotations

import pytest

from chrona.presentation.color_scheme import ColorSchemeError, resolve_theme
from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr


def _resolve(**options):
    parts = sr.bundle()
    ak.with_kind_theme(parts, **options)
    return parts, resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")


def test_a_kind_colour_resolves_through_the_scheme_like_a_colour_binding():
    _, resolved = _resolve()
    kinds = resolved["body"]["annotationKinds"]
    assert kinds["risk"] == {"label": "RISK", "secondary": "WARNING", "title": "{label} · {subject}", "color": "#8E1B12"}
    assert kinds["note"]["color"] == "#1D3F73" and "title" not in kinds["note"]


def test_a_theme_without_kinds_resolves_to_the_same_body_as_before():
    parts = sr.bundle()
    resolved = resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    assert "annotationKinds" not in resolved["body"]


def test_a_closed_scheme_intent_is_a_kind_colour_too():
    parts, _ = _resolve()
    parts["theme"]["body"]["annotationKinds"]["note"]["color"] = "text"
    resolved = resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    assert resolved["body"]["annotationKinds"]["note"]["color"] == parts["scheme"]["body"]["colors"]["text"]


@pytest.mark.parametrize("color", ["category:missing", "nonsense", 4])
def test_an_unknown_kind_colour_is_an_unknown_intent(color):
    parts, _ = _resolve()
    parts["theme"]["body"]["annotationKinds"]["risk"]["color"] = color
    with pytest.raises(ColorSchemeError) as failure:
        resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    assert failure.value.diagnostic_id == "E_SCHEME_INTENT_UNKNOWN"
    assert failure.value.source_ref == "/body/annotationKinds/risk/color"


def test_a_bad_title_template_is_a_theme_error_at_the_kind_pointer():
    parts, _ = _resolve()
    parts["theme"]["body"]["annotationKinds"]["risk"]["title"] = "{subject"
    with pytest.raises(ColorSchemeError) as failure:
        resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    assert failure.value.diagnostic_id == "E_THEME_ANNOTATION_KIND_TEMPLATE"
    assert failure.value.source_ref == "/body/annotationKinds/risk"


def test_the_header_text_is_judged_on_the_kind_bar_not_on_the_canvas_surface():
    # White label ink on the white canvas surface would fail the canvas check; on the dark bars it is legible.
    _resolve(label_fill="surface")


def test_header_text_too_close_to_one_kind_colour_names_the_kind_and_the_role():
    parts = sr.bundle()
    ak.with_kind_theme(parts)
    parts["scheme"]["body"]["categories"]["kind-report"] = "#F4F4F4"  # white on near-white: only the report kind fails
    with pytest.raises(ColorSchemeError) as failure:
        resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    assert failure.value.diagnostic_id == "E_SCHEME_ANNOTATION_KIND_CONTRAST"
    assert failure.value.source_ref == "/body/roles/annotation-kind-label/fill"
    assert failure.value.detail.startswith("annotation-kind-label:note:")


def test_without_a_bar_the_header_text_is_judged_on_the_note_box_fill():
    parts = sr.bundle()
    ak.with_kind_theme(parts, bar=False, label_fill="surface")  # white text on the light note box
    with pytest.raises(ColorSchemeError) as failure:
        resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    assert failure.value.diagnostic_id == "E_SCHEME_ANNOTATION_KIND_CONTRAST"
    assert "annotation-" in failure.value.detail and "-box:" in failure.value.detail


def test_a_declared_header_text_role_needs_its_contrast_treatment():
    parts = sr.bundle()
    ak.with_kind_theme(parts)
    del parts["theme"]["body"]["roles"]["annotation-kind-label"]["contrastTreatment"]
    with pytest.raises(ColorSchemeError) as failure:
        resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    assert failure.value.diagnostic_id == "E_SCHEME_STATE_TEXT_TREATMENT"


def test_the_token_view_returns_the_declaration_of_a_kind_and_nothing_for_another():
    _, resolved = _resolve()
    tokens = ThemeTokenView(resolved)
    risk = tokens.annotation_kind("risk")
    assert risk is not None and risk.color == "#8E1B12" and risk.header.label == "RISK"
    assert tokens.annotation_kind("other") is None and tokens.annotation_kind(None) is None


def test_the_frame_reads_which_elements_the_theme_declares_and_their_geometry():
    _, resolved = _resolve(accent="end", accent_size=5, padding=0.5)
    frame = ThemeTokenView(resolved).annotation_kind_frame()
    assert (frame.label_role, frame.secondary_role, frame.bar_role) == (
        "annotation-kind-label", "annotation-kind-secondary", "annotation-kind-bar")
    assert (frame.accent_role, frame.accent_side, float(frame.accent_size), float(frame.bar_padding_em)) == (
        "annotation-kind-accent", "end", 5.0, 0.5)
    _, plain = _resolve(bar=False, secondary=False, label_fill="text")
    assert ThemeTokenView(plain).annotation_kind_frame().bar_role is None
    assert ThemeTokenView(plain).annotation_kind_frame().secondary_role is None


@pytest.mark.parametrize("edge", [{"side": "diagonal", "size": 4}, {"side": "start", "size": 0}, {"side": "start", "size": -1}])
def test_an_invalid_edge_token_is_a_token_type_error(edge):
    parts = sr.bundle()
    ak.with_kind_theme(parts, accent="start")
    parts["theme"]["body"]["values"]["kind-accent-edge"] = {"type": "edge", "value": edge}
    resolved = resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    with pytest.raises(ThemeTokenError) as failure:
        ThemeTokenView(resolved).annotation_kind_frame()
    assert failure.value.diagnostic_id == "E_THEME_TOKEN_TYPE"


def test_a_kind_stamp_reference_is_carried_into_the_resolved_theme_and_the_token_view():
    _, resolved = _resolve(stamp="end-top")
    assert resolved["body"]["annotationKinds"]["risk"]["stamp"] == ak.STAMPS["risk"]
    tokens = ThemeTokenView(resolved)
    assert tokens.annotation_kind("risk").stamp == ak.STAMPS["risk"]
    frame = tokens.annotation_kind_frame()
    assert (frame.stamp_role, frame.stamp_corner, float(frame.stamp_size)) == ("annotation-kind-stamp", "end-top", 2.0)


def test_a_theme_without_a_stamp_role_has_no_stamp_in_its_frame():
    _, resolved = _resolve()
    frame = ThemeTokenView(resolved).annotation_kind_frame()
    assert frame.stamp_role is None and frame.stamp_corner is None


@pytest.mark.parametrize("placement", [{"corner": "middle", "size": 2}, {"corner": "end-top", "size": 0},
                                       {"corner": "end-top", "size": -1}])
def test_an_invalid_stamp_placement_token_is_a_token_type_error(placement):
    parts = sr.bundle()
    ak.with_kind_theme(parts, stamp="end-top")
    parts["theme"]["body"]["values"]["kind-stamp-placement"]["value"] = placement
    resolved = resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    with pytest.raises(ThemeTokenError) as failure:
        ThemeTokenView(resolved).annotation_kind_frame()
    assert failure.value.diagnostic_id == "E_THEME_TOKEN_TYPE"
