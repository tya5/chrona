from dataclasses import replace

import pytest

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.style_text import resolve_label_candidate_styles
from chrona.presentation.model.semantic_registry import inside_member_label_semantic
from chrona.presentation.model.style_rules import (
    OccurrenceStyleIndex,
    OccurrenceStyleIntent,
    StyleOccurrenceKey,
)
from chrona.presentation.model.theme_tokens import ThemeTokenView


def _intent(key, role):
    return OccurrenceStyleIntent(key, role, None, (f"rule:{role}",), (f"rule:{role}",), ())


def _tokens(*roles):
    values = {
        "family": {"type": "fontFamily", "value": "sans"},
        "weight": {"type": "fontWeight", "value": 400},
        "size": {"type": "number", "value": 12},
        "line": {"type": "number", "value": 1.2},
        "spacing": {"type": "number", "value": 0},
        "transform": {"type": "textTransform", "value": "none"},
        "numeric": {"type": "numericSpacing", "value": "proportional"},
        "ink": {"type": "color", "value": "#202020"},
    }
    role_bindings = {
        role: {
            "fontFamily": "family", "fontWeight": "weight", "fontSize": "size",
            "lineHeight": "line", "letterSpacing": "spacing", "textTransform": "transform",
            "numericSpacing": "numeric", "fill": "ink",
        }
        for role in roles
    }
    return ThemeTokenView({
        "version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
        "body": {"values": values, "roles": role_bindings},
    })


@pytest.mark.parametrize("source_kind", ["primary", "actual", "snapshot", "scenario"])
def test_inside_label_uses_canonical_source_semantic_but_outside_and_delta_stay_distinct(source_kind):
    label_key = StyleOccurrenceKey(
        "object:1", source_kind, "memberLabel", "row:1", "member:1", occurrence_kind="row"
    )
    inside_key = replace(label_key, semantic_id=inside_member_label_semantic(source_kind))
    delta_key = replace(label_key, semantic_id="finishDelta")
    index = OccurrenceStyleIndex((
        _intent(inside_key, "inside-treatment"),
        _intent(label_key, "outside-treatment"),
        _intent(delta_key, "delta-treatment"),
    ))

    styles = resolve_label_candidate_styles(
        label_key, ("inside", "outside"), index,
        _tokens("inside-treatment", "outside-treatment", "delta-treatment"),
    )
    delta_styles = resolve_label_candidate_styles(
        delta_key, ("inside",), index,
        _tokens("inside-treatment", "outside-treatment", "delta-treatment"),
    )

    assert styles["inside"].key == inside_key
    assert styles["inside"].role == "inside-treatment"
    assert styles["outside"].key == label_key
    assert styles["outside"].role == "outside-treatment"
    assert delta_styles["inside"].key == delta_key
    assert delta_styles["inside"].role == "delta-treatment"


def test_candidate_role_is_validated_before_any_measurement_or_fit():
    label_key = StyleOccurrenceKey(
        "object:1", "primary", "memberLabel", "row:1", "member:1", occurrence_kind="row"
    )
    inside_key = replace(label_key, semantic_id=inside_member_label_semantic("primary"))
    index = OccurrenceStyleIndex((_intent(inside_key, "incomplete-theme-role"),))

    with pytest.raises(LayoutError, match="E_STYLE_ROLE_INCOMPATIBLE") as caught:
        resolve_label_candidate_styles(label_key, ("inside",), index, _tokens())

    assert caught.value.diagnostic_id == "E_STYLE_ROLE_INCOMPATIBLE"
    assert caught.value.path == "/body/roles/incomplete-theme-role/fontFamily"
    assert "ruleIds=rule:incomplete-theme-role" in caught.value.detail
