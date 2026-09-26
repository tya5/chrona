from datetime import date
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import jsonschema
import pytest
import yaml

from chrona.resources import schema_resource
from tools.check_example_reachability import reachable_view_paths


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def _json_value(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


def _validator() -> jsonschema.Draft202012Validator:
    schema = yaml.safe_load(schema_resource("view-v0.26.schema.yaml").read_text(encoding="utf-8"))
    foundation = yaml.safe_load(schema_resource("presentation-resource-v0.1.schema.yaml").read_text(encoding="utf-8"))
    return jsonschema.Draft202012Validator(
        schema, resolver=jsonschema.RefResolver.from_schema(schema, store={foundation["$id"]: foundation})
    )


@pytest.mark.parametrize("path", reachable_view_paths(ROOT))
def test_declared_public_v03_view_validates(path: Path):
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert value.get("version") == "chrona/view/v0.26", path
    assert next(_validator().iter_errors(_json_value(value)), None) is None, path


def test_v03_relation_visibility_object_rejects_unsupported_policy():
    value = yaml.safe_load((ROOT / "examples/aster-ssd/views/01-overview.yaml").read_text(encoding="utf-8"))
    value["body"]["visibility"]["relations"] = {"mode": "all", "overflow": "truncate"}
    assert next(_validator().iter_errors(_json_value(value)), None) is not None


def test_v04_rejects_unimplemented_relation_fallback_contract():
    value = yaml.safe_load((ROOT / "examples/aster-ssd/views/01-overview.yaml").read_text(encoding="utf-8"))
    value["body"]["visibility"]["fallback"] = {"relations": ["above", "suppress"]}
    assert next(_validator().iter_errors(_json_value(value)), None) is not None


def test_view_admits_inside_at_each_member_label_side_ingress():
    value = yaml.safe_load((ROOT / "examples/aster-ssd/views/01-overview.yaml").read_text(encoding="utf-8"))
    value["body"]["visibility"]["labels"] = {
        "placement": "plot", "content": ["title"], "side": "inside", "overflow": "suppress",
    }
    value["body"]["visibility"]["fallback"] = {"labels": ["inside", "end", "suppress"]}
    assert next(_validator().iter_errors(_json_value(value)), None) is None
    schema = yaml.safe_load(schema_resource("view-v0.26.schema.yaml").read_text(encoding="utf-8"))
    assert "inside" in schema["$defs"]["presentationIntent"]["properties"]["label"]["properties"]["side"]["enum"]


def test_view_accepts_only_closed_progress_fill_sources():
    value = yaml.safe_load((ROOT / "examples/halcyon-1/views/02-programme-board.yaml").read_text(encoding="utf-8"))
    assert next(_validator().iter_errors(_json_value(value)), None) is None
    value["body"]["progressFill"] = {"source": "derived"}
    assert next(_validator().iter_errors(_json_value(value)), None) is not None


def test_v018_requires_closed_axis_and_table_header_orientation():
    value = yaml.safe_load((ROOT / "examples/halcyon-1/views/06-flight-readiness.yaml").read_text(encoding="utf-8"))
    assert next(_validator().iter_errors(_json_value(value)), None) is None
    del next(tier["label"] for tier in value["body"]["axis"]["tiers"] if "label" in tier)["orientation"]
    assert next(_validator().iter_errors(_json_value(value)), None) is not None
    value = yaml.safe_load((ROOT / "examples/halcyon-1/views/06-flight-readiness.yaml").read_text(encoding="utf-8"))
    value["body"]["tableColumns"][0]["headerOrientation"] = "diagonal"
    assert next(_validator().iter_errors(_json_value(value)), None) is not None


def test_v022_axis_name_table_is_only_a_finite_labels_tier_choice():
    source = yaml.safe_load((ROOT / "examples/controller-z/views/executive.yaml").read_text(encoding="utf-8"))
    value = deepcopy(source)
    labels = next(tier for tier in value["body"]["axis"]["tiers"] if tier["role"] == "labels")
    labels["label"]["nameTable"] = "ja-JP"
    assert next(_validator().iter_errors(_json_value(value)), None) is None

    labels["label"]["nameTable"] = "fr-FR"
    assert next(_validator().iter_errors(_json_value(value)), None) is not None

    value = deepcopy(source)
    non_label = next(tier for tier in value["body"]["axis"]["tiers"] if tier["role"] != "labels")
    non_label["label"] = {"form": "short-month", "align": "start", "overflow": "visible-overflow",
                          "orientation": "horizontal", "nameTable": "ja-JP"}
    assert next(_validator().iter_errors(_json_value(value)), None) is not None

    value = deepcopy(source)
    labels = next(tier for tier in value["body"]["axis"]["tiers"] if tier["role"] == "labels")
    labels["unit"] = "auto"
    labels["label"] = {"forms": {"month": "short-month"}, "align": "start",
                       "overflow": "visible-overflow", "orientation": "horizontal", "nameTable": "ja-JP"}
    assert next(_validator().iter_errors(_json_value(value)), None) is None

    value["version"] = "chrona/view/v0.21"
    assert next(_validator().iter_errors(_json_value(value)), None) is not None


def test_view_visual_target_selectors_and_encoding_eligibility_are_closed():
    value = yaml.safe_load((ROOT / "examples/controller-z/views/executive.yaml").read_text(encoding="utf-8"))
    value["body"]["visuals"] = [{"target": {"kind": "as-of-label"}, "ref": "chrona:risk"}]
    assert next(_validator().iter_errors(_json_value(value)), None) is None
    value["body"]["visuals"][0]["target"]["id"] = "invented"
    assert next(_validator().iter_errors(_json_value(value)), None) is not None
    value["body"]["visuals"] = [{"target": {"kind": "title"}, "encoding": {"field": "owner", "domain": {"fw": "chrona:risk"}}}]
    assert next(_validator().iter_errors(_json_value(value)), None) is not None
    value["body"]["visuals"] = [{"target": {"kind": "summary", "id": "key-figures"}, "ref": "chrona:risk"}]
    assert next(_validator().iter_errors(_json_value(value)), None) is not None


def test_v07_scenario_table_source_is_closed_to_id_or_title():
    value = yaml.safe_load((ROOT / "examples/halcyon-1/views/06-flight-readiness.yaml").read_text(encoding="utf-8"))
    value["body"]["tableColumns"][0]["source"] = {"scenario": "title"}
    assert next(_validator().iter_errors(_json_value(value)), None) is None
    value["body"]["tableColumns"][0]["source"] = {"scenario": "unknown"}
    assert next(_validator().iter_errors(_json_value(value)), None) is not None


def test_v16_table_intent_requires_finite_alignment_and_logical_width():
    value = yaml.safe_load((ROOT / "examples/aster-ssd/views/01-overview.yaml").read_text(encoding="utf-8"))
    column = value["body"]["tableColumns"][0]
    column.pop("align")
    assert next(_validator().iter_errors(_json_value(value)), None) is not None
    column["align"] = "start"
    column["width"] = {"content": True}
    assert next(_validator().iter_errors(_json_value(value)), None) is not None
    column["width"] = {"minmax": {"min": "content", "max": {"fr": 1}}}
    assert next(_validator().iter_errors(_json_value(value)), None) is None


def test_v21_background_decoration_has_independent_closed_row_and_group_policies():
    value = yaml.safe_load((ROOT / "examples/aster-ssd/views/01-overview.yaml").read_text(encoding="utf-8"))
    value["body"]["backgroundDecoration"] = {"rows": "gradient", "groups": "all"}
    assert next(_validator().iter_errors(_json_value(value)), None) is not None
    value["body"]["backgroundDecoration"] = {"rows": "alternate", "groups": "all"}
    assert next(_validator().iter_errors(_json_value(value)), None) is None
    body = value["body"]
    body["surface"] = "dependency-network"
    for name in ("tableColumns", "hierarchyColumn", "axis", "markers", "shading", "timePresentation", "annotations", "annotationPresentation"):
        body.pop(name, None)
    assert next(_validator().iter_errors(_json_value(value)), None) is not None


@pytest.mark.parametrize("key", ("entityIds", "profiles"))
def test_v03_selection_rejects_undefined_capability(key: str):
    value = yaml.safe_load((ROOT / "examples/aster-ssd/views/01-overview.yaml").read_text(encoding="utf-8"))
    value["body"]["selection"]["include"][key] = ["undefined"]
    assert next(_validator().iter_errors(_json_value(value)), None) is not None


def test_dependency_network_keeps_common_window_and_rejects_timeline_authoring():
    value = yaml.safe_load((ROOT / "examples/aster-ssd/views/01-overview.yaml").read_text(encoding="utf-8"))
    body = value["body"]
    body["surface"] = "dependency-network"
    forbidden = ("tableColumns", "hierarchyColumn", "backgroundDecoration", "axis", "markers", "shading", "timePresentation", "annotations", "annotationPresentation")
    saved = {name: body.pop(name) for name in forbidden if name in body}
    assert "window" in body
    assert next(_validator().iter_errors(_json_value(value)), None) is None
    for name, item in saved.items():
        candidate = deepcopy(value)
        candidate["body"][name] = item
        assert next(_validator().iter_errors(_json_value(candidate)), None) is not None, name


def _lane_view() -> dict:
    """The committed `rows.mode: lanes` migration (#467 L3: 02-programme-board)."""
    return yaml.safe_load((ROOT / "examples/halcyon-1/views/02-programme-board.yaml").read_text(encoding="utf-8"))


def test_lanes_mode_accepts_the_minimal_valid_shape():
    assert next(_validator().iter_errors(_json_value(_lane_view())), None) is None


def test_lanes_mode_requires_lane_table():
    value = _lane_view()
    del value["body"]["rows"]["laneTable"]
    assert next(_validator().iter_errors(_json_value(value)), None) is not None


def test_lanes_mode_forbids_explicit_row_items():
    value = _lane_view()
    value["body"]["rows"]["items"] = []
    assert next(_validator().iter_errors(_json_value(value)), None) is not None


def test_lanes_mode_forbids_automatic_point_policy():
    value = _lane_view()
    value["body"]["rows"]["points"] = "group-header"
    assert next(_validator().iter_errors(_json_value(value)), None) is not None


def test_lanes_mode_forbids_per_row_track_allocation():
    value = _lane_view()
    value["body"]["rows"]["trackAllocation"] = "collision"
    assert next(_validator().iter_errors(_json_value(value)), None) is not None


def test_lanes_mode_forbids_item_oriented_table_columns():
    value = _lane_view()
    value["body"]["tableColumns"] = [{"id": "Work package", "source": "title", "missing": "em-dash",
                                      "align": "start", "width": "content", "headerOrientation": "horizontal"}]
    assert next(_validator().iter_errors(_json_value(value)), None) is not None


def test_lanes_mode_forbids_hierarchy_grouping_and_hierarchy_column():
    value = _lane_view()
    value["body"]["grouping"] = {"by": "hierarchy", "order": []}
    assert next(_validator().iter_errors(_json_value(value)), None) is not None
    value = _lane_view()
    value["body"]["hierarchyColumn"] = "Work package"
    assert next(_validator().iter_errors(_json_value(value)), None) is not None


def test_lanes_mode_requires_selection_grouping_ordering_and_window_like_automatic():
    value = _lane_view()
    del value["body"]["selection"]
    assert next(_validator().iter_errors(_json_value(value)), None) is not None


def test_lanes_mode_is_table_timeline_only():
    value = _lane_view()
    value["body"]["surface"] = "dependency-network"
    assert next(_validator().iter_errors(_json_value(value)), None) is not None


def test_lanes_mode_requires_plot_placement_title_content_and_visible_overflow():
    value = _lane_view()
    value["body"]["visibility"]["labels"]["placement"] = "table"
    assert next(_validator().iter_errors(_json_value(value)), None) is not None

    value = _lane_view()
    value["body"]["visibility"]["labels"]["content"] = ["finishDelta"]
    assert next(_validator().iter_errors(_json_value(value)), None) is not None

    value = _lane_view()
    value["body"]["visibility"]["labels"]["overflow"] = "suppress"
    assert next(_validator().iter_errors(_json_value(value)), None) is not None


def test_lanes_mode_lane_table_label_is_closed_to_group_or_lane():
    value = _lane_view()
    value["body"]["rows"]["laneTable"]["label"] = "row"
    assert next(_validator().iter_errors(_json_value(value)), None) is not None


def test_automatic_and_explicit_rows_reject_the_lane_only_fields():
    value = yaml.safe_load((ROOT / "examples/halcyon-1/views/06-flight-readiness.yaml").read_text(encoding="utf-8"))
    value["body"]["rows"]["laneTable"] = {"label": "group"}
    assert next(_validator().iter_errors(_json_value(value)), None) is not None

    value = yaml.safe_load((ROOT / "examples/halcyon-1/views/06-flight-readiness.yaml").read_text(encoding="utf-8"))
    value["body"]["rows"]["trackAllocation"] = "collision"
    assert next(_validator().iter_errors(_json_value(value)), None) is not None
