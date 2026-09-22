from pathlib import Path

import yaml

from chrona.presentation.model.federation import federated_scene_input


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
FIXTURES = ROOT / "conformance" / "federation"


def _load(name):
    return yaml.safe_load((FIXTURES / name).read_text())


def test_federated_scene_input_namespaces_display_only_export_objects():
    plan = _load("program-federation-v0.2.yaml")
    child = _load("firmware-program.yaml")
    scene_input = federated_scene_input(plan, {"firmware": child})
    assert set(scene_input.nodes) == {"firmware:evt", "firmware:validation"}
    assert scene_input.nodes["firmware:evt"]["sceneId"] == "federation:firmware:evt"
    assert "objects" not in plan
    assert scene_input.nodes["firmware:evt"]["aggregation"] == {"method": "weighted-object-progress"}
