from copy import deepcopy

import pytest

from chrona.presentation_paint import resolve_facet_paint
from chrona.presentation_settings import builtin_bases


def test_facet_paint_uses_group_then_default_then_global_role():
    theme = builtin_bases()["executive-v0.2"]["theme"]
    assert resolve_facet_paint(theme, "delivery", "actual")["color"] == "#176F59"
    assert resolve_facet_paint(theme, "another-group", "actual")["color"] == "#269D79"
    del theme["facetPaints"]["default"]["baseline"]
    assert resolve_facet_paint(theme, "another-group", "baseline") == theme["paints"]["planned"]


def test_facet_paint_rejects_unknown_facet_and_missing_global_fallback():
    theme = builtin_bases()["executive-v0.2"]["theme"]
    with pytest.raises(ValueError, match="E_PRESENTATION_FACET_UNKNOWN"):
        resolve_facet_paint(theme, "delivery", "not-a-facet")
    missing = deepcopy(theme)
    del missing["facetPaints"]["default"]["variance"]
    del missing["paints"]["varianceBehind"]
    with pytest.raises(ValueError, match="E_PRESENTATION_FACET_PAINT"):
        resolve_facet_paint(missing, "delivery", "variance")
