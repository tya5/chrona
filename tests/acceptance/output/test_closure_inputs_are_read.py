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
KNOWN = yaml.safe_load((Path(__file__).parent / "known_unused.yaml").read_text(encoding="utf-8")) or {}


def _slides():
    for manifest_path in sorted(ROOT.glob("examples/*/manifest.yaml")):
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
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
    expected = KNOWN.get(slide)
    if not completed.returncode:
        assert expected is None, f"{slide} now reads every input: remove it from known_unused.yaml"
        return
    prefix = "closure inputs loaded but never read: "
    actual = completed.stdout.split(prefix, 1)[1].split('"', 1)[0].strip().split(", ") if prefix in completed.stdout else None
    assert actual is not None, completed.stdout.strip() or completed.stderr.strip()
    assert actual == expected, f"{slide} unused-input fingerprint changed: {actual!r}"
    pytest.xfail(f"{slide} drops {', '.join(actual)}")
