"""Immutable Render Context closure resolution before any rendering adapter runs."""
from __future__ import annotations

from difflib import get_close_matches
from dataclasses import dataclass
from hashlib import sha256
from importlib.metadata import version
import math
from pathlib import Path
import re
from typing import Any, Mapping

import jsonschema  # Kept as the closure module's validator seam for snapshot tests.
import yaml


from chrona.presentation.color_scheme import ColorSchemeError, resolve_theme
from chrona.presentation.scene.capabilities import theme_catalog_pattern_consumer
from chrona.presentation.icons import IconNormalizationError, IconPathCommand, NormalizedIconPath, NormalizedVectorIcon, validate_png
from chrona.presentation.contracts import (
    ActualSetContract, AuthoringWorkspaceContract, ClosureIdentity, ContractError, SchemaContractError, IconCatalogContract, IconEntry, IconPath, LayoutProfileContract,
    PresentationPresetContract,
    ProfilePackageContract, ProjectContract, RenderContextContract,
    ResolvedThemeContract, ResourceContract, ReviewDetailProfileContract,
    SnapshotRefContract, SummaryProfileContract, TypesetterIdentity, ViewContract,
    PresentationIngressRejected, PresentationResourceSource, collect_presentation_contracts,
    freeze, parse_contract, validate_icon_catalog_entry, validate_theme_asset_entry, IconRasterSource,
)
from chrona.presentation.model.authoring import AuthoringError, normalize_authoring_workspace
from chrona.presentation.model.theme_inheritance import (
    ThemeInheritanceError, is_derived_theme, resolve_draft_theme, resolve_snapshot_theme,
)
from chrona.presentation.model.theme_references import ThemeReferenceError, resolve_references, uses_references
from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView
from chrona.presentation.fonts.resolution import resolve_theme_font_stacks
from chrona.presentation.fonts.system import DraftFontResolution, SystemFontError, SystemFontResolver, resolve_draft_fonts, resolve_system_font
from chrona.presentation.model.font_metrics import FontMetricsCatalog, FontMetricsError, FontTabularWarning, resolve_font_files, resolve_font_metrics
from chrona.presentation.contracts.resources import (
    RENDER_CONTEXT_VERSION, RENDER_CONTEXT_VERSIONS, FrozenDict, FrozenList, _compact_commands,
)
from chrona.core.ports import SnapshotReadError, SnapshotReader
from chrona.core.store_address import StoreAddressError, check_store_address, resolve_store_address
from chrona.resources import safe_load
from chrona.core.identity import content_identity


class ClosureError(ValueError):
    def __init__(self, diagnostic_id: str, source_ref: str = "/", detail: str | None = None,
                 *, declaring_preset_id: str | None = None):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id
        self.source_ref = source_ref
        self.detail = detail
        self.declaring_preset_id = declaring_preset_id


def _closure_kind_error(scope: str, expected: str, found: object) -> ClosureError:
    return ClosureError("E_CLOSURE_KIND", detail=f"{scope}; expected {expected}; found {type(found).__name__}")


@dataclass(frozen=True)
class ClosureResource:
    kind: str
    id: str
    revision: str
    content_identity: str
    contract: ResourceContract


@dataclass(frozen=True)
class IconAsset:
    """Verified catalog asset bytes; no host path crosses this closure boundary."""

    icon_id: str
    kind: str
    content_identity: str
    viewport: tuple[int, int]
    alternative: str
    payload: NormalizedVectorIcon | bytes

@dataclass(frozen=True)
class RenderClosure:
    context: RenderContextContract
    resources: tuple[ClosureResource, ...]
    resolved_theme: ResolvedThemeContract
    icon_assets: tuple[IconAsset, ...] = ()
    guided_provenance: "GuidedAuthoringProvenance | None" = None

    def resource(self, kind: str) -> ClosureResource | None:
        return next((item for item in self.resources if item.kind == kind), None)

    @staticmethod
    def _kind_error(item: ClosureResource, expected: type[ResourceContract]) -> ClosureError:
        return ClosureError(
            "E_CLOSURE_KIND",
            detail=(f"resource kind={item.kind} id={item.id}; expected contract={expected.__name__}; "
                    f"found contract={type(item.contract).__name__}"),
        )

    @property
    def project(self) -> ProjectContract:
        item = self.resource("project")
        if item is None:
            raise ClosureError("E_CLOSURE_REQUIRED", detail="the closure has no project resource")
        if not isinstance(item.contract, ProjectContract):
            raise self._kind_error(item, ProjectContract)
        return item.contract

    @property
    def view(self) -> ViewContract:
        item = self.resource("view")
        if item is None:
            raise ClosureError("E_CLOSURE_REQUIRED", detail="the closure has no view resource")
        if not isinstance(item.contract, ViewContract):
            raise self._kind_error(item, ViewContract)
        return item.contract

    @property
    def layout_profile(self) -> LayoutProfileContract:
        item = self.resource("layout-profile")
        if item is None:
            raise ClosureError("E_CLOSURE_REQUIRED", detail="the closure has no layout-profile resource")
        if not isinstance(item.contract, LayoutProfileContract):
            raise self._kind_error(item, LayoutProfileContract)
        return item.contract

    def _optional(self, kind: str, expected: type[ResourceContract]) -> ResourceContract | None:
        item = self.resource(kind)
        if item is None:
            return None
        if not isinstance(item.contract, expected):
            raise self._kind_error(item, expected)
        return item.contract

    @property
    def actual_set(self) -> ActualSetContract | None:
        return self._optional("actual-set", ActualSetContract)  # type: ignore[return-value]

    @property
    def summary_profile(self) -> SummaryProfileContract | None:
        return self._optional("summary-profile", SummaryProfileContract)  # type: ignore[return-value]

    @property
    def detail_profile(self) -> ReviewDetailProfileContract | None:
        return self._optional("review-detail-profile", ReviewDetailProfileContract)  # type: ignore[return-value]

    @property
    def snapshot(self) -> SnapshotRefContract | None:
        return self._optional("snapshot-ref", SnapshotRefContract)  # type: ignore[return-value]

    @property
    def snapshot_project(self) -> ProjectContract | None:
        return self._optional("snapshot-project", ProjectContract)  # type: ignore[return-value]

    @property
    def profile_packages(self) -> tuple[ProfilePackageContract, ...]:
        values = tuple(item.contract for item in self.resources if item.kind == "profile-package")
        if not all(isinstance(item, ProfilePackageContract) for item in values):
            item = next(item for item in self.resources if item.kind == "profile-package" and not isinstance(item.contract, ProfilePackageContract))
            raise self._kind_error(item, ProfilePackageContract)
        return values  # type: ignore[return-value]

    @property
    def icon_catalogs(self) -> tuple[IconCatalogContract, ...]:
        """Ordered catalog set closed by the Context, never a global registry."""
        values = tuple(item.contract for item in self.resources if item.kind == "icon-catalog")
        if not all(isinstance(item, IconCatalogContract) for item in values):
            item = next(item for item in self.resources if item.kind == "icon-catalog" and not isinstance(item.contract, IconCatalogContract))
            raise self._kind_error(item, IconCatalogContract)
        return values  # type: ignore[return-value]

    def icon_asset(self, reference: str) -> IconAsset:
        """Resolve one authored ``set:name`` only against this closed Context."""
        if reference.count(":") != 1:
            raise ClosureError("E_ICON_REFERENCE", detail=f"icon reference {reference!r} must be set:name with exactly one colon")
        set_name, name = reference.split(":", 1)
        catalogs = [catalog for catalog in self.icon_catalogs if set_name in {catalog.set_name, *catalog.aliases}]
        if len(catalogs) != 1:
            raise ClosureError("E_ICON_SET_UNKNOWN" if not catalogs else "E_ICON_SET_AMBIGUOUS")
        catalog = catalogs[0]
        canonical = str(catalog.entry_aliases.get(name, name))
        asset_id = f"{catalog.set_name}:{canonical}"
        asset = next((item for item in self.icon_assets if item.icon_id == asset_id), None)
        if asset is None:
            candidates = get_close_matches(name, sorted(({entry.name for entry in catalog.entries} | set(catalog.entry_names)) | set(catalog.entry_aliases)), n=3, cutoff=0.45)
            detail = f"reference={reference}; catalog={catalog.set_name}; candidates={','.join(candidates) or 'none'}"
            raise ClosureError("E_ICON_NAME_UNKNOWN", detail=detail)
        return asset


@dataclass(frozen=True)
class DraftRender:
    """A non-evidence closure and the packaged assets it is allowed to read."""

    closure: RenderClosure
    asset_root: Path
    auto_block: bool = False
    font_resolution: DraftFontResolution | None = None


