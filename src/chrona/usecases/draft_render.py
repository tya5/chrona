"""Render one raw Draft Project into a review surface.

This is the draft-render pipeline an adapter used to carry itself: resolve a builtin
preset name into a process-local copy, build the typed in-memory closure from the
declared inputs, rewrite a stale-preset error into its next action, and run the render
use case. A caller supplies a ``DraftRenderRequest`` and receives the rendered artifact;
nothing here reads arguments, writes a file, prints or exits. Failures are raised as the
library's own typed exceptions (``StableFailure``, ``ClosureError``,
``PresentationIngressRejected``, ``RenderRejected``, ``RenderFailed``, ``OSError``,
``yaml.YAMLError``) which ``usecases.failure_report.report_failure`` maps to diagnostics.
"""
from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chrona.core.ports import RenderArtifact
from chrona.presentation.contracts import TypesetterIdentity
from chrona.presentation.model.closure import DEFAULT_DRAFT_VIEWPORT, ClosureError, resolve_draft_render
from chrona.presentation.model.info_diagnostics import PaintOmission, SuppressedPlotLabels
from chrona.resources import default_preset_resource, default_preset_root
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.failure_report import StableFailure
from chrona.usecases.preset_library import copy_builtin_preset, is_builtin_preset_id
from chrona.usecases.render_review import RenderRequest, RenderedReview, render_review

DEFAULT_VIEWPORT = f"{DEFAULT_DRAFT_VIEWPORT[0]}xauto"


@dataclass(frozen=True)
class DraftRenderRequest:
    """The declared inputs of one draft render; every path is a local file path."""

    project: str | Path
    target_kind: str
    preset: str | None = None
    view: str | Path | None = None
    theme: str | Path | None = None
    scheme: str | Path | None = None
    layout: str | Path | None = None
    actual: str | Path | None = None
    summary: str | Path | None = None
    detail: str | Path | None = None
    icon_catalogs: tuple[str | Path, ...] = ()
    font_metrics: str | Path | None = None
    system_fonts: bool = False
    viewport: str = DEFAULT_VIEWPORT
    locale: str = "en-US"
    visual_profile: str | None = None
    typesetter_engine: str | None = None
    typesetter_version: str | None = None
    typesetter_adapter_grammar: str | None = None


@dataclass(frozen=True)
class DraftRenderResult:
    rendered: RenderedReview

    @property
    def artifact(self) -> RenderArtifact:
        return self.rendered.artifact


def parse_viewport(value: str) -> tuple[int, int | None]:
    parts = value.lower().split("x")
    if len(parts) != 2:
        raise StableFailure("E_COMMAND_VIEWPORT", "viewport must be WIDTHxHEIGHT", "cli", "/viewport", 2)
    try:
        width = int(parts[0])
        height = None if parts[1] == "auto" else int(parts[1])
    except ValueError as error:
        raise StableFailure("E_COMMAND_VIEWPORT", "viewport must be WIDTHxHEIGHT", "cli", "/viewport", 2) from error
    if width <= 0 or (height is not None and height <= 0):
        raise StableFailure("E_COMMAND_VIEWPORT", "viewport dimensions must be positive or block size may be auto", "cli", "/viewport", 2)
    return width, height


def typesetter_identity(
    engine: str | None, version: str | None, adapter_grammar: str | None, target_kind: str,
) -> TypesetterIdentity | None:
    values = (engine, version, adapter_grammar)
    is_typeset = target_kind in {"typst", "tikz"}
    if is_typeset and not all(values):
        raise StableFailure(
            "E_RENDER_TYPESETTER_DESCRIPTOR",
            "typeset Draft targets require --typesetter-engine, --typesetter-version, and --typesetter-adapter-grammar",
            "cli", "/typesetter", 2,
        )
    if not is_typeset and any(values):
        raise StableFailure(
            "E_RENDER_TYPESETTER_DESCRIPTOR",
            "typesetter descriptor is valid only with --format typst or tikz",
            "cli", "/typesetter", 2,
        )
    return TypesetterIdentity(*values) if is_typeset else None


def looks_like_preset_path(value: str) -> bool:
    """A preset value naming a file always contains a separator or a YAML suffix (#429).

    `library.yaml` ids match `^[a-z][a-z0-9-]*$`, which can never collide with either.
    """
    return "/" in value or value.endswith((".yaml", ".yml"))


