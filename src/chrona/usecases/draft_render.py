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
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal

from chrona.core.ports import RenderArtifact, SnapshotReader
from chrona.core.validation import load_yaml
from chrona.extensions.profiles import resolve_local_extension_manifests
from chrona.presentation.contracts import TypesetterIdentity
from chrona.presentation.model.closure import DEFAULT_DRAFT_VIEWPORT, ClosureError, resolve_draft_render
from chrona.presentation.model.info_diagnostics import (
    RelationHintReceipt, RelationHintSummary,
    PaintOmission, ScaleValuesFolded, SuppressedPlotLabels, DeadlineCaptionsDropped, RelationRoutingSummary, RelationSearchBudgetHit,
    RelationResolutionInfo, RelationResolutionSummary,
    RelationPolicySupersession, UnboundFieldRole, FieldGroupingSummariesOmitted, BaselineObjectsRemoved, FontGlyphFallback,
    ForecastInfo,
)
from chrona.presentation.model.render_progress import RenderProgress
from chrona.resources import default_preset_resource, default_preset_root
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.diagnostic_messages import collapse_warnings
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
    style: str | Path | None = None
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
    relations: Literal["none", "semantic"] | None = None
    progress: RenderProgress | None = field(default=None, compare=False, repr=False)
    previous_scene: str | Path | None = None
    snapshot: str | Path | None = None
    forecast: bool = False
    package_reader: SnapshotReader | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class DraftRenderResult:
    rendered: RenderedReview
    notes: tuple[dict[str, Any], ...] = ()
    """Warnings about the request itself (an input the chosen View does not draw); they never change the artifact."""

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


_TYPESETTER_DEFAULTS = {"typst": ("typst", "chrona-typst/v0.1"), "tikz": ("tectonic", "chrona-tikz/v0.1")}


def typesetter_identity(
    engine: str | None, version: str | None, adapter_grammar: str | None, target_kind: str,
) -> TypesetterIdentity | None:
    """Engine and adapter grammar default from the target; an absent version stays absent (unspecified) (#1609)."""
    default = _TYPESETTER_DEFAULTS.get(target_kind)
    if default is None:
        if any((engine, version, adapter_grammar)):
            raise StableFailure(
                "E_RENDER_TYPESETTER_DESCRIPTOR",
                "typesetter descriptor is valid only with --format typst or tikz",
                "cli", "/typesetter", 2,
            )
        return None
    return TypesetterIdentity(engine or default[0], version or None,
                              adapter_grammar or default[1])


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
                previous_scene_path=_optional_path(request.previous_scene),
                snapshot_project_path=_optional_path(request.snapshot),
                forecast=request.forecast,
                package_reader=request.package_reader,
                preset_path=preset_path if preset_path is not None else Path(str(default)),
                preset_root=None if preset_path is not None else Path(str(default_preset_root())),
                view_path=_optional_path(request.view), theme_path=_optional_path(request.theme),
                style_path=_optional_path(request.style),
                scheme_path=_optional_path(request.scheme), layout_path=_optional_path(request.layout),
                actual_path=_optional_path(request.actual),
                summary_path=_optional_path(request.summary),
                detail_path=_optional_path(request.detail),
                icon_catalog_paths=tuple(Path(path) for path in request.icon_catalogs),
                font_metrics_path=_optional_path(request.font_metrics),
                system_fonts=request.system_fonts,
                viewport=parse_viewport(request.viewport), locale=request.locale, target_kind=request.target_kind,
                visual_profile=request.visual_profile,
                relations=request.relations,
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
            preset_visual_profile_fallback=closure.preset_visual_profile_fallback,
            progress=request.progress,
            **_draft_extensions(request),
        ))
    finally:
        if owned_tempdir is not None:
            owned_tempdir.cleanup()
    return DraftRenderResult(rendered, _typesetter_version_notes(request) + _undrawn_input_notes(request, closure.closure))


def _draft_extensions(request: DraftRenderRequest) -> dict[str, Any]:
    """Resolve each source Project's ``path`` extensions beside its own file (#1682).

    The primary and the Snapshot Project keep separate manifest sets; a failure to resolve either is reported.
    """
    resolved: dict[str, Any] = {}
    failures: list[Any] = []
    for key, path in (("extension_manifests", request.project), ("snapshot_extension_manifests", request.snapshot)):
        if path is None:
            continue
        project = load_yaml(Path(path))
        if not isinstance(project, dict) or not isinstance(project.get("extensions"), list):
            continue
        manifests, problems = resolve_local_extension_manifests(project, Path(path).parent)
        resolved[key] = manifests
        failures.extend(problems if key == "extension_manifests" else
                        [replace(item, path=f"/snapshot{item.path}") for item in problems])
    return {**resolved, "extension_diagnostics": tuple(failures)} if resolved else {}


def _typesetter_version_notes(request: DraftRenderRequest) -> tuple[dict[str, Any], ...]:
    """Say so when a typeset target is written without an engine version (#1609)."""
    if request.target_kind not in _TYPESETTER_DEFAULTS or request.typesetter_version:
        return ()
    return ({"code": "I_RENDER_TYPESETTER_VERSION_UNSPECIFIED", "severity": "info", "input": "--typesetter-version",
             "message": "no --typesetter-version was given; the typesetter version is unspecified in the render context"},)