@dataclass(frozen=True)
class GuidedAuthoringProvenance:
    """Non-Scene provenance for a guided closure."""

    workspace_identity: str
    preset_identity: str
    binding_identity: str
    normalizer_version: str = "chrona/authoring-normalizer/v0.1"


_DRAFT_CAPABILITIES = (
    "accessibleText", "hierarchicalAxis", "marker", "semanticRoles", "sourceMetadata",
    "tableSemantics",
)


DEFAULT_DRAFT_VIEWPORT: tuple[int, int | None] = (1600, None)


def resolve_draft_render(
    *, project_path: Path, view_path: Path | None = None, theme_path: Path | None = None, scheme_path: Path | None = None,
    layout_path: Path | None = None, preset_path: Path | None = None, preset_root: Path | None = None, actual_path: Path | None = None, summary_path: Path | None = None,
    detail_path: Path | None = None, icon_catalog_paths: tuple[Path, ...] = (),
    font_metrics_path: Path | None = None,
    system_fonts: bool = False,
    system_font_resolver: SystemFontResolver | None = None,
    viewport: tuple[int, int | None] = DEFAULT_DRAFT_VIEWPORT,
    locale: str = "en-US", target_kind: str = "svg", visual_profile: str | None = None, typesetter: TypesetterIdentity | None = None,
) -> DraftRender:
    """Build a typed, in-memory closure from explicit authoring inputs.

    This is deliberately an ingress adapter, not an alternate render pipeline:
    its identities are marked ``draft`` and it creates no Context or snapshot
    artifact.  Once returned, the normal review use case cannot distinguish it
    from an immutable closure.
    """
    preset = _load_draft_resource("presentation-preset", preset_path) if preset_path is not None else None
    preset_paths = _draft_preset_paths(preset, preset_path, preset_root) if preset is not None and preset_path is not None else {}
    declared_catalog_paths = (_draft_preset_catalog_paths(preset, preset_path, preset_root)
                              if not icon_catalog_paths and preset is not None and preset_path is not None else ())
    selected_catalog_paths = icon_catalog_paths or declared_catalog_paths
    visual_profile = _preset_visual_profile(preset.contract if preset is not None else None, visual_profile, target_kind)
    paths = (("project", project_path),
             ("view", view_path or preset_paths.get("view")),
             ("theme", theme_path or preset_paths.get("theme")),
             ("color-scheme", scheme_path or preset_paths.get("color-scheme")),
             ("layout-profile", layout_path or preset_paths.get("layout-profile")))
    if any(path is None for _kind, path in paths):
        raise ClosureError("E_DRAFT_PRESENTATION_INCOMPLETE", detail="no file for " + ", ".join(kind for kind, path in paths if path is None) + "; pass it, or a preset that declares it")
    optional = (
        ("actual-set", actual_path), ("summary-profile", summary_path),
        # A preset legend names roles of the preset's own Theme, so it applies
        # only when that Theme is the one rendered (#479 amendment 2).
        ("review-detail-profile", detail_path or (preset_paths.get("review-detail-profile") if theme_path is None else None)),
    )
    sources = [_load_draft_source(kind, path) for kind, path in paths if path is not None]
    sources.extend(_load_draft_source(kind, path) for kind, path in optional if path is not None)
    sources.extend(_load_draft_source("icon-catalog", path) for path in selected_catalog_paths)
    resources = _collect_presentation_resources(sources)
    catalog_resources = tuple(resource for resource in resources if resource.kind == "icon-catalog")
    _validate_icon_catalog_set(catalog_resources)
    return _draft_render_from_resources(resources, viewport=viewport, locale=locale, target_kind=target_kind,
                                        visual_profile=visual_profile, typesetter=typesetter,
                                        icon_assets=_load_draft_icon_assets(catalog_resources, selected_catalog_paths,
                                                                            _draft_view(resources), _draft_theme_refs(resources)),
                                        font_metrics=(safe_load(font_metrics_path.read_bytes()) if font_metrics_path else None),
                                        font_asset_root=(font_metrics_path.parent.resolve() if font_metrics_path else None),
                                        system_fonts=system_fonts, system_font_resolver=system_font_resolver)


_BASELINE_VISUAL_PROFILE = "chrona-output/visual/v0.5-baseline"


def _preset_visual_profile(preset: object, requested: str | None, target_kind: str) -> str:
    """An explicit profile wins; otherwise the preset's preferred profile, else the baseline."""
    if requested is not None:
        return requested
    preferred = preset.preferred_visual_profile if isinstance(preset, PresentationPresetContract) else None
    if preferred is None:
        return _BASELINE_VISUAL_PROFILE
    if preferred != _BASELINE_VISUAL_PROFILE and not preferred.endswith(f"-{target_kind}"):
        raise ClosureError("E_PRESET_VISUAL_PROFILE_TARGET", "/body/visualProfile/preferred",
                           f"preset prefers {preferred}, which cannot serve {target_kind}; pass --visual-profile explicitly")
    return preferred


def _draft_preset_paths(preset: Any, preset_path: Path, preset_root: Path | None = None) -> dict[str, Path]:
    """Resolve one explicit preset into safe ordinary-resource paths."""
    if not isinstance(preset.contract, PresentationPresetContract):
        raise ClosureError("E_DRAFT_PRESET_SCHEMA", detail=f"{preset_path.name} is not a presentation preset")
    mapping = {"view": "view", "theme": "theme", "colorScheme": "color-scheme", "layout": "layout-profile",
               "detailProfile": "review-detail-profile"}
    paths: dict[str, Path] = {}
    for name, kind in mapping.items():
        declaration = preset.contract.resources.get(name)
        if declaration is None and kind == "review-detail-profile":
            continue
        if not isinstance(declaration, Mapping):
            raise ClosureError("E_DRAFT_PRESET_SCHEMA", detail=f"preset {preset.id!r} declares no valid {name!r} resource")
        path = _declared_child(preset_root or preset_path.parent, str(declaration["path"]))
        try:
            resource = _load_draft_resource(kind, path)
        except ClosureError as error:
            if error.diagnostic_id != "E_RESOURCE_VERSION_UNSUPPORTED":
                raise
            # Only an eagerly loaded, declared member of this preset receives
            # copy provenance. Later explicit overrides do not pass this seam.
            raise ClosureError(error.diagnostic_id, error.source_ref, error.detail,
                               declaring_preset_id=preset.id) from error
        if resource.id != declaration["id"]:
            raise ClosureError("E_DRAFT_PRESET_RESOURCE", detail=f"preset {preset.id!r} declares {name} id {declaration['id']!r}, but {path.name} has id {resource.id!r}")
        paths[kind] = path
    return paths


def _draft_preset_catalog_paths(preset: Any, preset_path: Path,
                                preset_root: Path | None = None) -> tuple[Path, ...]:
    """Close only the catalogue paths explicitly pinned by a Draft preset."""
    if not isinstance(preset.contract, PresentationPresetContract):
        raise ClosureError("E_DRAFT_PRESET_SCHEMA", detail=f"{preset_path.name} is not a presentation preset")
    declarations = preset.contract.resources.get("iconCatalogs", ())
    if not isinstance(declarations, (tuple, list)):
        raise ClosureError("E_DRAFT_PRESET_SCHEMA", detail="resources.iconCatalogs of the preset must be a list")
    paths: list[Path] = []
    for declaration in declarations:
        if not isinstance(declaration, Mapping):
            raise ClosureError("E_DRAFT_PRESET_SCHEMA", detail="every entry of resources.iconCatalogs of the preset must be a mapping")
        path = _declared_child(preset_root or preset_path.parent, str(declaration["path"]))
        resource = _load_draft_resource("icon-catalog", path)
        if resource.id != declaration["id"]:
            raise ClosureError("E_DRAFT_PRESET_RESOURCE", detail=f"preset {preset.id!r} declares icon catalog id {declaration['id']!r}, but {path.name} has id {resource.id!r}")
        paths.append(path)
    return tuple(paths)


