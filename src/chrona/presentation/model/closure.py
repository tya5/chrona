"""Immutable Render Context closure resolution before any rendering adapter runs."""
from __future__ import annotations

from difflib import get_close_matches
from dataclasses import dataclass
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

import jsonschema  # Kept as the closure module's validator seam for snapshot tests.
import yaml


from chrona.presentation.color_scheme import ColorSchemeError, resolve_theme
from chrona.presentation.icons import IconNormalizationError, IconPathCommand, NormalizedIconPath, NormalizedVectorIcon, validate_png
from chrona.presentation.contracts import (
    ActualSetContract, AuthoringWorkspaceContract, ClosureIdentity, ContractError, SchemaContractError, IconCatalogContract, IconEntry, IconPath, LayoutProfileContract,
    PresentationPresetContract,
    ProfilePackageContract, ProjectContract, RenderContextContract,
    ResolvedThemeContract, ResourceContract, ReviewDetailProfileContract,
    SnapshotRefContract, SummaryProfileContract, TypesetterIdentity, ViewContract,
    PresentationIngressRejected, PresentationResourceSource, collect_presentation_contracts,
    freeze, parse_contract, validate_icon_catalog_entry, IconRasterSource,
)
from chrona.presentation.model.authoring import AuthoringError, normalize_authoring_workspace
from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView
from chrona.presentation.fonts.system import DraftFontResolution, SystemFontError, SystemFontResolver, resolve_draft_font, resolve_system_font
from chrona.presentation.contracts.resources import FrozenDict, FrozenList, _compact_commands
from chrona.core.ports import SnapshotReadError, SnapshotReader
from chrona.resources import safe_load


class ClosureError(ValueError):
    def __init__(self, diagnostic_id: str, source_ref: str = "/", detail: str | None = None):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id
        self.source_ref = source_ref
        self.detail = detail


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
            raise ClosureError("E_CLOSURE_REQUIRED")
        if not isinstance(item.contract, ProjectContract):
            raise self._kind_error(item, ProjectContract)
        return item.contract

    @property
    def view(self) -> ViewContract:
        item = self.resource("view")
        if item is None:
            raise ClosureError("E_CLOSURE_REQUIRED")
        if not isinstance(item.contract, ViewContract):
            raise self._kind_error(item, ViewContract)
        return item.contract

    @property
    def layout_profile(self) -> LayoutProfileContract:
        item = self.resource("layout-profile")
        if item is None:
            raise ClosureError("E_CLOSURE_REQUIRED")
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
            raise ClosureError("E_ICON_REFERENCE")
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


def resolve_draft_render(
    *, project_path: Path, view_path: Path | None = None, theme_path: Path | None = None, scheme_path: Path | None = None,
    layout_path: Path | None = None, preset_path: Path | None = None, preset_root: Path | None = None, actual_path: Path | None = None, summary_path: Path | None = None,
    detail_path: Path | None = None, icon_catalog_paths: tuple[Path, ...] = (),
    font_metrics_path: Path | None = None,
    system_fonts: bool = False,
    system_font_resolver: SystemFontResolver | None = None,
    viewport: tuple[int, int | None] = (1600, 900),
    locale: str = "en-US", target_kind: str = "svg", visual_profile: str = "chrona-output/visual/v0.5-baseline", typesetter: TypesetterIdentity | None = None,
) -> DraftRender:
    """Build a typed, in-memory closure from explicit authoring inputs.

    This is deliberately an ingress adapter, not an alternate render pipeline:
    its identities are marked ``draft`` and it creates no Context or snapshot
    artifact.  Once returned, the normal review use case cannot distinguish it
    from an immutable closure.
    """
    preset_paths = _draft_preset_paths(preset_path, preset_root) if preset_path is not None else {}
    paths = (("project", project_path),
             ("view", view_path or preset_paths.get("view")),
             ("theme", theme_path or preset_paths.get("theme")),
             ("color-scheme", scheme_path or preset_paths.get("color-scheme")),
             ("layout-profile", layout_path or preset_paths.get("layout-profile")))
    if any(path is None for _kind, path in paths):
        raise ClosureError("E_DRAFT_PRESENTATION_INCOMPLETE")
    optional = (
        ("actual-set", actual_path), ("summary-profile", summary_path),
        ("review-detail-profile", detail_path),
    )
    sources = [_load_draft_source(kind, path) for kind, path in paths if path is not None]
    sources.extend(_load_draft_source(kind, path) for kind, path in optional if path is not None)
    sources.extend(_load_draft_source("icon-catalog", path) for path in icon_catalog_paths)
    resources = _collect_presentation_resources(sources)
    catalog_resources = tuple(resource for resource in resources if resource.kind == "icon-catalog")
    _validate_icon_catalog_set(catalog_resources)
    return _draft_render_from_resources(resources, viewport=viewport, locale=locale, target_kind=target_kind,
                                        visual_profile=visual_profile, typesetter=typesetter,
                                        icon_assets=_load_draft_icon_assets(catalog_resources, icon_catalog_paths,
                                                                            _draft_view(resources)),
                                        font_metrics=(safe_load(font_metrics_path.read_bytes()) if font_metrics_path else None),
                                        font_asset_root=(font_metrics_path.parent.resolve() if font_metrics_path else None),
                                        system_fonts=system_fonts, system_font_resolver=system_font_resolver)


