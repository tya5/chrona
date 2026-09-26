#!/usr/bin/env python3
"""Fail release conformance on perceptibility errors in the real default Draft."""
from __future__ import annotations

from pathlib import Path

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility
from chrona.presentation.scene.serialization import scene_document
from chrona.resources import default_preset_resource, default_preset_root
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderRequest, render_review


ROOT = Path(__file__).resolve().parents[1]


def starter_scene_document() -> dict:
    """Render the packaged default, not a simplified Scene-only approximation."""
    draft = resolve_draft_render(
        project_path=ROOT / "examples/halcyon-1/project.yaml",
        preset_path=Path(str(default_preset_resource())),
        preset_root=Path(str(default_preset_root())),
    )
    rendered = render_review(RenderRequest(
        draft.closure, draft.asset_root, ReferenceScheduler(),
        renderer=V05SvgRenderer(), asset_root=draft.asset_root,
        draft_auto_block=draft.auto_block,
    ))
    return scene_document(rendered.scene)


def starter_errors(document: dict) -> tuple:
    """Use #446's sole evaluator and its existing error severity contract."""
    return tuple(item for item in evaluate_scene_perceptibility(document)
                 if item.severity == "error")


def main() -> int:
    errors = starter_errors(starter_scene_document())
    for item in errors:
        print(f"ERROR {item.code} {item.scene_path} primitives={','.join(item.primitive_ids)}")
    print(f"Starter perceptibility: {'FAIL' if errors else 'PASS'} ({len(errors)} errors)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
