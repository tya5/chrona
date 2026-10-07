"""Manifest-dependent detail enrichment must not reselect already normalized surface facts."""
from dataclasses import fields
from datetime import date
from types import SimpleNamespace

import pytest

from chrona.presentation.contracts.resources import ReviewDetailInput, freeze
from chrona.presentation.model.projection import ReviewProjection
from chrona.presentation.review.detail import ReviewDetailError
from chrona.presentation.review.v05_content import complete_v05_detail_content, normalize_v05_surface_content
from tests.unit.chrona.presentation.review.test_v05_content import EMPTY_SUMMARY, typed_view


def _selected():
    projection = ReviewProjection((), (date(2026, 1, 1), date(2026, 1, 2)), (), ())
    view = typed_view({"body": {"tableColumns": (), "visibility": {}}})
    content = normalize_v05_surface_content(projection, {"annotations": {"note": {"text": "Retained note"}}},
                                           view, summary=EMPTY_SUMMARY)
    return projection, content


def _manifest(*, required=False):
    return SimpleNamespace(decisions=(SimpleNamespace(source="observations", kind="slot",
                                                       priority="required" if required else "preferred"),))


def test_detail_enrichment_changes_only_manifest_admitted_detail_fields():
    projection, selected = _selected()
    detail = ReviewDetailInput((), (), (), freeze({
        "columns": [{"id": "value", "label": "Value"}],
        "rows": [{"id": "reading", "source": "reported", "cells": {"value": "42"}}]}))
    completed = complete_v05_detail_content(selected, projection, detail=detail, layout_manifest=_manifest())

    assert completed.observation_columns == (("value", "Value"),)
    assert completed.observation_rows == (("reading", "reported", "normal", (("value", "42"),)),)
    detail_fields = {"group_details", "milestones", "observation_columns", "observation_rows"}
    assert all(getattr(completed, field.name) is getattr(selected, field.name)
               for field in fields(selected) if field.name not in detail_fields)
    assert selected.observation_rows == ()
    assert completed.notes == (("note", "Retained note"),)


def test_detail_enrichment_keeps_the_missing_slot_diagnostic():
    projection, selected = _selected()
    detail = ReviewDetailInput((), (), (), freeze({"columns": [], "rows": []}))
    with pytest.raises(ReviewDetailError, match="E_DETAIL_SLOT_REQUIRED"):
        complete_v05_detail_content(selected, projection, detail=detail,
                                    layout_manifest=SimpleNamespace(decisions=()))


def test_detail_enrichment_keeps_a_required_source_unavailable_diagnostic():
    projection, selected = _selected()
    with pytest.raises(ReviewDetailError, match="E_LAYOUT_SOURCE_UNAVAILABLE"):
        complete_v05_detail_content(selected, projection, detail=None, layout_manifest=_manifest(required=True))
