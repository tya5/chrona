import json
from pathlib import Path
import subprocess
import sys

from chrona.presentation.scene.serialization import validate_scene_document


ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "tools/scene_adapter_fixture.py"


def _capability_free_scene(canvas=None):
    canvas = canvas or {"inline": 0, "block": 0, "inlineSize": 240, "blockSize": 80}
    viewport = {"inlineSize": canvas["inlineSize"], "blockSize": canvas["blockSize"]}
    return {
        "version": "chrona/scene/v0.6",
        "kind": "scene",
        "provenance": {"mode": "immutable", "chronaVersion": "0.1.0", "resources": []},
        "viewport": viewport,
        "requiredCapabilities": [],
        "surfaces": [{
            "id": "adapter-fixture",
            "slots": [{
                "id": "content",
                "source": "title",
                "bounds": canvas,
                "priority": "required",
                "overflow": "visible-overflow",
            }],
            "rows": [],
            "columns": [],
            "groups": [],
            "canvasBounds": canvas,
            "primitives": [{
                "id": "label",
                "kind": "Text",
                "sourceRef": "label",
                "sourceKind": "fixture",
                "purpose": "title-text",
                "visualRole": "text",
                "bounds": {"inline": 12, "block": 12, "inlineSize": 120, "blockSize": 20},
                "slotId": "content",
                "text": "Adapter fixture",
                "paint": {"fill": "#101820", "opacity": 1.0},
            }],
        }],
        "manifest": {
            "version": "chrona/scene-manifest/v0.1",
            "settingsVersion": "chrona/render-context/v0.17",
            "viewport": viewport,
            "selectedObjectIds": [],
            "fontAssetIdentities": [],
            "contentFamilyCounts": {
                "relations": 0, "annotations": 0, "notes": 0, "legendEntries": 0,
                "summaryPanels": 0, "groupDetails": 0, "milestones": 0, "observationRows": 0,
            },
            "surfaceScales": [],
            "visualRoleCounts": {},
        },
        "diagnostics": [],
    }


def _write_scene(path, document):
    validate_scene_document(document)
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_external_fixture_renders_a_capability_free_scene_from_scene_json_alone(tmp_path):
    scene = _write_scene(tmp_path / "scene.json", _capability_free_scene())
    output = tmp_path / "network.svg"
    completed = subprocess.run([sys.executable, str(ADAPTER), "--scene", str(scene), "--output", str(output)],
                               text=True, capture_output=True, check=False)
    assert completed.returncode == 0
    assert output.read_text(encoding="utf-8").startswith("<svg")
    source = ADAPTER.read_text(encoding="utf-8")
    assert "import chrona" not in source and "from chrona" not in source


def test_external_fixture_uses_the_published_completed_canvas(tmp_path):
    source = _capability_free_scene({"inline": 3, "block": 4, "inlineSize": 17, "blockSize": 19})
    scene, output = tmp_path / "scene.json", tmp_path / "network.svg"
    _write_scene(scene, source)
    completed = subprocess.run([sys.executable, str(ADAPTER), "--scene", str(scene), "--output", str(output)],
                               text=True, capture_output=True, check=False)
    assert completed.returncode == 0
    assert 'width="17" height="19" viewBox="3 4 17 19"' in output.read_text(encoding="utf-8")


def test_external_fixture_rejects_a_scene_with_an_undeclared_capability(tmp_path):
    scene = ROOT / "examples/halcyon-1/generated/02-programme-board.scene.json"
    completed = subprocess.run([sys.executable, str(ADAPTER), "--scene", str(scene),
                                "--output", str(tmp_path / "board.svg")],
                               text=True, capture_output=True, check=False)
    assert completed.returncode == 1
    result = json.loads(completed.stdout)
    assert result["code"] == "E_SCENE_CAPABILITY_UNSUPPORTED"
    assert result["missingCapabilities"]
