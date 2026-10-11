from datetime import date
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import jsonschema
import pytest
import yaml

from chrona.resources import schema_resource, validator_for_schema
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
    schema = yaml.safe_load(schema_resource("view-v0.27.schema.yaml").read_text(encoding="utf-8"))
    foundation = yaml.safe_load(schema_resource("presentation-resource-v0.1.schema.yaml").read_text(encoding="utf-8"))
    return jsonschema.Draft202012Validator(
        schema, resolver=jsonschema.RefResolver.from_schema(
            schema, store={foundation["$id"]: foundation, schema["$id"]: schema}
        )
    )


def _validator_v028() -> jsonschema.Draft202012Validator:
    schema = yaml.safe_load(schema_resource("view-v0.28.schema.yaml").read_text(encoding="utf-8"))
    return validator_for_schema(schema)


@pytest.mark.parametrize("path", reachable_view_paths(ROOT))
def test_declared_public_v03_view_validates(path: Path):
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    version = value.get("version")
    validators = {
        "chrona/view/v0.27": _validator,
        "chrona/view/v0.28": _validator_v028,
    }
    assert version in validators, (path, version)
    assert next(validators[version]().iter_errors(_json_value(value)), None) is None, path


def test_lane_resource_migration_inventory_and_editorial_mirror():
    library = yaml.safe_load((ROOT / "src/chrona/resources/presets/library.yaml").read_text(encoding="utf-8"))
    entries = {entry["id"]: entry for entry in library["entries"] if entry["id"] != "chrona-default-draft"}  # the default has automatic rows, below
    assert len(entries) == 7
    for preset_id, entry in entries.items():
        member = entry["members"]["view"]
        path = ROOT / "src/chrona/resources" / member["sourceRoot"] / member["sourcePath"]
        view = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert view["version"] == "chrona/view/v0.28", preset_id
        assert next(_validator_v028().iter_errors(_json_value(view)), None) is None, preset_id
        assert view["body"]["rows"]["mode"] == "lanes", preset_id
        assert "tableColumns" not in view["body"], preset_id
    editorial = entries["editorial"]["members"]["view"]
    assert editorial["id"] == "chrona-preset-editorial-lanes"
    assert editorial["sourcePath"] == "view-lanes.yaml"

    default = yaml.safe_load((ROOT / "src/chrona/resources/presets/bundles/editorial-readable-default/view.yaml").read_text(encoding="utf-8"))
    assert default["body"]["rows"] == {"mode": "automatic"}
    assert [column["id"] for column in default["body"]["tableColumns"]] == ["Task", "Plan"]
    assert default["version"] == "chrona/view/v0.28"
    assert (ROOT / "src/chrona/resources/presets/bundles/editorial-readable-default/view.yaml").read_bytes() == \
        (ROOT / "examples/halcyon-1/views/editorial-readable-default.yaml").read_bytes()

    package_view = ROOT / "src/chrona/resources/presets/bundles/editorial/view-lanes.yaml"
    corpus_view = ROOT / "examples/halcyon-1/views/editorial-lanes.yaml"
    assert package_view.read_bytes() == corpus_view.read_bytes()
    reference = yaml.safe_load((ROOT / "examples/halcyon-1/views/editorial.yaml").read_text(encoding="utf-8"))
    assert reference["id"] == "chrona-preset-editorial"
    assert reference["body"]["rows"]["mode"] == "automatic"
    assert (ROOT / "src/chrona/resources/presets/bundles/editorial/view.yaml").read_bytes() == \
        (ROOT / "examples/halcyon-1/views/editorial.yaml").read_bytes()


def test_halcyon_lane_slides_and_full_02_packing_policy():
    for slide in ("02-programme-board", "03-launch-campaign", "editorial-lanes"):
        view = yaml.safe_load((ROOT / f"examples/halcyon-1/views/{slide}.yaml").read_text(encoding="utf-8"))
        assert view["version"] == "chrona/view/v0.28"
        assert next(_validator_v028().iter_errors(_json_value(view)), None) is None, slide
        assert view["body"]["rows"]["mode"] == "lanes"
        assert view["body"]["visibility"]["labels"]["placement"] == "plot"
        assert "title" in view["body"]["visibility"]["labels"]["content"]
        assert "tableColumns" not in view["body"]

    # Preserve one committed automatic/table witness and its original bytes.
    mission = ROOT / "examples/halcyon-1/views/01-mission-brief.yaml"
    assert yaml.safe_load(mission.read_text(encoding="utf-8"))["body"]["rows"]["mode"] == "automatic"

    board = yaml.safe_load((ROOT / "examples/halcyon-1/views/02-programme-board.yaml").read_text(encoding="utf-8"))
    assert board["body"]["rows"]["packing"] == ["explicit", "attached", "chain", "dates"]
    assert "finishDelta" in board["body"]["visibility"]["labels"]["content"]

    reference_context = yaml.safe_load((ROOT / "examples/halcyon-1/contexts/13-gallery-editorial.yaml").read_text(encoding="utf-8"))
    lane_context = yaml.safe_load((ROOT / "examples/halcyon-1/contexts/16-gallery-editorial-lanes.yaml").read_text(encoding="utf-8"))
    assert reference_context["id"] == "halcyon-1-13-gallery-editorial"
    assert reference_context["body"]["view"]["id"] == "chrona-preset-editorial"
    assert lane_context["id"] == "halcyon-1-16-gallery-editorial-lanes"
    assert lane_context["body"]["view"]["id"] == "chrona-preset-editorial-lanes"
    assert lane_context["body"]["view"]["address"] == "views/editorial-lanes.yaml"
    context_schema = yaml.safe_load(schema_resource("render-context-v0.17.schema.yaml").read_text(encoding="utf-8"))
    assert next(validator_for_schema(context_schema).iter_errors(_json_value(lane_context)), None) is None


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
    schema = yaml.safe_load(schema_resource("view-v0.27.schema.yaml").read_text(encoding="utf-8"))
    assert "inside" in schema["$defs"]["presentationIntent"]["properties"]["label"]["properties"]["side"]["enum"]


