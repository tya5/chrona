"""The two steps ``chrona render-review`` and the ``render_review`` tool share (#812)."""
from __future__ import annotations

from pathlib import Path

import pytest

from chrona.core.ports import SnapshotReadError
from chrona.operational.store_config import load_store_config
from chrona.operational.store_reads import load_reference, snapshot_reader_for
from chrona.usecases.context_review import render_context_closure, resolve_context_closure
from chrona.usecases.local_authoring import initialize_project

REFERENCE = """id: halcyon-1-01-mission-brief
kind: render-context
store:
  provider: local
  identity: halcyon-1-example
address: contexts/01-mission-brief.yaml
revision:
  token: example-v4
"""
KEY = ("local", "halcyon-1-example")


@pytest.fixture(scope="module")
def corpus(tmp_path_factory) -> Path:
    return initialize_project(tmp_path_factory.mktemp("corpus") / "halcyon", example="halcyon-1")


def _reference(corpus: Path) -> dict:
    path = corpus / "context-reference.yaml"
    path.write_text(REFERENCE, encoding="utf-8")
    return load_reference(path)


def test_a_context_in_a_store_resolves_and_renders_to_an_svg(corpus):
    reference = _reference(corpus)
    reader, root = snapshot_reader_for(load_store_config(str(corpus / ".chrona" / "store.yaml")), reference)

    closure = resolve_context_closure(reference, reader)
    rendered = render_context_closure(closure, root)

    assert closure.context.target.kind == "svg"
    assert rendered.artifact.content.startswith(b"<svg")
    assert render_context_closure(closure, root).artifact.content == rendered.artifact.content


def test_a_required_store_refuses_the_examples_unpinned_inner_references(corpus):
    reference = _reference(corpus)
    config = load_store_config(str(corpus / ".chrona" / "store.yaml"))
    config.integrity[KEY] = "required"
    reader, _ = snapshot_reader_for(config, reference)

    with pytest.raises(Exception) as raised:
        resolve_context_closure(reference, reader)

    assert isinstance(raised.value, SnapshotReadError) or "E_CONTENT_IDENTITY" in str(raised.value)
