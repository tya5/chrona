"""A Render Context input that the render never reads is an authored intent lost.

The check itself lives in ``chrona.app.cli`` behind ``--reject-unused-closure-inputs``;
these tests exercise it over the shipped examples. `known_unused.yaml` pins the inputs
that are dropped today, on the same rules as the output-property gate: a pinned input
that is still dropped is reported, one that starts being read fails so its pin goes.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

from tools.materialize_example import _copy_context_closure

ROOT = Path(__file__).resolve().parents[3]
KNOWN = yaml.safe_load((Path(__file__).parent / "known_unused.yaml").read_text()) or {}


def _slides():
    for manifest_path in sorted(ROOT.glob("examples/*/manifest.yaml")):
        manifest = yaml.safe_load(manifest_path.read_text())
        example = manifest_path.parent
        for slide in manifest.get("slides", ()):
            identity = f"{example.name}/{slide['id']}"
            yield pytest.param(identity, example, example / str(slide.get("context", manifest["context"])), id=identity)


@pytest.mark.parametrize("slide,example,context_path", list(_slides()))
def test_every_declared_closure_input_is_read(slide, example, context_path):
    with tempfile.TemporaryDirectory() as temporary:
        snapshot = Path(temporary) / "snapshot"
        snapshot.mkdir()
        reference, _ = _copy_context_closure(example.resolve(), context_path, snapshot)
        reference_path = Path(temporary) / "context-ref.yaml"
        reference_path.write_text(yaml.safe_dump(reference, sort_keys=False))
        completed = subprocess.run(
            [sys.executable, "-c", "from chrona.app.cli import main; main()", "render-review",
             "--context-reference", str(reference_path), "--snapshot-root", str(snapshot),
             "--store-identity", reference["store"]["identity"], "--reject-unused-closure-inputs",
             "--output", str(Path(temporary) / "review.svg")],
            check=False, text=True, capture_output=True)
    pinned = KNOWN.get(slide) or []
    if not completed.returncode:
        assert not pinned, f"{slide} now reads every input: remove it from known_unused.yaml"
        return
    unused = [kind for kind in pinned if kind in completed.stdout]
    if "E_CLOSURE_INPUT_UNUSED" in completed.stdout and len(unused) == len(pinned) and pinned:
        pytest.xfail(f"{slide} drops {', '.join(pinned)}")
    raise AssertionError(completed.stdout.strip() or completed.stderr.strip())
