from __future__ import annotations

import pytest

from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.paint import resolve_legend_shape_paint


@pytest.mark.parametrize("role", ("scale:legacy-key", "scale:style:012345"))
def test_rule_pair_legend_uses_completed_category_ink_and_role_shape(role: str):
    tokens = ThemeTokenView({
        "version": "chrona/resolved-theme/v0.2",
        "kind": "resolved-theme",
        "body": {
            "values": {
                "base": {"type": "color", "value": "#112233"},
                "width": {"type": "number", "value": 2.5},
                "opacity": {"type": "number", "value": 0.6},
            },
            "roles": {role: {"stroke": "base", "strokeWidth": "width", "opacity": "opacity"}},
            "metrics": {},
        },
    })

    paint = resolve_legend_shape_paint(tokens, role, "rule-pair", fill_override="#AA0000")

    assert paint.fill is None
    assert paint.stroke == "#AA0000"
    assert paint.stroke_width == 2.5
    assert paint.opacity == 0.6


def test_rule_pair_without_completed_category_ink_keeps_legacy_role_stroke():
    role = "scale:legacy-key"
    tokens = ThemeTokenView({
        "version": "chrona/resolved-theme/v0.2",
        "kind": "resolved-theme",
        "body": {
            "values": {
                "base": {"type": "color", "value": "#112233"},
                "width": {"type": "number", "value": 2.5},
            },
            "roles": {role: {"stroke": "base", "strokeWidth": "width"}},
            "metrics": {},
        },
    })

    paint = resolve_legend_shape_paint(tokens, role, "rule-pair")

    assert paint.stroke == "#112233"
    assert paint.stroke_width == 2.5
