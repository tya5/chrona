"""Legend visuals bind semantic roles to final, identity-bearing labels."""
from datetime import date
from copy import deepcopy
from pathlib import Path

import pytest

from chrona.usecases.render_review import RenderFailed
from tests.integration.test_realized_legends import (
    ACTUAL, _detail, _encoded_parts, _parts, _source,
)
from tests.support import synthetic_review as sr


ROOT = Path(__file__).resolve().parents[2]
ICON_CATALOG = ROOT / "tests/fixtures/controller-z/icons.yaml"


def _render(tmp_path, source, parts, *, actual=None):
    parts["view"]["body"]["visuals"] = [
        {"target": {"kind": "legend", "role": "actual"},
         "ref": "chrona:risk", "decorative": True},
    ]
    return sr.render(tmp_path, source, presentation=parts, actual=actual,
                     detail=_detail(), icon_catalogs=(ICON_CATALOG,),
                     visual_profile="chrona-output/visual/v0.7-svg")


@pytest.mark.parametrize("groups", (1, 3))
def test_role_visual_fans_out_to_each_realized_hashed_label(tmp_path, groups):
    actual = deepcopy(ACTUAL)
    if groups == 1:
        actual["body"]["observations"] = actual["body"]["observations"][:1]
    rendered = _render(tmp_path, _source(), _parts(), actual=actual)
    swatches = tuple(item for item in rendered.surface.primitives
                     if item.purpose == "legend-swatch" and item.visual_role == "actual")
    labels = tuple(item for item in rendered.surface.primitives
                   if item.purpose == "legend-label" and item.source_ref in
                   {swatch.source_ref for swatch in swatches})
    icons = tuple(item for item in rendered.surface.primitives if item.kind == "Icon" and
                  item.scene_id.startswith("visual:legend:actual:"))

    assert len(swatches) == len(labels) == len(icons) == groups
    assert all(label.source_ref.startswith("actual:") for label in labels)
    assert {icon.scene_id.removeprefix("visual:").removesuffix(":leading") for icon in icons} == {
        label.scene_id for label in labels
    }


def test_filtered_absent_role_visual_still_fails_closed(tmp_path):
    parts = _encoded_parts()
    parts["view"]["body"]["visuals"] = [
        {"target": {"kind": "legend", "role": "planned"},
         "ref": "chrona:risk", "decorative": True},
    ]
    source = sr.project({
        "one": sr.span("one", date(2026, 2, 2), 5, owner="a"),
        "two": sr.span("two", date(2026, 2, 10), 5, owner="b"),
    })
    with pytest.raises(RenderFailed, match="E_LAYOUT_VISUAL_TARGET"):
        sr.render(tmp_path, source, presentation=parts, detail=_detail(),
                  icon_catalogs=(ICON_CATALOG,), visual_profile="chrona-output/visual/v0.7-svg")
