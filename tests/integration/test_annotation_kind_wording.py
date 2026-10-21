"""An annotation kind `label` / `secondary` accepts `{wording: key}` and follows the Render Context locale (#1865)."""
from __future__ import annotations

from copy import deepcopy

import pytest

from chrona.presentation.annotation_kind_text import AnnotationKindTextError, kind_header
from chrona.presentation.model.wording_tables import wording_resolver
from chrona.resources import schema_validator
from tests.integration.test_ja_jp_builtin_wording import _font_descriptor
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr

KINDS = {
    "risk": {"label": {"wording": "annotation.risk"}, "secondary": "WARNING", "title": "{label} · {subject}",
             "color": "category:kind-alert"},
    "note": {"label": {"wording": "annotation.note"}, "secondary": {"wording": "annotation.risk"},
             "color": "category:kind-report"},
}


def _texts(tmp_path, locale, kinds=KINDS):
    source = ak.project()
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    ak.with_kind_theme(parts, kinds=kinds)
    directory = tmp_path / locale
    directory.mkdir()
    review = sr.render(directory, source, presentation=parts, locale=locale, font_metrics_path=_font_descriptor(directory))
    return {item.scene_id: item.text for item in review.surface.primitives if item.scene_id.startswith("annotation-kind-text:")}


def test_note_and_risk_headers_follow_the_locale(tmp_path):
    japanese, english = _texts(tmp_path, "ja-JP"), _texts(tmp_path, "en-US")
    assert japanese == {"annotation-kind-text:view-n0:0": "リスク · Task 0", "annotation-kind-text:view-n0:1": "WARNING",
                        "annotation-kind-text:view-n1:0": "注記", "annotation-kind-text:view-n1:1": "リスク"}
    assert english == {"annotation-kind-text:view-n0:0": "Risk · Task 0", "annotation-kind-text:view-n0:1": "WARNING",
                       "annotation-kind-text:view-n1:0": "Note", "annotation-kind-text:view-n1:1": "Risk"}


def test_a_literal_label_is_unchanged_under_every_locale(tmp_path):
    for locale in ("en-US", "ja-JP"):
        texts = _texts(tmp_path, locale, kinds=ak.KINDS)
        assert texts["annotation-kind-text:view-n0:0"] == "RISK · Task 0" and texts["annotation-kind-text:view-n1:1"] == "REPORT"


def test_the_view_wording_override_reaches_the_reference(tmp_path):
    source = ak.project()
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    ak.with_kind_theme(parts, kinds=KINDS)
    parts["view"]["body"]["wording"] = {"keys": {"annotation.risk": "Hazard"}}
    review = sr.render(tmp_path, source, presentation=parts)
    ids = {item.scene_id: item.text for item in review.surface.primitives}
    assert ids["annotation-kind-text:view-n0:0"] == "Hazard · Task 0"


def test_an_unknown_key_fails_with_the_wording_error_naming_the_key(tmp_path):
    kinds = deepcopy(KINDS)
    kinds["risk"]["label"] = {"wording": "annotation.nope"}
    with pytest.raises(Exception) as raised:
        _texts(tmp_path, "en-US", kinds=kinds)
    text = f"{raised.value} {getattr(raised.value, 'detail', '')}"
    assert "E_WORDING_KEY_UNKNOWN" in text and "annotation.nope" in text, text


def test_kind_header_reads_the_locale_and_names_an_unknown_key():
    assert kind_header("risk", KINDS["risk"], wording_resolver("ja-JP", None)).label == "リスク"
    assert kind_header("risk", KINDS["risk"]).label == "Risk"
    with pytest.raises(AnnotationKindTextError) as raised:
        kind_header("risk", {"label": {"wording": "annotation.nope"}})
    assert raised.value.code == "E_WORDING_KEY_UNKNOWN" and "annotation.nope" in raised.value.detail


def test_the_theme_schema_accepts_a_reference_for_label_and_secondary():
    validator = schema_validator("theme-v0.15.schema.yaml")
    theme = sr.bundle()["theme"]
    theme["body"]["annotationKinds"] = deepcopy(KINDS)
    assert not list(validator.iter_errors(theme))
    theme["body"]["annotationKinds"]["risk"]["label"] = {"wording": ""}
    assert list(validator.iter_errors(theme))
    theme["body"]["annotationKinds"]["risk"]["label"] = {"words": "x"}
    assert list(validator.iter_errors(theme))