def test_view_accepts_only_closed_progress_fill_sources():
    value = yaml.safe_load((ROOT / "examples/halcyon-1/views/02-programme-board.yaml").read_text(encoding="utf-8"))
    assert next(_validator_v028().iter_errors(_json_value(value)), None) is None
    value["body"]["progressFill"] = {"source": "derived"}
    assert next(_validator_v028().iter_errors(_json_value(value)), None) is not None


def test_v028_lane_rows_require_closed_lane_intent_and_visible_names():
    value = yaml.safe_load((ROOT / "examples/halcyon-1/views/02-programme-board.yaml").read_text(encoding="utf-8"))
    body = value["body"]
    body.pop("tableColumns", None)
    body["rows"] = {"mode": "lanes", "laneTable": {"label": "group", "count": True}}
    body["visibility"]["labels"] = {
        "placement": "plot", "content": ["title", "finishDelta"],
        "side": "auto", "overflow": "suppress",
    }
    assert next(_validator_v028().iter_errors(_json_value(value)), None) is None

    invalid = deepcopy(value)
    invalid["body"]["visibility"]["labels"]["overflow"] = "visible-overflow"
    assert next(_validator_v028().iter_errors(_json_value(invalid)), None) is not None

    invalid = deepcopy(value)
    invalid["body"]["rows"].pop("laneTable")
    assert next(_validator_v028().iter_errors(_json_value(invalid)), None) is not None

    automatic = yaml.safe_load((ROOT / "examples/halcyon-1/views/02-programme-board.yaml").read_text(encoding="utf-8"))
    automatic["body"]["rows"]["mode"] = "automatic"
    automatic["body"]["rows"]["laneTable"] = {"label": "group"}
    assert next(_validator_v028().iter_errors(_json_value(automatic)), None) is not None

    invalid = deepcopy(value)
    invalid["body"]["grouping"]["by"] = "hierarchy"
    assert next(_validator_v028().iter_errors(_json_value(invalid)), None) is not None

    invalid = deepcopy(value)
    invalid["body"]["rows"]["trackAllocation"] = "collision"
    assert next(_validator().iter_errors(_json_value(invalid)), None) is not None

    explicit = yaml.safe_load((ROOT / "tests/fixtures/multi-lane-milestones/view.yaml").read_text(encoding="utf-8"))
    explicit["body"]["rows"]["trackAllocation"] = "collision"
    assert next(_validator().iter_errors(_json_value(explicit)), None) is None
    explicit["body"]["rows"]["laneTable"] = {"label": "group"}
    assert next(_validator().iter_errors(_json_value(explicit)), None) is not None
    explicit["body"]["rows"].pop("laneTable")
    explicit["body"]["rows"]["trackAllocation"] = "member-index"
    assert next(_validator().iter_errors(_json_value(explicit)), None) is not None


def test_v028_lane_packing_and_lane_keys_are_closed_and_lane_only():
    value = yaml.safe_load((ROOT / "examples/halcyon-1/views/02-programme-board.yaml").read_text(encoding="utf-8"))
    value["version"] = "chrona/view/v0.28"
    value["body"].pop("tableColumns", None)
    value["body"]["rows"] = {"mode": "lanes", "laneTable": {"label": "group"}}
    value["body"]["visibility"]["labels"] = {
        "placement": "plot", "content": ["title"], "side": "auto", "overflow": "suppress",
    }
    validator = _validator_v028()
    assert next(validator.iter_errors(_json_value(value)), None) is None

    rows = value["body"]["rows"]
    rows["packing"] = ["explicit", "attached", "dates"]
    rows["laneKeys"] = {"field": "lane", "byObject": {"obj-1": "primary"}}
    assert next(validator.iter_errors(_json_value(value)), None) is None
    rows["packing"] = []
    assert next(validator.iter_errors(_json_value(value)), None) is None

    invalid = deepcopy(value)
    invalid["body"]["rows"]["packing"] = ["dates", "chain"]
    assert next(validator.iter_errors(_json_value(invalid)), None) is not None
    invalid = deepcopy(value)
    invalid["body"]["rows"]["packing"] = ["explicit", "explicit"]
    assert next(validator.iter_errors(_json_value(invalid)), None) is not None
    invalid = deepcopy(value)
    invalid["body"]["rows"]["laneKeys"] = {"byObject": {"obj-1": ""}}
    assert next(validator.iter_errors(_json_value(invalid)), None) is not None
    invalid = deepcopy(value)
    invalid["body"]["rows"]["laneKeys"] = {}
    assert next(validator.iter_errors(_json_value(invalid)), None) is not None
    for mode in ("automatic", "explicit"):
        invalid = deepcopy(value)
        invalid["body"]["rows"] = {"mode": mode, "packing": ["explicit"]}
        if mode == "explicit":
            invalid["body"]["rows"]["items"] = [{"id": "r", "depth": 0, "items": [{"id": "i", "source": {"kind": "primary", "object": "obj-1"}}]}]
        assert next(validator.iter_errors(_json_value(invalid)), None) is not None


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
    value = yaml.safe_load((ROOT / "examples/halcyon-1/views/04-tvac-slip.yaml").read_text(encoding="utf-8"))
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
