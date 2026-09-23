import pytest

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_composer import visual_target_placement_id


@pytest.mark.parametrize(("kind", "selector", "expected"), [
    ("title", {}, "title"), ("column", {"id": "owner"}, "column:owner"),
    ("cell", {"object": "risk", "column": "owner"}, "cell:risk:owner"),
    ("annotation", {"id": "callout"}, "annotation-text:callout"),
    ("note", {"id": "scope"}, "note:scope"),
    ("group-detail", {"id": "firmware"}, "group-detail:firmware"),
    ("summary", {"panel": "key", "metric": "launch", "part": "value"}, "summary:key:launch:value"),
    ("axis-label", {"level": "month", "index": "2"}, "axis-label:month:2"),
    ("axis-band", {"level": "quarter", "index": "0"}, "axis-band:quarter:0"),
    ("variance-label", {"object": "risk"}, "variance:risk"),
    ("as-of-label", {}, "as-of-label"),
])
def test_visual_target_maps_only_to_existing_layout_identity(kind, selector, expected):
    assert visual_target_placement_id(kind, selector) == expected


def test_visual_target_rejects_incomplete_selector():
    with pytest.raises(LayoutError, match="E_LAYOUT_VISUAL_TARGET"):
        visual_target_placement_id("cell", {"object": "risk"})
