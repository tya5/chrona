"""Manifest-dependent detail enrichment must not reselect already normalized surface facts."""
from datetime import date
from types import SimpleNamespace

import pytest

from chrona.presentation.contracts.resources import ReviewDetailInput, freeze
from chrona.presentation.model.projection import ReviewProjection
from chrona.presentation.review.detail import ReviewDetailError
from chrona.presentation.review.v05_content import normalize_v05_surface_content
from chrona.usecases.render_review import admit_v05_detail_content
from tests.unit.chrona.presentation.review.test_v05_content import EMPTY_SUMMARY, typed_view


def _selected(detail=None):
    projection = ReviewProjection((), (date(2026, 1, 1), date(2026, 1, 2)), (), ())
    view = typed_view({"body": {"tableColumns": (), "visibility": {}}})
    content = normalize_v05_surface_content(projection, {"annotations": {"note": {"text": "Retained note"}}},
                                           view, summary=EMPTY_SUMMARY, detail=detail)
    return projection, content


def _manifest(*, required=False):
    return SimpleNamespace(decisions=(SimpleNamespace(source="observations", kind="slot",
                                                       priority="required" if required else "preferred"),))


def test_detail_normalizes_before_admission_and_admission_preserves_content_identity():
    detail = ReviewDetailInput((), (), (), freeze({
        "columns": [{"id": "value", "label": "Value"}],
        "rows": [{"id": "reading", "source": "reported", "cells": {"value": "42"}}]}))
    _, selected = _selected(detail)

    assert selected.observation_columns == (("value", "Value"),)
    assert selected.observation_rows == (("reading", "reported", "normal", (("value", "42"),)),)
    assert selected.notes == (("note", "Retained note"),)
    admitted = admit_v05_detail_content(selected, detail=detail, layout_manifest=_manifest())
    assert admitted is selected
    assert admit_v05_detail_content(selected, detail=detail, layout_manifest=_manifest()) is selected


def test_detail_admission_keeps_the_missing_slot_diagnostic():
    detail = ReviewDetailInput((), (), (), freeze({"columns": [], "rows": []}))
    selected = _selected(detail)[1]
    with pytest.raises(ReviewDetailError, match="E_DETAIL_SLOT_REQUIRED") as raised:
        admit_v05_detail_content(selected, detail=detail, layout_manifest=SimpleNamespace(decisions=()))
    assert "observations" in str(raised.value) and "Layout slot" in str(raised.value)


def test_detail_enrichment_keeps_a_required_source_unavailable_diagnostic():
    selected = _selected()[1]
    with pytest.raises(ReviewDetailError, match="E_LAYOUT_SOURCE_UNAVAILABLE") as raised:
        admit_v05_detail_content(selected, detail=None, layout_manifest=_manifest(required=True))
    assert "observations" in str(raised.value) and "Detail content" in str(raised.value)
