"""One slide's Render Context as its example manifest selects it (Spec 40 section 7, #415).

A deck may compose a slide's Context from `contextDefaults` and `contextOverrides`, so a test
must not assume that every slide has an authored file under `contexts/`. These helpers reuse the
one application composer; they never merge Context bodies themselves.
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

from chrona.usecases.deck_context import SelectedDeckContext, resolve_deck_context


def slide_context(example: Path, slide_id: str) -> SelectedDeckContext:
    """The selected (explicit or composed) Context source of ``slide_id``."""
    return resolve_deck_context(example / "manifest.yaml", slide_id)


def context_document(example: Path, slide_id: str) -> dict[str, Any]:
    """A mutable copy of the completed Context document of ``slide_id``."""
    return copy.deepcopy(dict(slide_context(example, slide_id).document))


def write_explicit_context(example: Path, slide_id: str, relative: str) -> Path:
    """Make ``slide_id`` of a writable example copy select an explicit Context file.

    The file holds the slide's completed Context, so a test can edit it in place; the copy's
    manifest is rewritten to select that file. Returns the file's path.
    """
    selected = slide_context(example, slide_id)
    path = example / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if selected.source_path is None or selected.source_path.resolve() != path.resolve():
        path.write_bytes(selected.payload)
    manifest_path = example / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    for slide in manifest["slides"]:
        if slide["id"] == slide_id:
            slide.pop("contextOverrides", None)
            slide["context"] = relative
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path