def resolve_guided_draft_render(
    *, workspace_path: Path, viewport: tuple[int, int | None] = DEFAULT_DRAFT_VIEWPORT,
    locale: str = "en-US", target_kind: str = "svg", visual_profile: str | None = None, typesetter: TypesetterIdentity | None = None,
) -> DraftRender:
    """Resolve one guided Draft without creating files or a second render pipeline."""
    workspace_resource = _load_draft_resource("authoring-workspace", workspace_path)
    if not isinstance(workspace_resource.contract, AuthoringWorkspaceContract):
        raise ClosureError("E_AUTHORING_WORKSPACE_SCHEMA", detail=f"{workspace_path.name} is not an authoring workspace")
    preset_selector = workspace_resource.contract.binding["preset"]
    preset_path = _declared_child(workspace_path.parent, str(preset_selector["path"]))
    preset_resource = _load_draft_resource("presentation-preset", preset_path)
    if not isinstance(preset_resource.contract, PresentationPresetContract):
        raise ClosureError("E_AUTHORING_PRESET_SCHEMA", detail=f"{preset_path.name} is not a presentation preset")
    visual_profile = _preset_visual_profile(preset_resource.contract, visual_profile, target_kind)
    resource_declarations = (*preset_resource.contract.resources.values(), *preset_resource.contract.compatible_color_schemes)
    resources_by_path = {
        str(declaration["path"]): safe_load(_declared_child(preset_path.parent, str(declaration["path"])).read_bytes())
        for declaration in resource_declarations if isinstance(declaration, Mapping)
    }
    if not all(isinstance(value, dict) for value in resources_by_path.values()):
        raise ClosureError("E_AUTHORING_PRESET_RESOURCE", detail="a resource the preset declares is not a mapping document")
    try:
        normalized = normalize_authoring_workspace(workspace_resource.contract, preset_resource.contract, resources_by_path)
    except ContractError as error:
        raise ClosureError(error.diagnostic_id, error.source_ref, error.detail) from error
    except AuthoringError as error:
        raise ClosureError(str(error)) from error
    sources = [_normalized_draft_source(kind, source) for kind, source in normalized.draft_sources()]
    catalog_declarations = preset_resource.contract.resources.get("iconCatalogs", ())
    if not isinstance(catalog_declarations, (tuple, list)):
        raise ClosureError("E_AUTHORING_PRESET_RESOURCE", detail="resources.iconCatalogs of the preset must be a list")
    catalog_paths = tuple(_declared_child(preset_path.parent, str(item["path"])) for item in catalog_declarations)
    sources.extend(_load_draft_source("icon-catalog", path) for path in catalog_paths)
    resources = _collect_presentation_resources(sources)
    catalog_resources = tuple(resource for resource in resources if resource.kind == "icon-catalog")
    if any(resource.id != declaration["id"] for resource, declaration in zip(catalog_resources, catalog_declarations)):
        raise ClosureError("E_AUTHORING_PRESET_RESOURCE", detail="the icon catalog files do not carry the ids the preset declares for them, in order")
    _validate_icon_catalog_set(catalog_resources)
    binding_identity = "sha256:" + sha256(yaml.safe_dump(_plain_value(workspace_resource.contract.binding), sort_keys=True).encode()).hexdigest()
    provenance = GuidedAuthoringProvenance(workspace_resource.content_identity, preset_resource.content_identity, binding_identity)
    return _draft_render_from_resources(resources, viewport=viewport, locale=locale, target_kind=target_kind,
                                        visual_profile=visual_profile, typesetter=typesetter, provenance=provenance,
                                        icon_assets=_load_draft_icon_assets(catalog_resources, catalog_paths,
                                                                            _draft_view(resources), _draft_theme_refs(resources)))


def _declared_child(root: Path, relative: str) -> Path:
    try:
        return resolve_store_address(root, relative)
    except StoreAddressError as error:
        raise ClosureError("E_AUTHORING_PRESET_PATH", detail=f"{relative!r} is not a safe relative path inside the preset directory") from error


def _draft_view(resources: list[ClosureResource]) -> ViewContract:
    view = next((resource.contract for resource in resources if resource.kind == "view"), None)
    if not isinstance(view, ViewContract):
        raise _closure_kind_error("draft resources", "ViewContract", view)
    return view


def _draft_theme_refs(resources: list[ClosureResource]) -> frozenset[str]:
    """Resolve the draft Theme early enough to select its container-image refs (#465).

    This mirrors the resolution `_draft_render_from_resources` performs
    again later for the completed closure; both calls are pure and
    deterministic, so resolving twice costs nothing beyond CPU.
    """
    by_kind = {item.kind: item for item in resources}
    theme, scheme = by_kind.get("theme"), by_kind.get("color-scheme")
    if theme is None or scheme is None:
        return frozenset()
    try:
        resolved = resolve_theme(theme.contract.theme_input, scheme.contract.scheme_input,
                                 scheme_content_identity=scheme.content_identity)
    except ColorSchemeError:
        return frozenset()  # The real error surfaces later, from the authoritative resolution.
    return _theme_container_image_references(resolved)


def _plain_value(value: Any) -> Any:
    """Detach frozen contract containers for canonical provenance serialization."""
    if isinstance(value, Mapping):
        return {str(key): _plain_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain_value(item) for item in value]
    return value


def _normalized_draft_source(kind: str, document: Mapping[str, Any]) -> PresentationResourceSource:
    """Expose a normalized guided resource to the same validation collector."""
    payload = yaml.safe_dump(document, sort_keys=True).encode("utf-8")
    identifier = _resource_id(kind, dict(document))
    if not isinstance(identifier, str) or not identifier:
        raise ClosureError("E_AUTHORING_NORMALIZATION", detail=f"the normalized {kind} resource has no id")
    identity = ClosureIdentity(kind, identifier, "draft", "sha256:" + sha256(payload).hexdigest())
    return PresentationResourceSource(identity, document)


def _draft_render_from_resources(
    resources: list[ClosureResource], *, viewport: tuple[int, int | None], locale: str, target_kind: str,
    visual_profile: str = "chrona-output/visual/v0.5-baseline",
    typesetter: TypesetterIdentity | None = None,
    provenance: GuidedAuthoringProvenance | None = None,
    icon_assets: tuple[IconAsset, ...] = (),
    font_metrics: dict[str, Any] | None = None,
    font_asset_root: Path | None = None,
    system_fonts: bool = False,
    system_font_resolver: SystemFontResolver | None = None,
) -> DraftRender:
    by_kind = {item.kind: item for item in resources}

    try:
        theme_value = resolve_theme(
                by_kind["theme"].contract.theme_input,
                by_kind["color-scheme"].contract.scheme_input,
                scheme_content_identity=by_kind["color-scheme"].content_identity,
            )
        draft_catalogs = tuple(item for item in resources if item.kind == "icon-catalog")
        _validate_icon_catalog_set(draft_catalogs)
        glyphs, patterns = _resolve_theme_catalog_assets(
            theme_value, draft_catalogs)
        if isinstance(theme_value.get("body"), dict):
            theme_value["body"]["catalogAssets"] = {"glyphs": glyphs, "patterns": patterns}
        resolved_theme = ResolvedThemeContract(by_kind["theme"].id, freeze(theme_value),
                                               freeze(glyphs), freeze(patterns))
    except ColorSchemeError as error:
        raise ClosureError(error.diagnostic_id, error.source_ref, error.detail) from error

    asset_root = Path(__file__).resolve().parents[2] / "resources"
    typesetter_environment = _draft_typesetter(target_kind, typesetter)
    resolution = (_draft_system_font_resolution(
        resolved_theme.resolved_input, system_font_resolver or resolve_system_font,
        font_metrics if font_metrics is not None else _packaged_font_metrics(asset_root),
        font_asset_root or asset_root,
    )
                  if system_fonts else
                  # Installed fonts are a normal source on every path: each Theme role's font stack resolves to a
                  # declared, installed or packaged face (#1281); None when every role is already one declared face.
                  resolve_theme_font_stacks(resolved_theme.resolved_input,
                                            font_metrics if font_metrics is not None else _packaged_font_metrics(asset_root),
                                            asset_root=font_asset_root or asset_root))
    context_value = {
            "version": RENDER_CONTEXT_VERSION, "kind": "render-context", "id": "draft-render",
        "body": {
            "project": _draft_reference(by_kind["project"]),
            "view": _draft_reference(by_kind["view"]),
            "theme": _draft_reference(by_kind["theme"]),
            "colorScheme": _draft_reference(by_kind["color-scheme"]),
            "layout": _draft_reference(by_kind["layout-profile"]),
            "inputs": {
                **({"actual": _draft_reference(by_kind["actual-set"])} if "actual-set" in by_kind else {}),
                **({"summaryProfile": _draft_reference(by_kind["summary-profile"])} if "summary-profile" in by_kind else {}),
                **({"detailProfile": _draft_reference(by_kind["review-detail-profile"])} if "review-detail-profile" in by_kind else {}),
                **({"iconCatalogs": [_draft_reference(item) for item in resources if item.kind == "icon-catalog"]}
                   if any(item.kind == "icon-catalog" for item in resources) else {}),
            },
            "environment": {
                "viewport": {"inlineSize": viewport[0], "blockSize": viewport[1] or 900},
                "locale": locale,
                "fontMetrics": font_metrics if font_metrics is not None else _packaged_font_metrics(asset_root),
                "scenePrecision": 3,
                **({"rasterizer": _draft_rasterizer(target_kind)} if target_kind in {"png", "pdf"} else {}),
                **({"typesetter": typesetter_environment} if typesetter_environment else {}),
            },
            "target": {"kind": target_kind, "capabilities": list(_DRAFT_CAPABILITIES) if target_kind == "svg" else [], "visualProfile": visual_profile,
                       **({"textMode": "positioned"} if target_kind in {"typst", "tikz"} else {})},
        },
    }
    try:
        context = parse_contract(
            ClosureIdentity("render-context", "draft-render", "draft", "draft"), context_value
        )
    except SchemaContractError as error:
        raise ClosureError("E_RENDER_CONTEXT_SCHEMA", error.source_ref, _schema_detail(error)) from error
    except ContractError as error:
        raise ClosureError("E_RENDER_CONTEXT_SCHEMA", detail=error.detail) from error
    if not isinstance(context, RenderContextContract):  # defensive contract boundary
        raise _closure_kind_error("draft render context", "RenderContextContract", context)
    return DraftRender(RenderClosure(context, tuple(resources), resolved_theme, icon_assets, provenance),
                       font_asset_root or asset_root, auto_block=viewport[1] is None, font_resolution=resolution)


