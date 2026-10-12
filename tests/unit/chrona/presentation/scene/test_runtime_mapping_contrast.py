"""Runtime ABC optimization preserves every completed contrast finding."""
from collections import UserDict
from collections.abc import Mapping
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
