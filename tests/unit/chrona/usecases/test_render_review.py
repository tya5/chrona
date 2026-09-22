"""The render use case is callable with a closure, without a command line."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from chrona.presentation.model.closure import RenderClosure, resolve_render_context
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.usecases.render_review import (
    RenderRequest, render_review,
)
from tools.materialize_example import _copy_context_closure

ROOT = Path(__file__).resolve().parents[4]
EXAMPLE = ROOT / "examples/halcyon-1"


def _closure(temporary: Path):
    snapshot = temporary / "snapshot"
    snapshot.mkdir()
    reference, _ = _copy_context_closure(EXAMPLE.resolve(), EXAMPLE / "contexts/02-programme-board.yaml", snapshot)
    reader = LocalSnapshotReader(snapshot, reference["store"]["identity"])
    return resolve_render_context(reference, reader), snapshot


def _request(closure, snapshot, **kwargs):
    return RenderRequest(closure, snapshot, ReferenceScheduler(), V05SvgRenderer(), **kwargs)


def test_render_review_renders_a_closure_without_the_cli():
    with tempfile.TemporaryDirectory() as temporary:
        closure, snapshot = _closure(Path(temporary))
        rendered = render_review(_request(closure, snapshot))
    assert rendered.svg == (EXAMPLE / "generated/02-programme-board.svg").read_text()
    assert rendered.surface.primitives
    assert {"project", "view", "layout-profile"} <= rendered.read_inputs


def test_render_review_reads_a_bound_summary_profile():
    with tempfile.TemporaryDirectory() as temporary:
        closure, snapshot = _closure(Path(temporary))
        assert closure.resource("summary-profile") is not None
        rendered = render_review(_request(closure, snapshot, require_all_inputs_read=True))
    assert "summary-profile" in rendered.read_inputs


def test_render_review_rejects_an_incomplete_closure():
    # An incomplete closure cannot be fabricated from arbitrary mappings.
    assert RenderRequest.__dataclass_fields__["closure"].type == "RenderClosure"


def test_render_review_is_deterministic_for_one_closure():
    with tempfile.TemporaryDirectory() as temporary:
        closure, snapshot = _closure(Path(temporary))
        first = render_review(_request(closure, snapshot))
        second = render_review(_request(closure, snapshot))
    assert first.svg == second.svg


def test_render_review_reports_a_theme_without_a_text_family():
    with tempfile.TemporaryDirectory() as temporary:
        closure, _snapshot = _closure(Path(temporary))
        with pytest.raises(TypeError):
            closure.resolved_theme.body["roles"]["text"].pop("fontFamily")
