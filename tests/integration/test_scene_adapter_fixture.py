import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "tools/scene_adapter_fixture.py"


def test_external_fixture_renders_a_capability_free_corpus_scene_from_scene_json_alone(tmp_path):
    scene = ROOT / "examples/halcyon-1/generated/05-dependency-network.scene.json"
    output = tmp_path / "network.svg"
    completed = subprocess.run([sys.executable, str(ADAPTER), "--scene", str(scene), "--output", str(output)],
                               text=True, capture_output=True, check=False)
    assert completed.returncode == 0
    assert output.read_text(encoding="utf-8").startswith("<svg")
    source = ADAPTER.read_text(encoding="utf-8")
    assert "import chrona" not in source and "from chrona" not in source


def test_external_fixture_uses_the_published_completed_canvas(tmp_path):
    source = json.loads((ROOT / "examples/halcyon-1/generated/05-dependency-network.scene.json").read_text(encoding="utf-8"))
    source["surfaces"][0]["canvasBounds"] = {"inline": 3, "block": 4, "inlineSize": 17, "blockSize": 19}
    scene, output = tmp_path / "scene.json", tmp_path / "network.svg"
    scene.write_text(json.dumps(source), encoding="utf-8")
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
