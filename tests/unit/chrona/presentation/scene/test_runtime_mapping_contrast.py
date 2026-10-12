"""Runtime ABC optimization preserves every completed contrast finding."""
from collections import UserDict
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from types import MappingProxyType
import json
import typing
import yaml

import pytest

from chrona.presentation.scene import contrast_policy as policy
from tests.unit.chrona.presentation.scene.test_contrast_policy import _primitive, _scene


def _compare(document, monkeypatch):
    assert policy.Mapping is Mapping  # prevent the expensive typing alias returning
    actual = policy.evaluate_scene_contrast(document)
    with monkeypatch.context() as old:
        old.setattr(policy, "Mapping", typing.Mapping)
        old.setattr(policy, "_prepare_primitives", lambda values: values)
        expected = policy.evaluate_scene_contrast(document)
    assert actual == expected
    assert [item.as_mapping() for item in actual] == [item.as_mapping() for item in expected]


@pytest.mark.parametrize("container", [dict, UserDict, MappingProxyType])
def test_runtime_mapping_preserves_nested_mapping_and_translucent_ground_findings(container, monkeypatch):
    def wrap(value):
        if isinstance(value, dict):
            return container({key: wrap(item) for key, item in value.items()})
        if isinstance(value, list):
            return [wrap(item) for item in value]
        return value
    document = wrap(_scene(
        _primitive("panel", "unclassified", "panel", "#EEEEEE", order=10),
        _primitive("bar", "planned", "planned", "#888888", opacity=0.5, order=100),
        _primitive("text", "variance-ahead", "table-cell", "#999999", treatment="required", order=110)))
    _compare(document, monkeypatch)


@pytest.mark.corpus
def test_all_public_scene_contrast_payloads_match_the_old_runtime_alias(monkeypatch):
    root = Path(__file__).resolve().parents[5]
    scenes = sorted({manifest.parent / slide["expectedScene"]
        for manifest in root.glob("examples/*/manifest.yaml")
        for slide in yaml.safe_load(manifest.read_bytes())["slides"]})
    assert scenes  # never silently turn a missing inventory into an empty sweep
    for path in scenes:
        _compare(json.loads(path.read_bytes()), monkeypatch)


def test_classification_is_once_and_plain_scenes_have_no_sparse_ink_scan(monkeypatch):
    builds, sparse_candidates = [], []
    original_prepare, original_candidates = policy._prepare_primitives, policy._candidate_entries
    def prepare(primitives):
        builds.append(len(primitives))
        return original_prepare(primitives)
    def entries(primitives, category):
        result = original_candidates(primitives, category)
        if category == "sparse":
            sparse_candidates.append(len(result))
        return result
    monkeypatch.setattr(policy, "_prepare_primitives", prepare)
    monkeypatch.setattr(policy, "_candidate_entries", entries)
    document = _scene(_primitive("panel", "unclassified", "panel", "#FFFFFF", order=10),
        *(_primitive(f"text:{index}", "variance-ahead", "table-cell", "#999999",
                     treatment="required", order=100 + index) for index in range(30)))
    policy.evaluate_scene_contrast(document)
    assert builds == [31]
    assert sparse_candidates and set(sparse_candidates) == {0}


def test_prepared_view_is_private_immutable_and_not_reused_across_modified_input():
    primitives = [_primitive("panel", "unclassified", "panel", "#FFFFFF", order=10)]
    before = deepcopy(primitives)
    prepared = policy._prepare_primitives(primitives)
    assert policy._prepare_primitives(prepared) is prepared
    assert primitives == before
    with pytest.raises(TypeError):
        prepared.categories["hosts"] = ()
    with pytest.raises(TypeError):
        prepared.first_ids["panel"] = (2, primitives[0])
    primitives.append(_primitive("new", "unclassified", "panel", "#BBBBBB", order=20))
    second = policy._prepare_primitives(primitives)
    assert len(prepared) == 1 and len(second) == 2


@pytest.mark.parametrize("case", ["duplicate-id", "paint-order-tie", "malformed-frame", "malformed-box", "invalid-primitive"])
def test_cached_shortlists_preserve_legacy_finding_and_failure_order(case, monkeypatch):
    primitives = [_primitive("panel", "unclassified", "panel", "#EEEEEE", order=10),
                  _primitive("mark", "planned", "planned", "#999999", order=100)]
    if case == "duplicate-id":
        primitives.insert(1, _primitive("panel", "unclassified", "panel", "#BBBBBB", order=20))
    elif case == "paint-order-tie":
        primitives.insert(1, _primitive("tie", "unclassified", "panel", "#BBBBBB", order=10))
    elif case == "malformed-frame":
        primitives.insert(1, _primitive("frame", "frame-glyph", "frame-glyph", "#BBBBBB", kind="Symbol", order=20))
    elif case == "malformed-box":
        primitives[0]["bounds"] = {"inline": "bad"}
    else:
        primitives.append(None)
    document = _scene(*primitives)
    def outcome():
        try:
            return policy.evaluate_scene_contrast(document)
        except (ValueError, TypeError, KeyError) as error:
            return type(error), str(error)
    actual = outcome()
    with monkeypatch.context() as old:
        old.setattr(policy, "_prepare_primitives", lambda values: values)
        expected = outcome()
    assert actual == expected
