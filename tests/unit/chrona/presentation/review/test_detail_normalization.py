"""Detail facts are selected once from validated resources and the immutable projection."""
from datetime import date
from types import SimpleNamespace

import pytest

from chrona.presentation.contracts.resources import ReviewDetailInput, freeze
from chrona.presentation.review.detail import ReviewDetailError, normalize_v05_review_detail_profile


def _detail(*, groups=(), milestones=(), observations=None):
    return ReviewDetailInput(tuple(freeze(item) for item in groups), tuple(milestones), (),
                             freeze(observations) if observations is not None else None)


def test_normalization_preserves_projection_group_order_point_dates_and_observation_provenance():
    items = (
        SimpleNamespace(object_id="b-item", group_id="b", source_type="span", planned={}, title="B"),
        SimpleNamespace(object_id="point", group_id="a", source_type="point",
                         planned={"at": date(2026, 1, 1)}, title="Launch"),
        SimpleNamespace(object_id="a-item", group_id="a", source_type="span", planned={}, title="A"),
    )
    detail = _detail(
        groups=({"groupId": "a", "label": "Alpha", "description": "A detail"},
                {"groupId": "b", "label": "Beta", "description": "B detail"}),
        milestones=("point",),
        observations={"columns": [{"id": "reading", "label": "Reading"},
                                   {"id": "unit", "label": "Unit"}],
                      "rows": [{"id": "r1", "source": "supplier log", "emphasis": "attention",
                                "cells": {"unit": "kg", "reading": "42"}}]},
    )

    normalized = normalize_v05_review_detail_profile(detail, items)

    assert normalized.group_details == (("b", "Beta", "B detail"), ("a", "Alpha", "A detail"))
    assert normalized.milestones == (("point", "Launch", date(2026, 1, 1)),)
    assert normalized.observation_columns == (("reading", "Reading"), ("unit", "Unit"))
    assert normalized.observation_rows == (("r1", "supplier log", "attention",
                                             (("reading", "42"), ("unit", "kg"))),)


@pytest.mark.parametrize(("detail", "items", "diagnostic", "operand"), [
    (_detail(groups=({"groupId": "g", "label": "G", "description": "one"},
                    {"groupId": "g", "label": "G", "description": "two"})), (), "E_DETAIL_DUPLICATE_GROUP", "/groupDetails/groupId='g'"),
    (_detail(groups=({"groupId": "missing", "label": "G", "description": "x"},)), (), "E_DETAIL_GROUP_REFERENCE", "'missing'"),
    (_detail(milestones=("p", "p")), (), "E_DETAIL_DUPLICATE_MILESTONE", "/milestones='p'"),
    (_detail(milestones=("missing",)), (), "E_DETAIL_MILESTONE_REFERENCE", "'missing'"),
    (_detail(observations={"columns": [{"id": "a", "label": "A"}, {"id": "a", "label": "A2"}],
                           "rows": []}), (), "E_DETAIL_DUPLICATE_COLUMN", "/observations/columns/id='a'"),
    (_detail(observations={"columns": [{"id": "a", "label": "A"}],
                           "rows": [{"id": "r", "source": "s", "cells": {"a": "1"}},
                                    {"id": "r", "source": "s", "cells": {"a": "2"}}]}), (), "E_DETAIL_DUPLICATE_ROW", "/observations/rows/id='r'"),
    (_detail(observations={"columns": [{"id": "a", "label": "A"}],
                           "rows": [{"id": "r", "source": "s", "cells": {}}]}), (), "E_DETAIL_OBSERVATION_CELLS", "missing=['a']"),
    (_detail(observations={"columns": [{"id": "a", "label": "A"}],
                           "rows": [{"id": "r", "source": "  ", "cells": {"a": "1"}}]}), (), "E_DETAIL_OBSERVATION_PROVENANCE", "source='  '"),
])
def test_normalization_preserves_semantic_reference_and_observation_diagnostics(detail, items, diagnostic, operand):
    with pytest.raises(ReviewDetailError, match=diagnostic) as error:
        normalize_v05_review_detail_profile(detail, items)
    assert operand in str(error.value)


def test_milestone_references_must_resolve_to_selected_point_with_a_date():
    span = SimpleNamespace(object_id="span", group_id="g", source_type="span", planned={"at": date(2026, 1, 1)}, title="Span")
    with pytest.raises(ReviewDetailError, match="E_DETAIL_MILESTONE_REFERENCE") as error:
        normalize_v05_review_detail_profile(_detail(milestones=("span",)), (span,))
    assert "/objects/'span' sourceType='span'" in str(error.value)


def test_milestone_date_diagnostic_names_object_and_invalid_at_operand():
    point = SimpleNamespace(object_id="dated-point", group_id="g", source_type="point",
                            planned={"at": "not-a-date"}, title="Point")
    with pytest.raises(ReviewDetailError, match="E_DETAIL_MILESTONE_REFERENCE") as error:
        normalize_v05_review_detail_profile(_detail(milestones=("dated-point",)), (point,))
    assert "/objects/'dated-point'/planned/at='not-a-date' (str)" in str(error.value)
