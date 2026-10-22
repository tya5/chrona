"""First-party designs declare a real, connector-free terminal note destination."""
from pathlib import Path

import pytest
import yaml

from chrona.resources import schema_validator


ROOT = Path(__file__).resolve().parents[5]


def _slots(node):
    if node["kind"] == "slot":
        yield node
    for child in node.get("children", ()):
        yield from _slots(child)


def _assert_list_candidate(candidate):
    assert candidate["region"] == {"kind": "slot", "source": "annotations"}
    assert candidate["search"] == {"kind": "row-aligned"}
    assert candidate["connector"] == {"kind": "none"}
    assert {"mark", "text", "annotation-box", "leader-route"} <= set(
        candidate["obstacles"]["classes"])


@pytest.mark.parametrize("design", ["marquee", "sunday", "target-b", "titlecard", "yuya"])
def test_design_declares_terminal_list_and_corresponding_slot(design):
    profile = yaml.safe_load((ROOT / "src/chrona/resources/designs" / design / "layout.yaml").read_text())
    assert not list(schema_validator("layout-profile-v0.10.schema.yaml").iter_errors(profile))
    candidates = profile["viewDefaults"]["annotationPlacement"]["note"]["candidates"]
    _assert_list_candidate(candidates[-1])
    assert any(slot["source"] == "annotations" for slot in _slots(profile["root"]))
    if design == "sunday":
        # Sunday deliberately tries plot/tail placements before its explicit list.
        assert all(candidate["connector"]["kind"] == "tail" for candidate in candidates[:-1])
    else:
        # Rail-first designs have a mandatory leader card, then an explicit
        # terminal list only for genuine box-placement exhaustion.
        assert candidates[0]["connector"] == {"kind": "leader"}
        assert len(candidates) == 2
        assert candidates[-1]["connector"] == {"kind": "none"}


def test_authored_roadmap_view_explicitly_migrates_its_placement_policies():
    view = yaml.safe_load((ROOT / "examples/chrona-roadmap/views/roadmap.yaml").read_text())
    assert not list(schema_validator("view-v0.28.schema.yaml").iter_errors(view))
    for annotation in view["body"]["annotations"]:
        _assert_list_candidate(annotation["candidates"][-1])
        assert annotation["candidates"][0]["connector"] == {"kind": "leader"}


def test_yuya_full_name_header_ground_is_below_row_rules():
    theme = yaml.safe_load((ROOT / "src/chrona/resources/designs/yuya/theme.yaml").read_text())
    role = theme["body"]["roles"]["group-header-band"]
    assert role["backgroundTreatment"] == "fill"
    assert role["backgroundPaintOrder"] < 10
