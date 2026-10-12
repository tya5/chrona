"""The public materializer stages and reads immutable previous-Scene bytes."""

from hashlib import sha256
import json
from pathlib import Path
import shutil

import yaml

from chrona.usecases import materialize as materialize_module
from tools.materialize_example import materialize


ROOT = Path(__file__).resolve().parents[2]


def test_public_materializer_reads_pinned_previous_scene_without_mutating_it(tmp_path, monkeypatch):
    example = tmp_path / "controller-z"
    shutil.copytree(ROOT / "tests/fixtures/controller-z", example)

    prior_address = "prior/executive.scene.json"
    prior_path = example / prior_address
    prior_path.parent.mkdir(parents=True)
    prior_bytes = (example / "generated/executive.scene.json").read_bytes()
    prior_path.write_bytes(prior_bytes)
    pin = {
        "store": {"provider": "local", "identity": "controller-z-example"},
        "address": prior_address,
        "revision": {"token": "previous-executive-scene-v1"},
        "contentIdentity": "sha256:" + sha256(prior_bytes).hexdigest(),
    }
    context_path = example / "contexts/executive.yaml"
    context = yaml.safe_load(context_path.read_bytes())
    context["body"].setdefault("inputs", {})["previousScene"] = pin
    context_path.write_text(yaml.safe_dump(context, sort_keys=False), encoding="utf-8")

    reads = []
    original_read = materialize_module.MaterializedResourceOverlay.read

    def capture_read(overlay, reference):
        payload = original_read(overlay, reference)
        if reference.get("address") == prior_address:
            reads.append((dict(reference), payload))
        return payload

    monkeypatch.setattr(materialize_module.MaterializedResourceOverlay, "read", capture_read)
    output = tmp_path / "materialized"
    materialize(example / "manifest.yaml", "executive", output, write=True)

    assert len(reads) == 1
    staged_reference, read_bytes = reads[0]
    assert "id" not in staged_reference and "kind" not in staged_reference
    assert staged_reference["address"] == prior_address
    assert staged_reference["revision"] == pin["revision"]
    assert read_bytes == prior_bytes
    assert prior_path.read_bytes() == prior_bytes

    scene_path = output / "review.scene.json"
    scene = json.loads(scene_path.read_bytes())
    primary_project = [item for item in scene["provenance"]["resources"] if item["kind"] == "project"]
    assert len(primary_project) == 1
    assert primary_project[0]["id"] == "controller-z-silicon-bringup"
    hint_summaries = [item for item in scene["diagnostics"]
                      if item.startswith("I_LAYOUT_RELATION_HINT_SUMMARY:")]
    assert hint_summaries
    assert scene["provenance"]["mode"] == "immutable"
