"""The render use case is callable with a closure, without a command line."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from chrona.presentation.model.closure import resolve_render_context
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.usecases.render_review import (
    RenderFailed, RenderRequest, render_review,
)
from tools.materialize_example import _copy_context_closure

ROOT = Path(__file__).resolve().parents[4]
EXAMPLE = ROOT / "examples/halcyon-1"


def _closure(temporary: Path):
    snapshot = temporary / "snapshot"
    snapshot.mkdir()
    reference, _ = _copy_context_closure(EXAMPLE.resolve(), EXAMPLE / "contexts/02-programme-board.yaml", snapshot)
    reader = LocalSnapshotReader(snapshot, reference["store"]["identity"])
    context, resources = resolve_render_context(reference, reader)
    return context, resources, snapshot


def test_render_review_renders_a_closure_without_the_cli():
    with tempfile.TemporaryDirectory() as temporary:
        context, resources, snapshot = _closure(Path(temporary))
        rendered = render_review(RenderRequest(context, resources, snapshot))
    assert rendered.svg == (EXAMPLE / "generated/02-programme-board.svg").read_text()
    assert rendered.surface.primitives
    assert {"project", "view", "layout-profile"} <= rendered.read_inputs


def test_render_review_reports_every_closure_input_it_never_read():
    """The Summary profile this Context declares is still dropped; see #86."""
    with tempfile.TemporaryDirectory() as temporary:
        context, resources, snapshot = _closure(Path(temporary))
        assert any(item.kind == "summary-profile" for item in resources)
        permissive = render_review(RenderRequest(context, resources, snapshot))
        assert "summary-profile" not in permissive.read_inputs
        with pytest.raises(RenderFailed) as failure:
            render_review(RenderRequest(context, resources, snapshot, require_all_inputs_read=True))
    assert failure.value.code == "E_CLOSURE_INPUT_UNUSED"
    assert "summary-profile" in failure.value.message


def test_render_review_rejects_an_incomplete_closure():
    request = RenderRequest({"body": {}, "resolvedTheme": None}, (), Path("."))
    with pytest.raises(RenderFailed) as failure:
        render_review(request)
    assert failure.value.code == "E_CLOSURE_REQUIRED"
    assert failure.value.component == "closure"


def test_render_review_is_deterministic_for_one_closure():
    with tempfile.TemporaryDirectory() as temporary:
        context, resources, snapshot = _closure(Path(temporary))
        first = render_review(RenderRequest(context, resources, snapshot))
        second = render_review(RenderRequest(context, resources, snapshot))
    assert first.svg == second.svg


def test_render_review_reports_a_theme_without_a_text_family():
    with tempfile.TemporaryDirectory() as temporary:
        context, resources, snapshot = _closure(Path(temporary))
        context = dict(context)
        context["resolvedTheme"] = yaml.safe_load(yaml.safe_dump(context["resolvedTheme"]))
        context["resolvedTheme"]["body"]["roles"]["text"].pop("fontFamily")
        with pytest.raises(RenderFailed) as failure:
            render_review(RenderRequest(context, resources, snapshot))
    assert failure.value.code == "E_THEME_ROLE_REQUIRED"
    assert failure.value.component == "theme"