def _draft_preset_paths(preset_path: Path, preset_root: Path | None = None) -> dict[str, Path]:
    """Resolve one explicit preset into safe ordinary-resource paths."""
    preset = _load_draft_resource("presentation-preset", preset_path)
    if not isinstance(preset.contract, PresentationPresetContract):
        raise ClosureError("E_DRAFT_PRESET_SCHEMA")
    mapping = {"view": "view", "theme": "theme", "colorScheme": "color-scheme", "layout": "layout-profile"}
    paths: dict[str, Path] = {}
    for name, kind in mapping.items():
        declaration = preset.contract.resources.get(name)
        if not isinstance(declaration, Mapping):
            raise ClosureError("E_DRAFT_PRESET_SCHEMA")
        path = _declared_child(preset_root or preset_path.parent, str(declaration["path"]))
        resource = _load_draft_resource(kind, path)
        if resource.id != declaration["id"]:
            raise ClosureError("E_DRAFT_PRESET_RESOURCE")
        paths[kind] = path
    return paths


def resolve_guided_draft_render(
    *, workspace_path: Path, viewport: tuple[int, int | None] = (1600, 900),
    locale: str = "en-US", target_kind: str = "svg", visual_profile: str = "chrona-output/visual/v0.5-baseline", typesetter: TypesetterIdentity | None = None,
) -> DraftRender:
    """Resolve one guided Draft without creating files or a second render pipeline."""
    workspace_resource = _load_draft_resource("authoring-workspace", workspace_path)
    if not isinstance(workspace_resource.contract, AuthoringWorkspaceContract):
        raise ClosureError("E_AUTHORING_WORKSPACE_SCHEMA")
    preset_selector = workspace_resource.contract.binding["preset"]
    preset_path = _declared_child(workspace_path.parent, str(preset_selector["path"]))
    preset_resource = _load_draft_resource("presentation-preset", preset_path)
    if not isinstance(preset_resource.contract, PresentationPresetContract):
        raise ClosureError("E_AUTHORING_PRESET_SCHEMA")
    resource_declarations = (*preset_resource.contract.resources.values(), *preset_resource.contract.compatible_color_schemes)
    resources_by_path = {
        str(declaration["path"]): safe_load(_declared_child(preset_path.parent, str(declaration["path"])).read_bytes())
        for declaration in resource_declarations if isinstance(declaration, Mapping)
    }
    if not all(isinstance(value, dict) for value in resources_by_path.values()):
        raise ClosureError("E_AUTHORING_PRESET_RESOURCE")
    try:
        normalized = normalize_authoring_workspace(workspace_resource.contract, preset_resource.contract, resources_by_path)
    except (AuthoringError, ContractError) as error:
        raise ClosureError(str(error)) from error
    sources = [_normalized_draft_source(kind, source) for kind, source in normalized.draft_sources()]
    catalog_declarations = preset_resource.contract.resources.get("iconCatalogs", ())
    if not isinstance(catalog_declarations, (tuple, list)):
        raise ClosureError("E_AUTHORING_PRESET_RESOURCE")
    catalog_paths = tuple(_declared_child(preset_path.parent, str(item["path"])) for item in catalog_declarations)
    sources.extend(_load_draft_source("icon-catalog", path) for path in catalog_paths)
    resources = _collect_presentation_resources(sources)
    catalog_resources = tuple(resource for resource in resources if resource.kind == "icon-catalog")
    if any(resource.id != declaration["id"] for resource, declaration in zip(catalog_resources, catalog_declarations)):
        raise ClosureError("E_AUTHORING_PRESET_RESOURCE")
    _validate_icon_catalog_set(catalog_resources)
    binding_identity = "sha256:" + sha256(yaml.safe_dump(_plain_value(workspace_resource.contract.binding), sort_keys=True).encode()).hexdigest()
    provenance = GuidedAuthoringProvenance(workspace_resource.content_identity, preset_resource.content_identity, binding_identity)
    return _draft_render_from_resources(resources, viewport=viewport, locale=locale, target_kind=target_kind,
                                        visual_profile=visual_profile, typesetter=typesetter, provenance=provenance,
                                        icon_assets=_load_draft_icon_assets(catalog_resources, catalog_paths,
                                                                            _draft_view(resources)))