def _draft_system_font_resolution(theme: Mapping[str, Any], resolver: SystemFontResolver,
                                  descriptor: dict[str, Any], asset_root: Path) -> DraftFontResolution:
    """Close declared pairs first, resolving only missing exact faces from the host."""
    try:
        typography = ThemeTokenView(theme)
        roles = theme.get("body", {}).get("roles", {})
        treatments = {
            role: typography.text_treatment(role)
            for role, binding in roles.items()
            if isinstance(binding, Mapping) and "fontFamily" in binding and "fontWeight" in binding
        }
        requests = {(treatment.family.split(",", 1)[0].strip(), treatment.weight)
                    for treatment in treatments.values()}
    except (AttributeError, ThemeTokenError, TypeError, ValueError) as error:
        raise ClosureError("E_FONT_SYSTEM_MISMATCH", detail="Theme typography cannot select one system face") from error
    if not requests:
        raise ClosureError("E_FONT_SYSTEM_MISSING", detail="Theme has no typography faces")
    if any(not family for family, _weight in requests):
        raise ClosureError("E_FONT_SYSTEM_MISSING", detail="Theme primary font family is empty")
    try:
        declared = {(str(asset.get("family", "")).casefold(), asset.get("weight"))
                    for asset in descriptor.get("assets", ()) if isinstance(asset, dict)}
        declared_files = resolve_font_files(descriptor, asset_root=asset_root)[0]
        metrics = {}
        selected_files = []
        missing = []
        for family, weight in sorted(requests):
            if (family.casefold(), weight) in declared:
                metric = resolve_font_metrics(family, descriptor, weight=weight,
                                              asset_root=asset_root, _allow_substitute=False)
                metrics[(family.casefold(), weight)] = metric
                selected_files.append(next(item for item in declared_files
                                           if item.family.casefold() == family.casefold() and item.weight == weight))
            else:
                missing.append((family, weight))
        host = (resolve_draft_fonts(resolver(family, weight) for family, weight in missing)
                if missing else None)
        if host is not None:
            metrics.update(host.metrics.metrics)
            selected_files.extend(host.font_files)
        files = tuple({(item.content_identity, item.index): item for item in selected_files}.values())
        resolution = DraftFontResolution(host.faces if host else (), FontMetricsCatalog(metrics), files)
        tabular_warnings: list[FontTabularWarning] = []
        for role, treatment in sorted(treatments.items()):
            metric = resolution.metrics.select(treatment.family, treatment.weight)
            try:
                metric.ensure_numeric_spacing(treatment.numeric_spacing)
            except FontMetricsError as error:
                if treatment.numeric_spacing == "tabular":
                    try:
                        metric.ensure_numeric_spacing("proportional")
                    except FontMetricsError:
                        pass
                    else:
                        tabular_warnings.append(FontTabularWarning(role, treatment.family, treatment.weight))
                        continue
                raise ClosureError("E_FONT_METRICS_UNAVAILABLE", detail=(
                    f"role={role}; {treatment.family}/{treatment.weight} lacks "
                    f"{treatment.numeric_spacing} digit advances")) from error
        return DraftFontResolution(resolution.faces, resolution.metrics, resolution.font_files,
                                   tuple(tabular_warnings))
    except SystemFontError as error:
        raise ClosureError(error.code, detail=error.detail) from error
    except (FontMetricsError, StopIteration, KeyError, TypeError) as error:
        raise ClosureError("E_FONT_METRICS_UNAVAILABLE", detail=str(error)) from error


def _load_draft_resource(kind: str, path: Path) -> ClosureResource:
    """Read one explicit draft input and freeze it through its resource contract."""
    value = safe_load(path.read_bytes())
    if not isinstance(value, dict):
        raise _draft_shape_error(kind, value)
    identifier = _resource_id(kind, value)
    if not isinstance(identifier, str) or not identifier:
        raise _draft_shape_error(kind, value)
    payload = path.read_bytes()
    identity = ClosureIdentity(kind, identifier, "draft", "sha256:" + sha256(payload).hexdigest())
    try:
        contract = parse_contract(identity, value)
    except SchemaContractError as error:
        raise ClosureError("E_" + kind.upper().replace("-", "_") + "_SCHEMA", error.source_ref, _schema_detail(error)) from error
    except ContractError as error:
        raise ClosureError(error.diagnostic_id, error.source_ref, error.detail) from error
    return ClosureResource(kind, identifier, "draft", identity.content_identity, contract)


def _load_draft_source(kind: str, path: Path) -> PresentationResourceSource:
    """Read one declared Draft file without allowing it into typed closure yet."""
    payload = path.read_bytes()
    try:
        source = safe_load(payload)
        derived = kind == "theme" and is_derived_theme(source)
        value = resolve_draft_theme(path, payload=payload) if derived else source
        referenced = kind == "theme" and isinstance(value, dict) and uses_references(value)
        if referenced:
            value = resolve_references(value)
    except ThemeInheritanceError as error:
        raise ClosureError(error.code, detail=error.detail or None) from error
    except ThemeReferenceError as error:
        raise ClosureError(error.code, error.pointer, error.detail) from error
    if not isinstance(value, dict):
        raise _draft_shape_error(kind, value)
    identifier = _resource_id(kind, value)
    if not isinstance(identifier, str) or not identifier:
        raise _draft_shape_error(kind, value)
    identity = ClosureIdentity(kind, identifier, "draft",
                               content_identity(value) if derived or referenced else "sha256:" + sha256(payload).hexdigest())
    return PresentationResourceSource(identity, value)


def _collect_presentation_resources(sources: list[PresentationResourceSource]) -> list[ClosureResource]:
    """Turn a fully declared, valid resource set into closure resources."""
    collection = collect_presentation_contracts(tuple(sources))
    if collection.diagnostics:
        if len(collection.diagnostics) == 1:
            diagnostic = collection.diagnostics[0]
            code = ("E_" + diagnostic.resource_kind.upper().replace("-", "_") + "_SCHEMA"
                    if diagnostic.code == "E_RESOURCE_SCHEMA" else diagnostic.code)
            raise ClosureError(code, diagnostic.pointer, diagnostic.message)
        raise PresentationIngressRejected(collection.diagnostics)
    return [ClosureResource(contract.identity.kind, contract.identity.id, contract.identity.revision,
                            contract.identity.content_identity, contract)
            for contract in collection.contracts]


def _draft_shape_error(kind: str, value: object) -> ClosureError:
    """A declared Draft file that is not a mapping with an id: say which, instead of only the code (#782)."""
    code = "E_" + kind.upper().replace("-", "_") + "_SCHEMA"
    if not isinstance(value, dict):
        found = "an empty document" if value is None else f"a {type(value).__name__}"
        return ClosureError(code, detail=f"a {kind} file must be a YAML mapping; found {found}")
    name = "project.id" if kind == "project" else "id"
    return ClosureError(code, detail=f"a {kind} file must declare a non-empty string {name}")


def _resource_id(kind: str, value: dict[str, Any]) -> object:
    return value.get("project", {}).get("id") if kind == "project" and isinstance(value.get("project"), dict) else value.get("id")


def _schema_detail(error: SchemaContractError) -> str:
    return error.violation.message if error.violation is not None else str(error)


def _draft_reference(resource: ClosureResource) -> dict[str, Any]:
    return {
        "id": resource.id, "kind": resource.kind,
        "store": {"provider": "draft", "identity": "draft"},
        "address": resource.kind, "revision": {"token": "draft"},
        "contentIdentity": resource.content_identity,
    }


def _packaged_font_metrics(asset_root: Path) -> dict[str, Any]:
    """Load the selected packaged default as declared data, never code literals."""
    value = safe_load((asset_root / "fonts" / "default-font-metrics.yaml").read_bytes())
    if not isinstance(value, dict):
        raise ClosureError("E_FONT_METRICS_UNAVAILABLE", detail="the packaged default-font-metrics.yaml is not a mapping")
    return value


