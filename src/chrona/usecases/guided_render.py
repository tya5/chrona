"""Render one guided authoring workspace through the ordinary review pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from chrona.core.ports import RenderArtifact, SnapshotReader
from chrona.presentation.contracts import TypesetterIdentity
from chrona.presentation.model.closure import (
    ClosureError, GuidedAuthoringProvenance, resolve_guided_draft_render,
)
from chrona.presentation.model.render_progress import RenderProgress
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.draft_render import parse_viewport
from chrona.usecases.render_review import RenderRequest, RenderedReview, render_review


@dataclass(frozen=True)
class WorkspaceRenderRequest:
    """Inputs accepted by the shared CLI and MCP guided-render adapter."""

    workspace: Path
    target_kind: str
    viewport: str | None = None
    locale: str = "en-US"
    visual_profile: str | None = None
    typesetter: TypesetterIdentity | None = None
    forecast: bool = False
    progress: RenderProgress | None = field(default=None, compare=False, repr=False)
    package_reader: SnapshotReader | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class WorkspaceRenderResult:
    rendered: RenderedReview
    provenance: GuidedAuthoringProvenance

    @property
    def artifact(self) -> RenderArtifact:
        return self.rendered.artifact


def render_workspace(request: WorkspaceRenderRequest) -> WorkspaceRenderResult:
    """Resolve and render one workspace; adapters do not reimplement Draft setup."""
    draft = resolve_guided_draft_render(
        workspace_path=Path(request.workspace), viewport=parse_viewport(request.viewport),
        locale=request.locale, target_kind=request.target_kind, visual_profile=request.visual_profile,
        typesetter=request.typesetter, forecast=request.forecast, package_reader=request.package_reader,
    )
    provenance = draft.closure.guided_provenance
    if provenance is None:
        raise ClosureError("E_AUTHORING_PROVENANCE", detail="guided closure provenance is required")
    rendered = render_review(RenderRequest(
        closure=draft.closure, snapshot_root=Path("."), scheduler=ReferenceScheduler(),
        asset_root=draft.asset_root, draft_auto_block=draft.auto_block,
        draft_font_resolution=draft.font_resolution,
        preset_visual_profile_fallback=draft.preset_visual_profile_fallback,
        progress=request.progress,
    ))
    return WorkspaceRenderResult(rendered, provenance)
