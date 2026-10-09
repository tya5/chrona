"""#584: Theme resolution of `annotationKinds`, the kind roles and the kind header text contrast gate."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from chrona.presentation.color_scheme import ColorSchemeError, resolve_theme
from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView
from chrona.presentation.scene.capabilities import theme_role_property_consumer
from chrona.resources import validator_for_schema
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr

_THEME_SCHEMA = validator_for_schema(yaml.safe_load(
    (Path(__file__).resolve().parents[4] / "schemas/theme-v0.15.schema.yaml").read_text(encoding="utf-8")))


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
    assert failure.value.detail.startswith("'annotation-kind-label':'note':")


def test_without_a_bar_the_header_text_is_judged_on_the_note_box_fill():
    parts = sr.bundle()
    ak.with_kind_theme(parts, bar=False, label_fill="surface")  # white text on the light note box
    with pytest.raises(ColorSchemeError) as failure:
        resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    assert failure.value.diagnostic_id == "E_SCHEME_ANNOTATION_KIND_CONTRAST"
    assert failure.value.detail.startswith("'annotation-kind-label':'annotation-callout-box':")


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
    _, resolved = _resolve(border_side="end", border_width=5, padding=0.5)
    frame = ThemeTokenView(resolved).annotation_kind_frame()
    assert (frame.label_role, frame.secondary_role, frame.bar_role) == (
        "annotation-kind-label", "annotation-kind-secondary", "annotation-kind-bar")
    assert float(frame.bar_padding_em) == 0.5
    assert (frame.bar_bleed, frame.stamp_placement) == ("none", "column")
    assert not hasattr(frame, "accent_role")
    border = ThemeTokenView(resolved).annotation_container("annotation-note-box").border
    assert border["end"].width == 5 and border["end"].paint == "kind"
    _, plain = _resolve(bar=False, secondary=False, label_fill="text")
    assert ThemeTokenView(plain).annotation_kind_frame().bar_role is None
    assert ThemeTokenView(plain).annotation_kind_frame().secondary_role is None


@pytest.mark.parametrize("width", ["fill", "hug"])
def test_bar_width_is_typed_intent_with_fill_as_absent_default(width):
    parts, resolved = _resolve()
    assert ThemeTokenView(resolved).annotation_kind_frame().bar_width == "fill"
    parts["theme"]["body"]["roles"]["annotation-kind-bar"]["barWidth"] = width
    resolved = resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    assert ThemeTokenView(resolved).annotation_kind_frame().bar_width == width


@pytest.mark.parametrize("width", ["auto", 3, None])
def test_invalid_bar_width_is_rejected_at_the_role_pointer(width):
    parts, _ = _resolve()
    parts["theme"]["body"]["roles"]["annotation-kind-bar"]["barWidth"] = width
    resolved = resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    with pytest.raises(ThemeTokenError, match="E_THEME_TOKEN_TYPE"):
        ThemeTokenView(resolved).annotation_kind_frame()


def test_the_retired_edge_role_member_is_rejected_not_ignored():
    parts = sr.bundle()
    ak.with_kind_theme(parts, border_side="start")
    parts["theme"]["body"]["roles"]["annotation-kind-accent"]["edge"] = "removed-edge"
    with pytest.raises(ColorSchemeError) as failure:
        resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    assert failure.value.diagnostic_id == "E_THEME_ROLE_PROPERTY_UNSUPPORTED"


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
    assert frame.stamp_placement == "column"


@pytest.mark.parametrize("placement,corner", [(None, "end-top"), ("column", "start-bottom")])
def test_column_stamp_placement_keeps_the_legacy_corner(placement, corner):
    parts = sr.bundle()
    ak.with_kind_theme(parts, stamp="end-top")
    value = {"corner": corner, "size": 2}
    if placement is not None:
        value["placement"] = placement
    parts["theme"]["body"]["values"]["kind-stamp-placement"]["value"] = value
    resolved = resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    frame = ThemeTokenView(resolved).annotation_kind_frame()
    assert (frame.stamp_placement, frame.stamp_corner, float(frame.stamp_size)) == ("column", corner, 2.0)


def test_bar_end_stamp_placement_has_size_but_no_corner():
    parts = sr.bundle()
    ak.with_kind_theme(parts, stamp="end-top")
    parts["theme"]["body"]["values"]["kind-stamp-placement"]["value"] = {
        "placement": "bar-end", "size": 1.5}
    resolved = resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    frame = ThemeTokenView(resolved).annotation_kind_frame()
    assert (frame.stamp_placement, frame.stamp_corner, float(frame.stamp_size)) == ("bar-end", None, 1.5)


@pytest.mark.parametrize("value", [
    {"placement": "bar-end", "corner": "end-top", "size": 2},
    {"placement": "column", "size": 2},
    {"placement": "unknown", "size": 2},
])
def test_stamp_placement_schema_rejects_meaningless_corner_combinations(value):
    parts = sr.bundle()
    ak.with_kind_theme(parts, stamp="end-top")
    parts["theme"]["body"]["values"]["kind-stamp-placement"]["value"] = value
    assert tuple(_THEME_SCHEMA.iter_errors(parts["theme"]))


@pytest.mark.parametrize("bleed", ["none", "border"])
def test_bar_bleed_is_typed_intent_with_none_as_the_absent_default(bleed):
    parts, resolved = _resolve()
    assert ThemeTokenView(resolved).annotation_kind_frame().bar_bleed == "none"
    parts["theme"]["body"]["roles"]["annotation-kind-bar"]["barBleed"] = bleed
    resolved = resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    assert ThemeTokenView(resolved).annotation_kind_frame().bar_bleed == bleed


@pytest.mark.parametrize("bleed", ["edge", 3])
def test_bar_bleed_schema_rejects_values_outside_the_closed_vocabulary(bleed):
    parts = sr.bundle()
    ak.with_kind_theme(parts)
    parts["theme"]["body"]["roles"]["annotation-kind-bar"]["barBleed"] = bleed
    assert tuple(_THEME_SCHEMA.iter_errors(parts["theme"]))


def test_bar_bleed_is_admitted_only_as_annotation_kind_bar_geometry():
    assert theme_role_property_consumer("annotation-kind-bar", "barBleed") is not None
    assert theme_role_property_consumer("annotation-kind-stamp", "barBleed") is None
    assert theme_role_property_consumer("text", "barBleed") is None


@pytest.mark.parametrize("placement", [{"corner": "middle", "size": 2}, {"corner": "end-top", "size": 0},
                                       {"corner": "end-top", "size": -1}, {"corner": ["end-top"], "size": 2},
                                       {"placement": [], "size": 2}])
def test_an_invalid_stamp_placement_token_is_a_token_type_error(placement):
    parts = sr.bundle()
    ak.with_kind_theme(parts, stamp="end-top")
    parts["theme"]["body"]["values"]["kind-stamp-placement"]["value"] = placement
    resolved = resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    with pytest.raises(ThemeTokenError) as failure:
        ThemeTokenView(resolved).annotation_kind_frame()
    assert failure.value.diagnostic_id == "E_THEME_TOKEN_TYPE"