def _declared_child(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    if root.resolve() not in candidate.parents:
        raise ClosureError("E_AUTHORING_PRESET_PATH")
    return candidate


def _draft_view(resources: list[ClosureResource]) -> ViewContract:
    view = next((resource.contract for resource in resources if resource.kind == "view"), None)
    if not isinstance(view, ViewContract):
        raise _closure_kind_error("draft resources", "ViewContract", view)
    return view


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
        raise ClosureError("E_AUTHORING_NORMALIZATION")
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
        resolved_theme = ResolvedThemeContract(
            by_kind["theme"].id,
            freeze(resolve_theme(
                by_kind["theme"].contract.theme_input,
                by_kind["color-scheme"].contract.scheme_input,
                scheme_content_identity=by_kind["color-scheme"].content_identity,
            )),
        )
    except ColorSchemeError as error:
        raise ClosureError(error.diagnostic_id, error.source_ref, error.detail) from error

    asset_root = Path(__file__).resolve().parents[2] / "resources"
    typesetter_environment = _draft_typesetter(target_kind, typesetter)
    if system_fonts and font_metrics is not None:
        raise ClosureError("E_FONT_SYSTEM_MISMATCH", detail="--system-fonts cannot be combined with --font-metrics")
    resolution = (_draft_system_font_resolution(resolved_theme.resolved_input, system_font_resolver or resolve_system_font)
                  if system_fonts else None)
    if resolution is not None and target_kind not in {"svg", "png"}:
        raise ClosureError("E_FONT_SYSTEM_IMMUTABLE", detail=f"draft system fonts do not support {target_kind}")
    context_value = {
            "version": "chrona/render-context/v0.16", "kind": "render-context", "id": "draft-render",
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


def _draft_system_font_resolution(theme: Mapping[str, Any], resolver: SystemFontResolver) -> DraftFontResolution:
    """Resolve the one face the current measurement contract can represent."""
    try:
        typography = ThemeTokenView(theme)
        roles = theme.get("body", {}).get("roles", {})
        requests = {
            (typography.font_family(role).split(",", 1)[0].strip(), typography.font_weight(role))
            for role, binding in roles.items()
            if isinstance(binding, Mapping) and "fontFamily" in binding and "fontWeight" in binding
        }
    except (AttributeError, ThemeTokenError, TypeError, ValueError) as error:
        raise ClosureError("E_FONT_SYSTEM_MISMATCH", detail="Theme typography cannot select one system face") from error
    if len(requests) != 1:
        values = ", ".join(f"{family}/{weight}" for family, weight in sorted(requests))
        raise ClosureError("E_FONT_SYSTEM_MISMATCH", detail=f"multiple Theme faces: {values}")
    family, weight = next(iter(requests))
    if not family:
        raise ClosureError("E_FONT_SYSTEM_MISSING", detail="Theme primary font family is empty")
    try:
        return resolve_draft_font(resolver(family, weight))
    except SystemFontError as error:
        raise ClosureError(error.code, detail=error.detail) from error


def _load_draft_resource(kind: str, path: Path) -> ClosureResource:
    """Read one explicit draft input and freeze it through its resource contract."""
    value = safe_load(path.read_bytes())
    if not isinstance(value, dict):
        raise ClosureError("E_" + kind.upper().replace("-", "_") + "_SCHEMA")
    identifier = _resource_id(kind, value)
    if not isinstance(identifier, str) or not identifier:
        raise ClosureError("E_" + kind.upper().replace("-", "_") + "_SCHEMA")
    payload = path.read_bytes()
    identity = ClosureIdentity(kind, identifier, "draft", "sha256:" + sha256(payload).hexdigest())
    try:
        contract = parse_contract(identity, value)
    except SchemaContractError as error:
        raise ClosureError("E_" + kind.upper().replace("-", "_") + "_SCHEMA", error.source_ref, _schema_detail(error)) from error
    except ContractError as error:
        raise ClosureError(error.diagnostic_id, detail=error.detail) from error
    return ClosureResource(kind, identifier, "draft", identity.content_identity, contract)


def _load_draft_source(kind: str, path: Path) -> PresentationResourceSource:
    """Read one declared Draft file without allowing it into typed closure yet."""
    payload = path.read_bytes()
    value = safe_load(payload)
    if not isinstance(value, dict):
        raise ClosureError("E_" + kind.upper().replace("-", "_") + "_SCHEMA")
    identifier = _resource_id(kind, value)
    if not isinstance(identifier, str) or not identifier:
        raise ClosureError("E_" + kind.upper().replace("-", "_") + "_SCHEMA")
    identity = ClosureIdentity(kind, identifier, "draft", "sha256:" + sha256(payload).hexdigest())
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
        raise ClosureError("E_FONT_METRICS_UNAVAILABLE")
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
            raise ClosureError("E_RENDER_TYPESETTER_DESCRIPTOR")
        return None
    if typesetter is None:
        raise ClosureError("E_RENDER_TYPESETTER_DESCRIPTOR")
    return {"engine": typesetter.engine, "version": typesetter.version,
            "adapterGrammar": typesetter.adapter_grammar}


def resolve_render_context(reference: dict[str, Any], reader: SnapshotReader,
                           *, decoded_resources: Mapping[str, Any] | None = None) -> RenderClosure:
    context = _load_presentation(reference, reader, decoded_resources)
    if context.version != "chrona/render-context/v0.16":
        raise ClosureError("E_RENDER_CONTEXT_SCHEMA")
    return _resolve_layout_context(context, reader, decoded_resources)


def _resolve_layout_context(context_contract: RenderContextContract, reader: SnapshotReader,
                            decoded_resources: Mapping[str, Any] | None = None) -> RenderClosure:
    if context_contract.environment.font_metrics.get("missingFont") != "diagnose":
        raise ClosureError("E_FONT_SUBSTITUTE_CONTEXT")
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
                raise ClosureError("E_CLOSURE_REQUIRED")
            if package.contract.package_id != extension.get("packageId"):
                raise ClosureError("E_CLOSURE_ID")
    if context_contract.snapshot is not None:
        snapshot = _load_reference(context_contract.snapshot.as_reader_reference(), reader, "snapshot-ref", decoded_resources)
        snapshot_project = _load_reference(snapshot.contract.project.as_reader_reference(), reader, "project", decoded_resources)
        if snapshot_project.id != resources[0].id:
            raise ClosureError("E_CLOSURE_ID")
        resources.extend((snapshot, ClosureResource(
            "snapshot-project", snapshot_project.id, snapshot_project.revision,
            snapshot_project.content_identity, snapshot_project.contract)))
    if context_contract.target.capabilities != tuple(sorted(context_contract.target.capabilities)):
        raise ClosureError("E_TARGET_CAPABILITY_ORDER")
    theme, scheme = resources[2], resources[3]
    try:
        value = resolve_theme(theme.contract.theme_input, scheme.contract.scheme_input, scheme_content_identity=scheme.content_identity)
        resolved_theme = ResolvedThemeContract(theme.id, freeze(value))
    except ColorSchemeError as error:
        raise ClosureError(error.diagnostic_id, error.source_ref, error.detail) from error
    catalog_resources = tuple(item for item in resources if item.kind == "icon-catalog")
    _validate_icon_catalog_set(catalog_resources)
    if catalog_resources:
        view_contract = resources[1].contract
        if not isinstance(view_contract, ViewContract):
            raise _closure_kind_error("resolved View resource", "ViewContract", view_contract)
        icon_assets = _load_icon_assets(context_contract, catalog_resources, reader, view_contract)
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
            raise ClosureError("E_ICON_SET_AMBIGUOUS")
        namespaces.update(names)


def _safe_icon_address(address: str) -> bool:
    path = PurePosixPath(address)
    return bool(address and address == path.as_posix() and not path.is_absolute()
                and all(part not in {"", ".", ".."} for part in path.parts))


def _selected_icon_references(view: ViewContract) -> set[str]:
    selected: set[str] = set()
    for visual in view.view.visuals:
        if visual.ref is not None:
            selected.add(visual.ref)
        if visual.encoding is not None:
            selected.update(str(item) for item in visual.encoding.get("domain", {}).values())
    return selected


def _selected_icon_entry(catalog: IconCatalogContract, name: str) -> IconEntry:
    try:
        validate_icon_catalog_entry(catalog, name)
    except ContractError as error:
        raise ClosureError("E_ICON_CATALOG_SCHEMA", f"/body/icons/{name}") from error
    raw = catalog.raw_icons[name]
    viewport, paths, source = raw["viewport"], raw.get("paths", ()), raw.get("source")
    if not isinstance(viewport, FrozenDict) or not isinstance(paths, (FrozenList, tuple)):
        raise ClosureError("E_ICON_CATALOG_SCHEMA")
    normalized = tuple(IconPath(str(path["paint"]), str(path["data"]),
                                float(path["strokeWidth"]) if "strokeWidth" in path else None,
                                str(path["lineCap"]) if "lineCap" in path else None,
                                str(path["lineJoin"]) if "lineJoin" in path else None)
                       for path in paths if isinstance(path, FrozenDict))
    if len(normalized) != len(paths):
        raise ClosureError("E_ICON_CATALOG_SCHEMA")
    source_value = raw.get("source")
    source = None
    if source_value is not None:
        if not isinstance(source_value, FrozenDict):
            raise ClosureError("E_ICON_CATALOG_SCHEMA")
        source = IconRasterSource(str(source_value["address"]), str(source_value["contentIdentity"]))
    return IconEntry(name, str(raw["kind"]), (int(viewport["inlineSize"]), int(viewport["blockSize"])),
                     str(raw["alternative"]), normalized, source)


def _selected_catalog_entries(catalog: IconCatalogContract, view: ViewContract) -> tuple[IconEntry, ...]:
    names: set[str] = set()
    for reference in _selected_icon_references(view):
        if reference.count(":") != 1:
            continue
        set_name, name = reference.split(":", 1)
        if set_name in {catalog.set_name, *catalog.aliases}:
            canonical = str(catalog.entry_aliases.get(name, name))
            if canonical in catalog.raw_icons:
                names.add(canonical)
    return tuple(_selected_icon_entry(catalog, name) for name in sorted(names))


def _load_icon_assets(context: RenderContextContract, catalog_resources: tuple[ClosureResource, ...],
                      reader: SnapshotReader, view: ViewContract) -> tuple[IconAsset, ...]:
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
        entries = _selected_catalog_entries(catalog, view)
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
                            catalog_paths: tuple[Path, ...], view: ViewContract) -> tuple[IconAsset, ...]:
    """Close exactly the explicit local Draft catalog files and their raster bytes."""
    paths_by_identity = {resource.content_identity: path for resource, path in zip(catalog_resources, catalog_paths)}
    assets: list[IconAsset] = []
    for resource in catalog_resources:
        if not isinstance(resource.contract, IconCatalogContract):
            raise _closure_kind_error(f"draft icon catalog resource id={resource.id}", "IconCatalogContract", resource.contract)
        catalog = resource.contract
        catalog_path = paths_by_identity[resource.content_identity]
        root = catalog_path.parent.resolve()
        for entry in _selected_catalog_entries(catalog, view):
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
            path = (root / entry.source.address).resolve()
            if root not in path.parents:
                raise ClosureError("E_ICON_ASSET_PATH", f"/body/icons/{entry.name}/source/address")
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
        raise ClosureError(error.diagnostic_id, detail=error.detail) from error
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
        if not isinstance(value, dict) or value.get("version") != "chrona/review-detail-profile/v0.1":
            raise ClosureError("E_CLOSURE_KIND", detail=f"reference id={reference.get('id')!r}; expected chrona/review-detail-profile/v0.1 object; found {value!r}")
        actual_id = value.get("id")
    elif expected_kind == "layout-profile":
        if not isinstance(value, dict) or value.get("version") != "chrona/layout-profile/v0.9":
            raise ClosureError("E_CLOSURE_KIND", detail=f"reference id={reference.get('id')!r}; expected chrona/layout-profile/v0.9 object; found {value!r}")
        actual_id = value.get("id")
    else:
        actual_id = value.get("id") if isinstance(value, dict) else None
        expected_version_prefix = f"chrona/{expected_kind}/v"
        if (not isinstance(value, dict) or value.get("kind") != expected_kind
                or not str(value.get("version", "")).startswith(expected_version_prefix)):
            raise ClosureError("E_CLOSURE_KIND", detail=f"reference id={reference.get('id')!r}; expected kind={expected_kind} version prefix={expected_version_prefix}; found {value!r}")
    if actual_id != reference.get("id"):
        raise ClosureError("E_CLOSURE_ID")
    identity = ClosureIdentity(expected_kind, actual_id, reference["revision"]["token"], reference.get("contentIdentity", computed_identity))
    return PresentationResourceSource(identity, value)


def _load_presentation(reference: dict[str, Any], reader: SnapshotReader,
                       decoded_resources: Mapping[str, Any] | None = None) -> RenderContextContract:
    item = _load_reference(reference, reader, "render-context", decoded_resources)
    if not isinstance(item.contract, RenderContextContract):
        raise _closure_kind_error(f"presentation resource id={item.id}", "RenderContextContract", item.contract)
    return item.contract
