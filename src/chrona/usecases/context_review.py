"""Resolve an immutable Render Context from a Store and render it: the two steps both front ends share (#812).

``chrona render-review`` and the agent tool ``render_review`` read a Context reference, resolve its closure through a
reader of the Store the reference names, and render it through ``usecases.render_review``. A tool may reach the
presentation layer only through a use case, so the two steps are named here and the command line calls them too:
a disagreement between the two front ends is a defect in these functions.

Nothing here reads a file, opens a Store, writes or prints; the caller supplies the decoded reference and a reader.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from chrona.core.ports import SnapshotReader
from chrona.presentation.model.closure import RenderClosure, resolve_render_context
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderedReview, RenderRequest, render_review


def resolve_context_closure(reference: dict[str, Any], reader: SnapshotReader) -> RenderClosure:
    """The closure of the immutable Render Context ``reference`` names, every input read and verified through ``reader``."""
    return resolve_render_context(reference, reader)


def render_context_closure(
    closure: RenderClosure, snapshot_root: Path, *, reject_unused_inputs: bool = False,
) -> RenderedReview:
    """Render one resolved Context closure; ``reject_unused_inputs`` is ``--reject-unused-closure-inputs``."""
    return render_review(RenderRequest(
        closure=closure, snapshot_root=snapshot_root, scheduler=ReferenceScheduler(),
        require_all_inputs_read=reject_unused_inputs,
    ))
