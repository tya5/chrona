"""A Render Context input that the render never reads is an authored intent lost.

The check lives in ``render_review`` and is exposed by the CLI through
``--reject-unused-closure-inputs``. These tests exercise it with the verified
materializer overlay over the shipped examples. `known_unused.yaml` pins the inputs
that are dropped today, on the same rules as the output-property gate: a pinned input
that is still dropped is reported, one that starts being read fails so its pin goes.
"""
from __future__ import annotations

import tempfile
from importlib.util import find_spec
from pathlib import Path

import pytest
import yaml

from tools.materialize_example import _copy_context_closure
from chrona.presentation.model.closure import resolve_render_context
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.materialize import _OverlayBuilder
from chrona.usecases.render_review import RenderFailed, RenderRequest, render_review

ROOT = Path(__file__).resolve().parents[3]
KNOWN = yaml.safe_load((Path(__file__).parent / "known_unused.yaml").read_text(encoding="utf-8")) or {}


def _slides():
    for manifest_path in sorted(ROOT.glob("examples/*/manifest.yaml")):
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        example = manifest_path.parent
        for slide in manifest.get("slides", ()):
            identity = f"{example.name}/{slide['id']}"
            marks = (pytest.mark.skip(reason="requires the optional local CJK font provider")
                     if example.name == "controller-z-ja" and find_spec("chrona_fonts_noto_cjk") is None else ())
            yield pytest.param(identity, example, example / str(slide.get("context", manifest["context"])),
                               id=identity, marks=marks)


@pytest.mark.parametrize("slide,example,context_path", list(_slides()))
def test_every_declared_closure_input_is_read(slide, example, context_path):
    with tempfile.TemporaryDirectory() as temporary:
        snapshot = Path(temporary) / "snapshot"
        snapshot.mkdir()
        decoded_catalogs = {}
        overlay_builder = _OverlayBuilder(Path(temporary))
        reference, _ = _copy_context_closure(example.resolve(), context_path, snapshot,
                                             decoded_catalogs=decoded_catalogs,
                                             overlay_builder=overlay_builder)
        overlay = overlay_builder.finish()
        closure = resolve_render_context(reference, overlay, decoded_resources=decoded_catalogs)
        try:
            render_review(RenderRequest(closure, snapshot, ReferenceScheduler(),
                                        require_all_inputs_read=True, asset_resolver=overlay))
            failure = None
        except RenderFailed as error:
            failure = error
    expected = KNOWN.get(slide)
    if failure is None:
        assert expected is None, f"{slide} now reads every input: remove it from known_unused.yaml"
        return
    prefix = "closure inputs loaded but never read: "
    actual = failure.message.split(prefix, 1)[1].strip().split(", ") if prefix in failure.message else None
    assert failure.code == "E_CLOSURE_INPUT_UNUSED" and actual is not None, failure
    assert actual == expected, f"{slide} unused-input fingerprint changed: {actual!r}"
    pytest.xfail(f"{slide} drops {', '.join(actual)}")