def resolve_preset_argument(value: str | None) -> tuple[Path | None, tempfile.TemporaryDirectory | None]:
    """Return `(preset_path, owned_tempdir)` for a preset value, resolving a builtin id by name (#429).

    A name is resolved through the exact same `copy_builtin_preset` a user's own
    `chrona preset copy <id>` would run, into a process-local temporary directory,
    so `render --preset <name>` is byte-identical to `preset copy <name>` followed
    by `render --preset <path>` by construction rather than by a second code path.
    The caller owns `owned_tempdir` and must `.cleanup()` it once rendering is done
    (a plain try/finally, not `@contextmanager`: `StableFailure` is a frozen dataclass,
    and contextlib's generator-based `__exit__` cannot re-raise a frozen exception
    through `gen.throw` -- it tries to stamp `__traceback__` on it and fails).
    """
    if not value:
        return None, None
    if looks_like_preset_path(value):
        return Path(value), None
    tmp = tempfile.TemporaryDirectory(prefix="chrona-preset-")
    try:
        return copy_builtin_preset(value, Path(tmp.name) / "preset"), tmp
    except BaseException:
        tmp.cleanup()
        raise


def _optional_path(value: str | Path | None) -> Path | None:
    return Path(value) if value else None


def render_draft(request: DraftRenderRequest) -> DraftRenderResult:
    preset_path, owned_tempdir = resolve_preset_argument(request.preset)
    try:
        default = default_preset_resource() if preset_path is None else None
        try:
            closure = resolve_draft_render(
                project_path=Path(request.project),
                preset_path=preset_path if preset_path is not None else Path(str(default)),
                preset_root=None if preset_path is not None else Path(str(default_preset_root())),
                view_path=_optional_path(request.view), theme_path=_optional_path(request.theme),
                scheme_path=_optional_path(request.scheme), layout_path=_optional_path(request.layout),
                actual_path=_optional_path(request.actual),
                summary_path=_optional_path(request.summary),
                detail_path=_optional_path(request.detail),
                icon_catalog_paths=tuple(Path(path) for path in request.icon_catalogs),
                font_metrics_path=_optional_path(request.font_metrics),
                system_fonts=request.system_fonts,
                viewport=parse_viewport(request.viewport), locale=request.locale, target_kind=request.target_kind,
                visual_profile=request.visual_profile,
                typesetter=typesetter_identity(
                    request.typesetter_engine, request.typesetter_version,
                    request.typesetter_adapter_grammar, request.target_kind,
                ),
            )
        except ClosureError as error:
            preset_id = error.declaring_preset_id
            if (error.diagnostic_id == "E_RESOURCE_VERSION_UNSUPPORTED" and owned_tempdir is None
                    and preset_path is not None and preset_id is not None
                    and preset_id.startswith("chrona-builtin-")
                    and is_builtin_preset_id(preset_id.removeprefix("chrona-builtin-"))):
                catalogue_id = preset_id.removeprefix("chrona-builtin-")
                message = (f"{error.detail}; run chrona preset copy {catalogue_id} --output <new-dir> "
                           "and re-apply your edits")
                raise StableFailure(error.diagnostic_id, message, "closure", error.source_ref) from error
            raise
        rendered = render_review(RenderRequest(
            closure=closure.closure, snapshot_root=Path("."), scheduler=ReferenceScheduler(),
            require_all_inputs_read=False, asset_root=closure.asset_root,
            draft_auto_block=closure.auto_block, draft_font_resolution=closure.font_resolution,
        ))
    finally:
        if owned_tempdir is not None:
            owned_tempdir.cleanup()
    return DraftRenderResult(rendered)


def warning_payloads(rendered: RenderedReview) -> list[dict[str, Any]]:
    """The render's warning and info records, in the order an adapter reports them."""
    payloads: list[dict[str, Any]] = [warning.payload for warning in rendered.warning_records]
    for info in rendered.info_diagnostics:
        if isinstance(info, SuppressedPlotLabels):
            payloads.append({"code": info.code, "severity": "info", "surfaceId": info.surface_id,
                             "count": info.count})
        elif isinstance(info, PaintOmission):
            message = (f"{info.treatment} on {info.role} was omitted by {info.visual_profile}; "
                       + (f"use {info.paintable_profile} to paint it"
                          if info.paintable_profile else f"no {info.target_kind} profile can paint it"))
            payloads.append({"code": info.code, "severity": "info", "role": info.role,
                             "treatment": info.treatment, "sourceRef": info.source_ref,
                             "visualProfile": info.visual_profile,
                             "paintableProfile": info.paintable_profile, "message": message})
    return payloads
