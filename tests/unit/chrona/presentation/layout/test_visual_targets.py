import pytest

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_composer import visual_target_placement_id


@pytest.mark.parametrize(("kind", "selector", "expected"), [
    ("title", {}, "title"), ("column", {"id": "owner"}, "column:owner"),
    ("cell", {"object": "risk", "column": "owner"}, "cell:risk:owner"),
    ("annotation", {"id": "note"}, "annotation-text:note"),
    ("axis-label", {"level": "month", "index": "2"}, "axis-label:month:2"),
])
def test_visual_target_maps_only_to_existing_layout_identity(kind, selector, expected):
    assert visual_target_placement_id(kind, selector) == expected


def test_visual_target_rejects_incomplete_selector():
    with pytest.raises(LayoutError, match="E_LAYOUT_VISUAL_TARGET"):
        visual_target_placement_id("cell", {"object": "risk"})