def _undrawn_input_notes(request: DraftRenderRequest, closure: Any) -> tuple[dict[str, Any], ...]:
    """Warn when `--snapshot` was supplied but the chosen View does not draw a snapshot baseline (#1585)."""
    # Forecast mode explicitly retains a supplied Snapshot as its own baseline
    # ghost, independently of the ordinary View comparison baseline.
    if not request.snapshot or request.forecast:
        return ()
    comparison = closure.view.view.comparison
    if comparison.baseline == "snapshot" and comparison.baseline_marks in {"ghost", "ghost-when-changed"}:
        return ()
    return ({"code": "W_SNAPSHOT_NOT_DRAWN", "severity": "warning", "input": "--snapshot",
             "message": f"--snapshot {request.snapshot} was read but the chosen View draws no snapshot baseline "
                        "(its comparison.baseline is not 'snapshot' with baselineMarks ghost); the render shows no baseline. "
                        "Use a preset or View that draws one, for example --preset target-b"},)


def warning_payloads(rendered: RenderedReview) -> list[dict[str, Any]]:
    """The render's warning and info records, in the order an adapter reports them.

    Warnings with the same code and cause are one row (``count``, ``occurrences``); every record has a
    ``message`` (#782). The Scene keeps every per-placement fact.
    """
    payloads: list[dict[str, Any]] = collapse_warnings([warning.payload for warning in rendered.warning_records])
    fallback = getattr(rendered, "preset_visual_profile_fallback", None)
    if fallback is not None:
        payloads.append({"code": fallback.code, "severity": "info", "presetId": fallback.preset_id,
                         "preferredProfile": fallback.preferred_profile, "selectedProfile": fallback.selected_profile,
                         "targetKind": fallback.target_kind,
                         "message": f"preset {fallback.preset_id} prefers {fallback.preferred_profile}; "
                                    f"selected {fallback.selected_profile} for {fallback.target_kind}"})
    for info in rendered.info_diagnostics:
        if isinstance(info, FontGlyphFallback):
            payloads.append({"code": info.code, "severity": "info", **info.payload(),
                             "message": f"{info.requested_family} uses {info.fallback_family} for {info.count} {info.script} glyphs "
                                        f"(first U+{info.codepoint:04X})"})
        elif isinstance(info, ForecastInfo):
            payloads.append({"code": info.code, "severity": "info", **info.payload()})
        elif isinstance(info, UnboundFieldRole):
            payloads.append({"code": info.code, "severity": "info", **info.payload(),
                "message": f"Project does not declare field role {info.role!r}; "
                           f"{info.count} View declarations use their fallback or are omitted"})
        elif isinstance(info, BaselineObjectsRemoved):
            payloads.append({"code": info.code, "severity": "info", **info.payload(),
                "message": f"{len(info.objects)} baseline objects have no current counterpart and no ghost is shown: "
                           + ", ".join(f"{t} ({i})" for i, t in info.objects)})
        elif isinstance(info, FieldGroupingSummariesOmitted):
            payloads.append({"code": info.code, "severity": "info", **info.payload(),
                "message": f"{info.count} selected group summaries omitted from field-role grouping"})
        elif isinstance(info, (RelationHintReceipt, RelationHintSummary)):
            payloads.append({"code": info.code, "severity": "info", **info.payload(),
                "message": (f"Prior route {info.relation_id}: {info.disposition} ({info.reason})"
                            if isinstance(info, RelationHintReceipt) else
                            f"Previous Scene hints evaluated for {len(info.receipts)} relations")})
        elif isinstance(info, RelationPolicySupersession):
            payloads.append({"code": info.code, "severity": "info", **info.payload(),
                "message": f"Layout relationRouting.unroutable={info.layout_mode} supersedes declared "
                           f"View visibility.relations.overflow={info.view_overflow} for spatial routing"})
        elif isinstance(info, (RelationResolutionInfo, RelationResolutionSummary)):
            payloads.append({"code": info.code, "severity": "info", **info.payload(),
                "message": (f"Relation {info.relation_id} uses {info.stage.value} resolution; "
                            f"critical={info.critical}; not a safety/completeness claim"
                            if isinstance(info, RelationResolutionInfo) else
                            f"{sum(count for _, count in info.stage_counts)} relations on {info.surface_id} use recovery")})
        elif isinstance(info, RelationSearchBudgetHit):
            payloads.append({"code": info.code, "severity": "info", **info.payload(),
                "message": f"Search budget reached for {info.relation_id} in {info.pass_name}; "
                           "not proof that no safe route exists"})
        elif isinstance(info, RelationRoutingSummary):
            payloads.append({"code": info.code, "severity": "info", "surfaceId": info.surface_id,
                "relationInstances": info.relation_instances, "shapeSettled": info.shape_settled,
                "fallbackSearch": info.fallback_search,
                "message": f"{info.shape_settled} relations on {info.surface_id} settled without search; "
                           f"{info.fallback_search} used fallback search"})
        elif isinstance(info, (SuppressedPlotLabels, DeadlineCaptionsDropped)):
            label_kind = "deadline captions" if isinstance(info, DeadlineCaptionsDropped) else "plot labels"
            payloads.append({"code": info.code, "severity": "info", "surfaceId": info.surface_id,
                             "count": info.count,
                             "message": f"{info.count} {label_kind} on {info.surface_id} were left out because "
                                        "they do not fit"})
        elif isinstance(info, ScaleValuesFolded):
            payloads.append({"code": info.code, "severity": "info", **info.payload(),
                "message": f"{len(info.values)} values of {info.source_field} exceed the {info.palette_size} distinct "
                           f"colors of scale {info.scale_id}; they share one neutral Other entry"})
        elif isinstance(info, PaintOmission):
            message = (f"{info.treatment} on {info.role} was omitted by {info.visual_profile}; "
                       + (f"use {info.paintable_profile} to paint it"
                          if info.paintable_profile else f"no {info.target_kind} profile can paint it"))
            payloads.append({"code": info.code, "severity": "info", "role": info.role,
                             "treatment": info.treatment, "sourceRef": info.source_ref,
                             "visualProfile": info.visual_profile,
                             "paintableProfile": info.paintable_profile, "message": message})
    return payloads
