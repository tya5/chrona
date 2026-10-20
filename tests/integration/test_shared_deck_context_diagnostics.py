"""Authoring origins survive the actual CLI and standalone adapters."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from chrona.usecases.failure_report import StableFailure
from chrona.usecases.materialize import materialize


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("slides,pointer", [
    ("not-a-list", "/slides"),
    ([42, {"id": "overview", "evidence": "test", "context": "missing.yaml"}], "/slides/0"),
    ([{"id": "overview", "evidence": "test", "context": "missing.yaml"}], "/slides/0"),
])
def test_materializer_admits_manifest_before_reading_output_fields(tmp_path, slides, pointer):
    import yaml

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(yaml.safe_dump({
        "version": "chrona/example-materializer/v0.1", "role": "regression-corpus",
        "slides": slides,
    }), encoding="utf-8")
    with pytest.raises(StableFailure) as caught:
        materialize(manifest, "overview", tmp_path / "out")
    assert caught.value.source_ref == pointer
    assert "MANIFEST" in caught.value.code


@pytest.mark.parametrize("adapter", ["cli", "tool"])
def test_manifest_duplicate_is_pointed_before_any_render(tmp_path, adapter):
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        "version: chrona/example-materializer/v0.1\n"
        "role: regression-corpus\nid: deck\n"
        "contextDefaults:\n  theme: one\n  theme: two\n"
        "slides:\n- id: overview\n  contextOverrides: {id: context}\n"
        "  evidence: synthetic\n  expectedSvg: generated/result.svg\n",
        encoding="utf-8")
    command = ([sys.executable, "-m", "chrona", "materialize"] if adapter == "cli"
               else [sys.executable, "-m", "tools.materialize_example"])
    result = subprocess.run(
        [*command, str(manifest), "--slide", "overview", "--output", str(tmp_path / "out")],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "rejected"
    diagnostic, = payload["diagnostics"]
    assert "DUPLICATE" in diagnostic["code"]
    assert diagnostic["sourceRef"] == "/contextDefaults/theme"
    assert "Traceback" not in result.stderr
    assert not (tmp_path / "out").exists()