def _draft_rasterizer(target_kind: str) -> dict[str, Any]:
    if target_kind == "png":
        try:
            import resvg_py
            return {"engine": "resvg-py", "version": resvg_py.__version__, "resvgVersion": resvg_py.__resvg_version__, "dpi": 96}
        except ImportError:
            return {"engine": "resvg-py", "version": "unavailable", "resvgVersion": "unavailable", "dpi": 96}
    try:
        return {"engine": "reportlab", "svglibVersion": version("svglib"), "reportlabVersion": version("reportlab"), "invariant": True}
    except Exception:
        return {"engine": "reportlab", "svglibVersion": "unavailable", "reportlabVersion": "unavailable", "invariant": True}


def _draft_typesetter(target_kind: str, typesetter: TypesetterIdentity | None) -> dict[str, Any] | None:
    if target_kind not in {"typst", "tikz"}:
        if typesetter is not None:
            raise ClosureError("E_RENDER_TYPESETTER_DESCRIPTOR", detail=f"a {target_kind} render takes no typesetter, got {typesetter.engine}")
        return None
    if typesetter is None:
        raise ClosureError("E_RENDER_TYPESETTER_DESCRIPTOR", detail=f"a {target_kind} render needs a typesetter identity (engine, version, adapter grammar)")
    return {"engine": typesetter.engine, "version": typesetter.version,
            "adapterGrammar": typesetter.adapter_grammar}


def resolve_render_context(reference: dict[str, Any], reader: SnapshotReader,
                           *, decoded_resources: Mapping[str, Any] | None = None) -> RenderClosure:
    context = _load_presentation(reference, reader, decoded_resources)
    if context.version not in RENDER_CONTEXT_VERSIONS:
        raise ClosureError("E_RENDER_CONTEXT_SCHEMA", detail=f"render context version {context.version!r} is not one of {sorted(RENDER_CONTEXT_VERSIONS)}")
    return _resolve_layout_context(context, reader, decoded_resources)


def _resolve_layout_context(context_contract: RenderContextContract, reader: SnapshotReader,
                            decoded_resources: Mapping[str, Any] | None = None) -> RenderClosure:
    if context_contract.environment.font_metrics.get("missingFont") != "diagnose":
        raise ClosureError("E_FONT_SUBSTITUTE_CONTEXT", detail=f"environment.fontMetrics.missingFont is {context_contract.environment.font_metrics.get('missingFont')!r}; a render context must say diagnose")
    ordered = (
        (context_contract.project.as_reader_reference(), "project"),
        (context_contract.view.as_reader_reference(), "view"),
        (context_contract.theme.as_reader_reference(), "theme"),
        (context_contract.color_scheme.as_reader_reference(), "color-scheme"),
        (context_contract.layout.as_reader_reference(), "layout-profile"),
    )
    sources = [_load_reference_source(reference, reader, kind, decoded_resources) for reference, kind in ordered]
    optional = ((context_contract.actual, "actual-set"),
                (context_contract.summary_profile, "summary-profile"),
                (context_contract.detail_profile, "review-detail-profile"),
                *((reference, "icon-catalog") for reference in (context_contract.icon_catalogs or ())))
    sources.extend(_load_reference_source(reference.as_reader_reference(), reader, kind, decoded_resources)
                   for reference, kind in optional if reference is not None)
    initial = collect_presentation_contracts(tuple(sources))
    project = next((contract for contract in initial.contracts if isinstance(contract, ProjectContract)), None)
    if project is not None:
        for extension in project.extensions:
            package_reference = extension.get("resource")
            if package_reference is not None:
                sources.append(_load_reference_source(package_reference, reader, "profile-package", decoded_resources))
    resources = _collect_presentation_resources(sources)
    for extension in resources[0].contract.extensions:
        package_reference = extension.get("resource")
        if package_reference is not None:
            package = next((item for item in resources if item.kind == "profile-package" and item.id == package_reference.get("id")), None)
            if package is None:
                raise ClosureError("E_CLOSURE_REQUIRED", detail=f"the extension names profile-package {package_reference.get('id')!r}, which the closure does not contain")
            if package.contract.package_id != extension.get("packageId"):
                raise ClosureError("E_CLOSURE_ID", detail=f"profile-package {package_reference.get('id')!r} declares packageId {package.contract.package_id!r}, the extension says {extension.get('packageId')!r}")
    if context_contract.snapshot is not None:
        snapshot = _load_reference(context_contract.snapshot.as_reader_reference(), reader, "snapshot-ref", decoded_resources)
        snapshot_project = _load_reference(snapshot.contract.project.as_reader_reference(), reader, "project", decoded_resources)
        if snapshot_project.id != resources[0].id:
            raise ClosureError("E_CLOSURE_ID", detail=f"the snapshot project id {snapshot_project.id!r} is not the context project id {resources[0].id!r}")
        resources.extend((snapshot, ClosureResource(
            "snapshot-project", snapshot_project.id, snapshot_project.revision,
            snapshot_project.content_identity, snapshot_project.contract)))
    if context_contract.target.capabilities != tuple(sorted(context_contract.target.capabilities)):
        raise ClosureError("E_TARGET_CAPABILITY_ORDER", detail=f"target.capabilities must be sorted, got {list(context_contract.target.capabilities)}")
    theme, scheme = resources[2], resources[3]
    try:
        value = resolve_theme(theme.contract.theme_input, scheme.contract.scheme_input, scheme_content_identity=scheme.content_identity)
    except ColorSchemeError as error:
        raise ClosureError(error.diagnostic_id, error.source_ref, error.detail) from error
    catalog_resources = tuple(item for item in resources if item.kind == "icon-catalog")
    _validate_icon_catalog_set(catalog_resources)
    glyphs, patterns = _resolve_theme_catalog_assets(value, catalog_resources)
    if isinstance(value.get("body"), dict):
        value["body"]["catalogAssets"] = {"glyphs": glyphs, "patterns": patterns}
    resolved_theme = ResolvedThemeContract(theme.id, freeze(value), freeze(glyphs), freeze(patterns))
    if catalog_resources:
        view_contract = resources[1].contract
        if not isinstance(view_contract, ViewContract):
            raise _closure_kind_error("resolved View resource", "ViewContract", view_contract)
        icon_assets = _load_icon_assets(context_contract, catalog_resources, reader, view_contract,
                                        _theme_container_image_references(value))
    else:
        icon_assets = ()
    return RenderClosure(context_contract, tuple(resources), resolved_theme, icon_assets)


def _validate_icon_catalog_set(resources: tuple[ClosureResource, ...]) -> None:
    """Reject ambiguity before any View can select an icon reference."""
    namespaces: set[str] = set()
    for resource in resources:
        if not isinstance(resource.contract, IconCatalogContract):
            raise _closure_kind_error(f"icon catalog resource id={resource.id}", "IconCatalogContract", resource.contract)
        catalog = resource.contract
        names = (catalog.set_name, *catalog.aliases)
        if len(names) != len(set(names)) or any(name in namespaces for name in names):
            raise ClosureError("E_ICON_SET_AMBIGUOUS", detail=f"icon catalog {resource.id!r} reuses a set name or alias: {[name for name in names if names.count(name) > 1 or name in namespaces]}")
        namespaces.update(names)


