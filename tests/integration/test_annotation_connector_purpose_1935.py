"""A declared connector is drawn or named: a purpose without a leader style says so (#1935)."""
from __future__ import annotations

from xml.etree import ElementTree

import pytest

from tests.integration.test_annotation_card_fallthrough_1906 import BODY, _candidate, _fixture
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr

CODE = "W_LAYOUT_ANNOTATION_CONNECTOR_UNSUPPORTED_FOR_PURPOSE"
PURPOSES = ("callout", "highlight", "note", "explanatory-arrow")
REGIONS = ("rail", "plot")


def _render(tmp_path, purpose, connector, region):
    source, parts = _fixture()
    annotation = parts["view"]["body"]["annotations"][0]
    annotation["purpose"] = purpose
    if region == "rail":
        annotation["candidates"] = [_candidate("only", connector)]
    else:
        annotation["candidates"] = [sr.candidate("only", connector=connector)]
    return ak.render(tmp_path, source, parts)


@pytest.mark.parametrize("region", REGIONS)
@pytest.mark.parametrize("connector", ("leader", "none"))
@pytest.mark.parametrize("purpose", PURPOSES)
def test_every_purpose_connector_combination_draws_or_names_its_connector(tmp_path, purpose, connector, region):
    rendered = _render(tmp_path, purpose, connector, region)
    ids = {item.scene_id: item for item in rendered.surface.primitives}
    svg = {item.get("data-scene-id") for item in ElementTree.fromstring(rendered.artifact.content).iter()
           if item.get("data-scene-id")}
    warned = [item for item in rendered.scene.diagnostics if item.startswith(CODE)]
    # The box (or, for a connector-free rail candidate, its list entry) and the full body are kept.
    shown = "annotation-box:view-n0" if "annotation-box:view-n0" in ids else "annotation-list:view-n0"
    assert shown in ids and shown in svg
    assert any(BODY in item.text for key, item in ids.items()
               if key.startswith("annotation-text:") or key.startswith("annotation-list:"))
    if connector == "none":
        assert "annotation-leader:view-n0" not in ids
        assert warned == []
    elif purpose == "highlight":
        # No leader style exists for a highlight: no leader, one pointed diagnostic.
        assert "annotation-leader:view-n0" not in ids
        assert warned == [f"{CODE}:view-n0:highlight:leader"]
    else:
        assert "annotation-leader:view-n0" in ids and "annotation-leader:view-n0" in svg
        assert warned == []