def _resolve_theme_catalog_assets(theme: Mapping[str, Any],
                                 resources: tuple[ClosureResource, ...]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve every Theme catalogue reference before Layout receives tokens."""
    body = theme.get("body")
    roles = body.get("roles") if isinstance(body, Mapping) else None
    values = body.get("values") if isinstance(body, Mapping) else None
    if not isinstance(roles, Mapping) or not isinstance(values, Mapping):
        return {}, {}
    catalogs = [item.contract for item in resources if isinstance(item.contract, IconCatalogContract)]
    glyphs: dict[str, Any] = {}
    patterns: dict[str, Any] = {}

    def fail(pointer: str, reference: str, reason: str) -> None:
        raise ClosureError("E_THEME_ASSET_REFERENCE", pointer,
                           f"reference={reference}; {reason}")

    def resolve(reference: object, kind: str, pointer: str) -> None:
        if not isinstance(reference, str) or reference.count(":") != 1:
            fail(pointer, str(reference), "malformed set:name")
        set_name, name = reference.split(":", 1)
        matches = [catalog for catalog in catalogs if set_name in {catalog.set_name, *catalog.aliases}]
        if len(matches) != 1:
            fail(pointer, reference, "unknown or ambiguous catalogue set")
        catalog = matches[0]
        collection = catalog.raw_glyphs if kind == "glyph" else catalog.raw_patterns
        if name not in collection:
            fail(pointer, reference, f"missing {kind} entry")
        try:
            entry = validate_theme_asset_entry(catalog, kind, name)
        except ContractError as error:
            fail(pointer, reference, f"invalid {kind} entry ({error.diagnostic_id})")
        target = glyphs if kind == "glyph" else patterns
        target[reference] = entry

    canvas_pattern_roles = {"canvas-texture", "canvas-overlay"}

    def bound_value(role: str, binding: Mapping[str, Any], property_name: str,
                    expected_type: str, *, required: bool = True) -> Any:
        pointer = f"/body/roles/{role}/{property_name}"
        token_id = binding.get(property_name)
        if token_id is None and not required:
            return None
        if not isinstance(token_id, str):
            raise ClosureError("E_THEME_ROLE_REQUIRED", pointer)
        token = values.get(token_id)
        if not isinstance(token, Mapping) or token.get("type") != expected_type:
            raise ClosureError("E_THEME_TOKEN_TYPE", pointer)
        return token.get("value")

    def validate_color(role: str, binding: Mapping[str, Any], property_name: str,
                       *, required: bool = True) -> None:
        value = bound_value(role, binding, property_name, "color", required=required)
        if value is None and not required:
            return
        if not isinstance(value, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
            raise ClosureError("E_THEME_ROLE_PROPERTY_UNSUPPORTED", f"/body/roles/{role}/{property_name}")

    def validate_numeric(role: str, binding: Mapping[str, Any], property_name: str,
                         *, required: bool = True) -> Any:
        value = bound_value(role, binding, property_name, "number", required=required)
        if value is None and not required:
            return None
        try:
            finite = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))
        except (OverflowError, TypeError, ValueError):
            finite = False
        if not finite:
            raise ClosureError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/{property_name}")
        return value

    def validate_seeded_pattern(role: str, declaration: Mapping[str, Any]) -> None:
        pointer = f"/body/roles/{role}/pattern"
        motif = declaration.get("motif")
        numeric_values: list[Any] = []
        tile = declaration.get("tile")
        if not isinstance(tile, Mapping):
            raise ClosureError("E_THEME_TOKEN_TYPE", pointer)
        numeric_values.extend((tile.get("inlineSize"), tile.get("blockSize")))
        numeric_values.extend((declaration.get("radius"),) if motif == "grain" else
                              (declaration.get("length"), declaration.get("strokeWidth"), declaration.get("slant")))
        try:
            if any(not isinstance(value, (int, float)) or isinstance(value, bool)
                   or not math.isfinite(float(value)) for value in numeric_values):
                raise ValueError
        except (OverflowError, TypeError, ValueError):
            raise ClosureError("E_THEME_TOKEN_TYPE", pointer) from None
        if (not isinstance(declaration.get("seed"), int) or isinstance(declaration.get("seed"), bool)
                or not 0 <= declaration["seed"] <= 0xFFFFFFFF
                or not isinstance(declaration.get("count"), int) or isinstance(declaration.get("count"), bool)
                or not 1 <= declaration["count"] <= 64):
            raise ClosureError("E_THEME_TOKEN_TYPE", pointer)

    def validate_fidelity(role: str, binding: Mapping[str, Any], property_name: str) -> None:
        if property_name not in binding:
            return
        value = bound_value(role, binding, property_name, "fidelity")
        if value not in {"required", "decorative-optional"}:
            raise ClosureError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/{property_name}")

    def validate_canvas_pattern(role: str, binding: Mapping[str, Any]) -> None:
        mode = binding.get("patternMode") if role == "canvas-texture" else "ink-only"
        if mode not in {None, "ink-only"}:
            raise ClosureError("E_THEME_ROLE_PROPERTY_UNSUPPORTED", f"/body/roles/{role}/patternMode")
        ink_only = mode == "ink-only"
        if role == "canvas-overlay" or ink_only:
            if "fill" in binding:
                raise ClosureError("E_THEME_ROLE_PROPERTY_UNSUPPORTED", f"/body/roles/{role}/fill")
            validate_color(role, binding, "stroke")
            validate_numeric(role, binding, "opacity", required=False)
            validate_fidelity(role, binding, "textureFidelity")
        else:
            if "textureFidelity" in binding:
                raise ClosureError("E_THEME_ROLE_PROPERTY_UNSUPPORTED",
                                   f"/body/roles/{role}/textureFidelity")
            # Preserve the historical opaque-pattern no-op bindings. The old
            # validator accepted opacity=1 and backgroundTreatment=fill.
            if "opacity" in binding:
                validate_numeric(role, binding, "opacity", required=False)
                token_id = binding["opacity"]
                token = values.get(token_id) if isinstance(token_id, str) else None
                token_value = token.get("value") if isinstance(token, Mapping) else None
                if (not isinstance(token, Mapping) or token.get("type") != "number"
                        or not isinstance(token_value, (int, float))
                        or isinstance(token_value, bool) or not math.isfinite(float(token_value))
                        or float(token_value) != 1):
                    raise ClosureError("E_THEME_ROLE_PROPERTY_UNSUPPORTED",
                                       f"/body/roles/{role}/opacity")
            if ("backgroundTreatment" in binding
                    and binding["backgroundTreatment"] != "fill"):
                raise ClosureError("E_THEME_ROLE_PROPERTY_UNSUPPORTED",
                                   f"/body/roles/{role}/backgroundTreatment")
            validate_color(role, binding, "fill")
            validate_color(role, binding, "stroke")
        conflicting = ("strokeWidth", "dash", "strokeLineCap", "strokeLineJoin",
                       "strokeFinishFidelity", "gradientStart", "gradientEnd", "gradientAngle",
                       "gradientFidelity", "shadowColor", "shadowOffsetX", "shadowOffsetY",
                       "shadowBlur", "shadowOpacity", "shadowFidelity", "glowColor", "glowBlur",
                       "glowOpacity", "glowFidelity", "wobbleAmplitude", "wobbleWavelength",
                       "wobbleSeed", "wobbleFidelity", "backgroundPaintOrder")
        for property_name in conflicting:
            if property_name in binding:
                raise ClosureError("E_THEME_ROLE_PROPERTY_UNSUPPORTED", f"/body/roles/{role}/{property_name}")
        if role == "canvas-overlay" and "patternMode" in binding:
            raise ClosureError("E_THEME_ROLE_PROPERTY_UNSUPPORTED", f"/body/roles/{role}/patternMode")

    def validate_radial_overlay(role: str, binding: Mapping[str, Any]) -> None:
        if "stroke" in binding:
            raise ClosureError("E_THEME_ROLE_PROPERTY_UNSUPPORTED", f"/body/roles/{role}/stroke")
        validate_color(role, binding, "fill")
        for property_name in ("radialCenterInline", "radialCenterBlock", "radialRadiusInline",
                              "radialRadiusBlock", "radialInnerStop"):
            validate_numeric(role, binding, property_name)
        validate_numeric(role, binding, "opacity", required=False)
        validate_fidelity(role, binding, "gradientFidelity")
        conflicting = ("pattern", "patternMode", "textureFidelity", "strokeWidth", "dash",
                       "strokeLineCap", "strokeLineJoin", "strokeFinishFidelity", "gradientStart",
                       "gradientEnd", "gradientAngle", "shadowColor", "shadowOffsetX", "shadowOffsetY",
                       "shadowBlur", "shadowOpacity", "shadowFidelity", "glowColor", "glowBlur",
                       "glowOpacity", "glowFidelity", "wobbleAmplitude", "wobbleWavelength",
                       "wobbleSeed", "wobbleFidelity", "backgroundTreatment", "backgroundPaintOrder")
        for property_name in conflicting:
            if property_name in binding:
                raise ClosureError("E_THEME_ROLE_PROPERTY_UNSUPPORTED", f"/body/roles/{role}/{property_name}")

    def validate_pattern_paint(role: str, binding: Mapping[str, Any]) -> None:
        conflicting = ("strokeWidth", "dash", "strokeLineCap", "strokeLineJoin",
                       "strokeFinishFidelity", "gradientStart", "gradientEnd",
                       "gradientAngle", "gradientFidelity")
        for property_name in conflicting:
            if property_name in binding:
                raise ClosureError("E_THEME_ROLE_PROPERTY_UNSUPPORTED",
                                   f"/body/roles/{role}/{property_name}")
        if ("backgroundTreatment" in binding
                and binding["backgroundTreatment"] != "fill"):
            raise ClosureError("E_THEME_ROLE_PROPERTY_UNSUPPORTED",
                               f"/body/roles/{role}/backgroundTreatment")
        for property_name in ("fill", "stroke"):
            token_id = binding.get(property_name)
            role_pointer = f"/body/roles/{role}/{property_name}"
            if not isinstance(token_id, str):
                raise ClosureError("E_THEME_ROLE_REQUIRED", role_pointer)
            token = values.get(token_id)
            token_value = token.get("value") if isinstance(token, Mapping) else None
            if (not isinstance(token, Mapping) or token.get("type") != "color"
                    or not isinstance(token_value, str)
                    or not re.fullmatch(r"#[0-9A-Fa-f]{6}", token_value)):
                raise ClosureError("E_THEME_ROLE_PROPERTY_UNSUPPORTED", role_pointer)
        token_id = binding.get("opacity")
        if isinstance(token_id, str):
            token = values.get(token_id)
            try:
                opacity = float(token.get("value")) if isinstance(token, Mapping) and token.get("type") == "number" else float("nan")
            except (TypeError, ValueError):
                opacity = float("nan")
            if not math.isfinite(opacity) or opacity != 1:
                raise ClosureError("E_THEME_ROLE_PROPERTY_UNSUPPORTED", f"/body/roles/{role}/opacity")

    for role, binding in roles.items():
        if not isinstance(binding, Mapping):
            continue
        role_name = str(role)
        if role_name in canvas_pattern_roles:
            if role_name == "canvas-texture" and "pattern" not in binding and "patternMode" not in binding:
                # Preserve the legacy non-drawable role-without-pattern behavior.
                pass
            else:
                if "pattern" not in binding:
                    raise ClosureError("E_THEME_ROLE_REQUIRED", f"/body/roles/{role_name}/pattern")
                validate_canvas_pattern(role_name, binding)
        elif role_name == "canvas-overlay-gradient":
            validate_radial_overlay(role_name, binding)

        for property_name, expected_kind, ref_pointer in (
                ("symbol", "glyph", "shape/catalog"), ("pattern", "pattern", "ref")):
            token_id = binding.get(property_name)
            if not isinstance(token_id, str):
                continue
            token = values.get(token_id)
            token_value = token.get("value") if isinstance(token, Mapping) else None
            reference = None
            if property_name == "symbol" and isinstance(token_value, Mapping):
                shape = token_value.get("shape")
                if isinstance(shape, Mapping):
                    reference = shape.get("catalog")
            elif property_name == "pattern" and isinstance(token_value, Mapping):
                pattern_kind = token_value.get("kind")
                if pattern_kind == "catalog":
                    reference = token_value.get("ref")
                elif pattern_kind == "seeded":
                    if role_name not in canvas_pattern_roles:
                        raise ClosureError("E_THEME_ROLE_PROPERTY_UNSUPPORTED",
                                           f"/body/roles/{role_name}/pattern")
                    validate_seeded_pattern(role_name, token_value)
            if reference is None:
                continue
            pointer = f"/body/values/{token_id}/value/{ref_pointer}"
            if property_name == "pattern" and theme_catalog_pattern_consumer(str(role), property_name) is None:
                raise ClosureError("E_THEME_ROLE_PROPERTY_UNSUPPORTED",
                                   f"/body/roles/{role}/{property_name}")
            if property_name == "pattern" and role_name not in canvas_pattern_roles:
                validate_pattern_paint(str(role), binding)
            resolve(reference, expected_kind, pointer)
    for role, binding in roles.items():
        # The vector artwork of an annotation container (#848) is a catalogue glyph the Theme names.
        token_id = binding.get("annotationContainer") if isinstance(binding, Mapping) else None
        token = values.get(token_id) if isinstance(token_id, str) else None
        token_value = token.get("value") if isinstance(token, Mapping) else None
        artwork = token_value.get("artwork") if isinstance(token_value, Mapping) else None
        if isinstance(artwork, Mapping) and artwork.get("glyph") is not None:
            resolve(artwork["glyph"], "glyph", f"/body/values/{token_id}/value/artwork/glyph")
        elif isinstance(artwork, list):
            for index, layer in enumerate(artwork):
                if isinstance(layer, Mapping) and layer.get("glyph") is not None:
                    resolve(layer["glyph"], "glyph", f"/body/values/{token_id}/value/artwork/{index}/glyph")
    declared_kinds = body.get("annotationKinds") if isinstance(body, Mapping) else None
    if isinstance(declared_kinds, Mapping):
        # A kind's stamp (#584) is a catalogue glyph the Theme names, resolved with the other glyphs.
        for kind, entry in declared_kinds.items():
            if isinstance(entry, Mapping) and entry.get("stamp") is not None:
                resolve(entry["stamp"], "glyph", f"/body/annotationKinds/{kind}/stamp")
    return glyphs, patterns


def _safe_icon_address(address: str) -> bool:
    try:
        check_store_address(address)
    except StoreAddressError:
        return False
    return True


def _selected_icon_references(view: ViewContract, extra: frozenset[str] = frozenset()) -> set[str]:
    selected: set[str] = set(extra)
    for visual in view.view.visuals:
        if visual.ref is not None:
            selected.add(visual.ref)
        if visual.encoding is not None:
            selected.update(str(item) for item in visual.encoding.get("domain", {}).values())
    return selected


def _theme_container_image_references(resolved_theme: Mapping[str, Any]) -> frozenset[str]:
    """Return every icon-catalog reference a Theme binds as container artwork (#465).

    A View's `visuals` grammar never selects these (Specification 64 §7);
    without this, an entry named only by `annotationContainer.image` would
    never be closed into `RenderClosure.icon_assets`, and Theme/Layout
    resolution would fail with a stable ingress error for an entry the
    pinned Context can actually supply.
    """
    body = resolved_theme.get("body")
    roles = body.get("roles") if isinstance(body, Mapping) else None
    if not isinstance(roles, Mapping):
        return frozenset()
    tokens = ThemeTokenView(resolved_theme)
    references: set[str] = set()
    for role in roles:
        try:
            container = tokens.annotation_container(str(role))
        except ThemeTokenError:
            continue  # Malformed tokens are diagnosed later, when the role is actually used.
        if container is not None and container.outline == "image" and container.image_ref:
            references.add(container.image_ref)
    return frozenset(references)


def _selected_icon_entry(catalog: IconCatalogContract, name: str) -> IconEntry:
    try:
        validate_icon_catalog_entry(catalog, name)
    except ContractError as error:
        raise ClosureError("E_ICON_CATALOG_SCHEMA", f"/body/icons/{name}") from error
    raw = catalog.raw_icons[name]
    viewport, paths, source = raw["viewport"], raw.get("paths", ()), raw.get("source")
    if not isinstance(viewport, FrozenDict) or not isinstance(paths, (FrozenList, tuple)):
        raise ClosureError("E_ICON_CATALOG_SCHEMA", detail=f"icon {name!r} of catalog {catalog.set_name!r} needs a viewport mapping and a paths list")
    normalized = tuple(IconPath(str(path["paint"]), str(path["data"]),
                                float(path["strokeWidth"]) if "strokeWidth" in path else None,
                                str(path["lineCap"]) if "lineCap" in path else None,
                                str(path["lineJoin"]) if "lineJoin" in path else None)
                       for path in paths if isinstance(path, FrozenDict))
    if len(normalized) != len(paths):
        raise ClosureError("E_ICON_CATALOG_SCHEMA", detail=f"icon {name!r} of catalog {catalog.set_name!r}: every entry of paths must be a mapping")
    source_value = raw.get("source")
    source = None
    if source_value is not None:
        if not isinstance(source_value, FrozenDict):
            raise ClosureError("E_ICON_CATALOG_SCHEMA", detail=f"icon {name!r} of catalog {catalog.set_name!r}: source must be a mapping")
        source = IconRasterSource(str(source_value["address"]), str(source_value["contentIdentity"]))
    return IconEntry(name, str(raw["kind"]), (int(viewport["inlineSize"]), int(viewport["blockSize"])),
                     str(raw["alternative"]), normalized, source)


def _selected_catalog_entries(catalog: IconCatalogContract, view: ViewContract,
                              theme_refs: frozenset[str] = frozenset()) -> tuple[IconEntry, ...]:
    names: set[str] = set()
    for reference in _selected_icon_references(view, theme_refs):
        if reference.count(":") != 1:
            continue
        set_name, name = reference.split(":", 1)
        if set_name in {catalog.set_name, *catalog.aliases}:
            canonical = str(catalog.entry_aliases.get(name, name))
            if canonical in catalog.raw_icons:
                names.add(canonical)
    return tuple(_selected_icon_entry(catalog, name) for name in sorted(names))


def _load_icon_assets(context: RenderContextContract, catalog_resources: tuple[ClosureResource, ...],
                      reader: SnapshotReader, view: ViewContract,
                      theme_refs: frozenset[str] = frozenset()) -> tuple[IconAsset, ...]:
    if not catalog_resources:
        return ()
    assets: list[IconAsset] = []
    by_id = {reference.id: reference for reference in context.icon_catalogs}
    for catalog_resource in catalog_resources:
        if not isinstance(catalog_resource.contract, IconCatalogContract):
            raise _closure_kind_error(f"icon catalog resource id={catalog_resource.id}", "IconCatalogContract", catalog_resource.contract)
        reference = by_id.get(catalog_resource.id)
        if reference is None:
            raise _closure_kind_error(f"icon catalog resource id={catalog_resource.id}", "declared Context icon catalog reference", reference)
        catalog = catalog_resource.contract
        entries = _selected_catalog_entries(catalog, view, theme_refs)
        for entry in entries:
            icon_id = f"{catalog_resource.contract.set_name}:{entry.name}"
            if entry.kind == "vector":
                paths = tuple(NormalizedIconPath(tuple(IconPathCommand(command.kind, command.points)
                                                        for command in _compact_commands(path.data)), path.paint,
                                           path.stroke_width, path.line_cap, path.line_join)
                              for path in entry.paths)
                assets.append(IconAsset(icon_id, entry.kind, catalog_resource.content_identity,
                                        entry.viewport, entry.alternative,
                                        NormalizedVectorIcon(entry.viewport, paths)))
                continue
            if entry.source is None:
                raise ClosureError("E_ICON_CATALOG_SCHEMA", f"/body/icons/{entry.name}")
            if not _safe_icon_address(entry.source.address):
                raise ClosureError("E_ICON_ASSET_PATH", f"/body/icons/{entry.name}/source/address")
            asset_reference = {
                "id": entry.name, "kind": "icon-asset", "store": reference.store,
                "address": entry.source.address, "revision": {"token": reference.revision_token},
                "contentIdentity": entry.source.content_identity,
            }
            try:
                payload = reader.read(asset_reference)
            except SnapshotReadError as error:
                diagnostic = "E_ICON_ASSET_IDENTITY" if error.diagnostic_id == "E_CONTENT_IDENTITY" else "E_ICON_ASSET_MISSING"
                raise ClosureError(diagnostic, f"/body/icons/{entry.name}/source") from error
            try:
                validate_png(payload, entry.viewport)
            except IconNormalizationError as error:
                raise ClosureError(error.diagnostic_id, f"/body/icons/{entry.name}/source") from error
            assets.append(IconAsset(icon_id, entry.kind, entry.source.content_identity, entry.viewport, entry.alternative, payload))
    return tuple(assets)


def _load_draft_icon_assets(catalog_resources: tuple[ClosureResource, ...],
                            catalog_paths: tuple[Path, ...], view: ViewContract,
                            theme_refs: frozenset[str] = frozenset()) -> tuple[IconAsset, ...]:
    """Close exactly the explicit local Draft catalog files and their raster bytes."""
    paths_by_identity = {resource.content_identity: path for resource, path in zip(catalog_resources, catalog_paths)}
    assets: list[IconAsset] = []
    for resource in catalog_resources:
        if not isinstance(resource.contract, IconCatalogContract):
            raise _closure_kind_error(f"draft icon catalog resource id={resource.id}", "IconCatalogContract", resource.contract)
        catalog = resource.contract
        catalog_path = paths_by_identity[resource.content_identity]
        root = catalog_path.parent.resolve()
        for entry in _selected_catalog_entries(catalog, view, theme_refs):
            icon_id = f"{catalog.set_name}:{entry.name}"
            if entry.kind == "vector":
                paths = tuple(NormalizedIconPath(tuple(IconPathCommand(command.kind, command.points)
                                                        for command in _compact_commands(path.data)), path.paint,
                                           path.stroke_width, path.line_cap, path.line_join)
                              for path in entry.paths)
                assets.append(IconAsset(icon_id, entry.kind, resource.content_identity, entry.viewport,
                                        entry.alternative, NormalizedVectorIcon(entry.viewport, paths)))
                continue
            if entry.source is None:
                raise ClosureError("E_ICON_CATALOG_SCHEMA", f"/body/icons/{entry.name}")
            if not _safe_icon_address(entry.source.address):
                raise ClosureError("E_ICON_ASSET_PATH", f"/body/icons/{entry.name}/source/address")
            try:
                path = resolve_store_address(root, entry.source.address)
            except StoreAddressError as error:
                raise ClosureError("E_ICON_ASSET_PATH", f"/body/icons/{entry.name}/source/address") from error
            try:
                payload = path.read_bytes()
            except OSError as error:
                raise ClosureError("E_ICON_ASSET_MISSING", f"/body/icons/{entry.name}/source") from error
            if "sha256:" + sha256(payload).hexdigest() != entry.source.content_identity:
                raise ClosureError("E_ICON_ASSET_IDENTITY", f"/body/icons/{entry.name}/source")
            try:
                validate_png(payload, entry.viewport)
            except IconNormalizationError as error:
                raise ClosureError(error.diagnostic_id, f"/body/icons/{entry.name}/source") from error
            assets.append(IconAsset(icon_id, entry.kind, entry.source.content_identity, entry.viewport,
                                    entry.alternative, payload))
    return tuple(assets)


def _load_reference(reference: dict[str, Any], reader: SnapshotReader, expected_kind: str,
                    decoded_resources: Mapping[str, Any] | None = None) -> ClosureResource:
    source = _load_reference_source(reference, reader, expected_kind, decoded_resources)
    try:
        contract = parse_contract(source.identity, source.value)
    except SchemaContractError as error:
        code = "E_" + expected_kind.upper().replace("-", "_") + "_SCHEMA"
        raise ClosureError(code, error.source_ref, _schema_detail(error)) from error
    except ContractError as error:
        raise ClosureError(error.diagnostic_id, error.source_ref, error.detail) from error
    return ClosureResource(expected_kind, source.identity.id, source.identity.revision, source.identity.content_identity, contract)


def _load_reference_source(reference: dict[str, Any], reader: SnapshotReader, expected_kind: str,
                           decoded_resources: Mapping[str, Any] | None = None) -> PresentationResourceSource:
    """Verify one immutable reference before it joins its known collector set."""
    if reference.get("kind") != expected_kind:
        raise ClosureError("E_CLOSURE_KIND", detail=f"reference id={reference.get('id')!r}; expected kind={expected_kind}; found kind={reference.get('kind')!r}")
    try:
        payload = reader.read(reference)
    except SnapshotReadError as error:
        raise ClosureError(error.diagnostic_id) from error
    computed_identity = f"sha256:{sha256(payload).hexdigest()}"
    value = (decoded_resources or {}).get(computed_identity)
    if value is None:
        value = safe_load(payload)
    if expected_kind == "project":
        actual_id = value.get("project", {}).get("id") if isinstance(value, dict) else None
    elif expected_kind == "profile-package":
        actual_id = value.get("packageId") if isinstance(value, dict) else None
    elif expected_kind == "review-detail-profile":
        if not isinstance(value, dict):
            raise ClosureError("E_CLOSURE_KIND", detail=f"reference id={reference.get('id')!r}; expected review-detail-profile object; found {type(value).__name__}")
        actual_id = value.get("id")
    elif expected_kind == "layout-profile":
        if not isinstance(value, dict):
            raise ClosureError("E_CLOSURE_KIND", detail=f"reference id={reference.get('id')!r}; expected layout-profile object; found {type(value).__name__}")
        actual_id = value.get("id")
    else:
        actual_id = value.get("id") if isinstance(value, dict) else None
        if not isinstance(value, dict) or value.get("kind") != expected_kind:
            raise ClosureError("E_CLOSURE_KIND", detail=f"reference id={reference.get('id')!r}; expected kind={expected_kind}; found kind={value.get('kind') if isinstance(value, dict) else type(value).__name__}")
    if actual_id != reference.get("id"):
        raise ClosureError("E_CLOSURE_ID", detail=f"reference id {reference.get('id')!r} names a {expected_kind} whose own id is {actual_id!r}")
    derived = expected_kind == "theme" and is_derived_theme(value)
    referenced = False
    try:
        if derived:
            value = resolve_snapshot_theme(value, reference, reader)
        referenced = expected_kind == "theme" and uses_references(value)
        if referenced:
            value = resolve_references(value)
    except ThemeInheritanceError as error:
        raise ClosureError(error.code, detail=error.detail or None) from error
    except ThemeReferenceError as error:
        raise ClosureError(error.code, error.pointer, error.detail) from error
    identity = ClosureIdentity(expected_kind, actual_id, reference["revision"]["token"],
                               content_identity(value) if derived or referenced else reference.get("contentIdentity", computed_identity))
    return PresentationResourceSource(identity, value)


def _load_presentation(reference: dict[str, Any], reader: SnapshotReader,
                       decoded_resources: Mapping[str, Any] | None = None) -> RenderContextContract:
    item = _load_reference(reference, reader, "render-context", decoded_resources)
    if not isinstance(item.contract, RenderContextContract):
        raise _closure_kind_error(f"presentation resource id={item.id}", "RenderContextContract", item.contract)
    return item.contract
