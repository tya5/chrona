"""Immutable Render Context closure resolution before any rendering adapter runs."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from typing import Any

import jsonschema  # Kept as the closure module's validator seam for snapshot tests.
import yaml


from chrona.presentation.color_scheme import ColorSchemeError, resolve_theme
from chrona.presentation.contracts import (
    ActualSetContract, ClosureIdentity, ContractError, SchemaContractError, LayoutProfileContract,
    ProfilePackageContract, ProjectContract, RenderContextContract,
    ResolvedThemeContract, ResourceContract, ReviewDetailProfileContract,
    SnapshotRefContract, SummaryProfileContract, ViewContract,
    freeze, parse_contract,
)
from chrona.core.ports import SnapshotReadError, SnapshotReader


class ClosureError(ValueError):
    def __init__(self, diagnostic_id: str, source_ref: str = "/"):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id
        self.source_ref = source_ref


@dataclass(frozen=True)
class ClosureResource:
    kind: str
    id: str
    revision: str
    content_identity: str
    contract: ResourceContract

@dataclass(frozen=True)
class RenderClosure:
    context: RenderContextContract
    resources: tuple[ClosureResource, ...]
    resolved_theme: ResolvedThemeContract

    def resource(self, kind: str) -> ClosureResource | None:
        return next((item for item in self.resources if item.kind == kind), None)

    @property
    def project(self) -> ProjectContract:
        item = self.resource("project")
        if item is None:
            raise ClosureError("E_CLOSURE_REQUIRED")
        if not isinstance(item.contract, ProjectContract):
            raise ClosureError("E_CLOSURE_KIND")
        return item.contract

    @property
    def view(self) -> ViewContract:
        item = self.resource("view")
        if item is None:
            raise ClosureError("E_CLOSURE_REQUIRED")
        if not isinstance(item.contract, ViewContract):
            raise ClosureError("E_CLOSURE_KIND")
        return item.contract

    @property
    def layout_profile(self) -> LayoutProfileContract:
        item = self.resource("layout-profile")
        if item is None:
            raise ClosureError("E_CLOSURE_REQUIRED")
        if not isinstance(item.contract, LayoutProfileContract):
            raise ClosureError("E_CLOSURE_KIND")
        return item.contract

    def _optional(self, kind: str, expected: type[ResourceContract]) -> ResourceContract | None:
        item = self.resource(kind)
        if item is None:
            return None
        if not isinstance(item.contract, expected):
            raise ClosureError("E_CLOSURE_KIND")
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
            raise ClosureError("E_CLOSURE_KIND")
        return values  # type: ignore[return-value]


@dataclass(frozen=True)
class DraftRender:
    """A non-evidence closure and the packaged assets it is allowed to read."""

    closure: RenderClosure
    asset_root: Path


_DRAFT_CAPABILITIES = (
    "accessibleText", "hierarchicalAxis", "marker", "semanticRoles", "sourceMetadata",
    "tableSemantics",
)


def resolve_draft_render(
    *, project_path: Path, view_path: Path, theme_path: Path, scheme_path: Path,
    layout_path: Path, actual_path: Path | None = None, summary_path: Path | None = None,
    detail_path: Path | None = None, viewport: tuple[int, int] = (1600, 900),
    locale: str = "en-US", target_kind: str = "svg",
) -> DraftRender:
    """Build a typed, in-memory closure from explicit authoring inputs.

    This is deliberately an ingress adapter, not an alternate render pipeline:
    its identities are marked ``draft`` and it creates no Context or snapshot
    artifact.  Once returned, the normal review use case cannot distinguish it
    from an immutable closure.
    """
    paths = (
        ("project", project_path), ("view", view_path), ("theme", theme_path),
        ("color-scheme", scheme_path), ("layout-profile", layout_path),
    )
    optional = (
        ("actual-set", actual_path), ("summary-profile", summary_path),
        ("review-detail-profile", detail_path),
    )
    resources = [_load_draft_resource(kind, path) for kind, path in paths]
    resources.extend(_load_draft_resource(kind, path) for kind, path in optional if path is not None)
    by_kind = {item.kind: item for item in resources}

    try:
        resolved_theme = ResolvedThemeContract(
            by_kind["theme"].id,
            freeze(resolve_theme(
                by_kind["theme"].contract.document,
                by_kind["color-scheme"].contract.document,
                scheme_content_identity=by_kind["color-scheme"].content_identity,
            )),
        )
    except ColorSchemeError as error:
        raise ClosureError(str(error)) from error

    asset_root = Path(__file__).resolve().parents[2] / "resources"
    context_value = {
        "version": "chrona/render-context/v0.7", "kind": "render-context", "id": "draft-render",
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
            },
            "environment": {
                "viewport": {"inlineSize": viewport[0], "blockSize": viewport[1]},
                "locale": locale,
                "fontMetrics": _packaged_font_metrics(asset_root),
                "scenePrecision": 3,
                **({"rasterizer": _draft_rasterizer(target_kind)} if target_kind in {"png", "pdf"} else {}),
            },
            "target": {"kind": target_kind, "capabilities": list(_DRAFT_CAPABILITIES) if target_kind == "svg" else []},
        },
    }
    try:
        context = parse_contract(
            ClosureIdentity("render-context", "draft-render", "draft", "draft"), context_value
        )
    except SchemaContractError as error:
        raise ClosureError("E_RENDER_CONTEXT_SCHEMA", error.source_ref) from error
    except ContractError as error:
        raise ClosureError("E_RENDER_CONTEXT_SCHEMA") from error
    if not isinstance(context, RenderContextContract):  # defensive contract boundary
        raise ClosureError("E_CLOSURE_KIND")
    return DraftRender(RenderClosure(context, tuple(resources), resolved_theme), asset_root)


def _load_draft_resource(kind: str, path: Path) -> ClosureResource:
    """Read one explicit draft input and freeze it through its resource contract."""
    value = yaml.safe_load(path.read_bytes())
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
        raise ClosureError("E_" + kind.upper().replace("-", "_") + "_SCHEMA", error.source_ref) from error
    except ContractError as error:
        raise ClosureError(str(error)) from error
    return ClosureResource(kind, identifier, "draft", identity.content_identity, contract)


def _resource_id(kind: str, value: dict[str, Any]) -> object:
    return value.get("project", {}).get("id") if kind == "project" and isinstance(value.get("project"), dict) else value.get("id")


def _draft_reference(resource: ClosureResource) -> dict[str, Any]:
    return {
        "id": resource.id, "kind": resource.kind,
        "store": {"provider": "draft", "identity": "draft"},
        "address": resource.kind, "revision": {"token": "draft"},
        "contentIdentity": resource.content_identity,
    }


def _packaged_font_metrics(asset_root: Path) -> dict[str, Any]:
    path = asset_root / "font_metrics" / "nimbus-sans-regular-v1.json"
    return {"algorithm": "declared-metrics-v1", "assets": [{
        "family": "Nimbus Sans", "weight": 400, "revision": "nimbus-sans-regular-v1",
        "contentIdentity": "sha256:" + sha256(path.read_bytes()).hexdigest(),
        "path": "font_metrics/nimbus-sans-regular-v1.json",
    }], "missingFont": "declared-fallback"}


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


def resolve_render_context(reference: dict[str, Any], reader: SnapshotReader) -> RenderClosure:
    context = _load_presentation(reference, reader)
    if context.get("version") != "chrona/render-context/v0.7":
        raise ClosureError("E_RENDER_CONTEXT_SCHEMA")
    return _resolve_layout_context(context, reader)


def _resolve_layout_context(
    context: dict[str, Any], reader: SnapshotReader
) -> RenderClosure:
    try:
        context_contract = parse_contract(
            ClosureIdentity("render-context", str(context["id"]), "", ""), context
        )
    except SchemaContractError as error:
        raise ClosureError("E_RENDER_CONTEXT_SCHEMA", error.source_ref) from error
    except ContractError as error:
        raise ClosureError("E_RENDER_CONTEXT_SCHEMA") from error
    body = context_contract.body
    ordered = (
        (body["project"], "project"),
        (body["view"], "view"),
        (body["theme"], "theme"),
        (body["colorScheme"], "color-scheme"),
        (body["layout"], "layout-profile"),
    )
    resources = [_load_reference(reference, reader, kind) for reference, kind in ordered]
    for extension in resources[0].contract.document.get("extensions", []):
        package_reference = extension.get("resource")
        if package_reference is not None:
            package = _load_reference(package_reference, reader, "profile-package")
            if package.contract.document.get("packageId") != extension.get("packageId"):
                raise ClosureError("E_CLOSURE_ID")
            resources.append(package)
    for name, kind in (("actual", "actual-set"), ("summaryProfile", "summary-profile"), ("detailProfile", "review-detail-profile")):
        if name in body["inputs"]:
            resources.append(_load_reference(body["inputs"][name], reader, kind))
    if "snapshot" in body["inputs"]:
        snapshot = _load_reference(body["inputs"]["snapshot"], reader, "snapshot-ref")
        project_reference = snapshot.contract.document.get("body", {}).get("project")
        if not isinstance(project_reference, dict):
            raise ClosureError("E_CLOSURE_KIND")
        snapshot_project = _load_reference(project_reference, reader, "project")
        if snapshot_project.id != resources[0].id:
            raise ClosureError("E_CLOSURE_ID")
        resources.extend((snapshot, ClosureResource(
            "snapshot-project", snapshot_project.id, snapshot_project.revision,
            snapshot_project.content_identity, snapshot_project.contract)))
    if body["target"]["capabilities"] != sorted(body["target"]["capabilities"]):
        raise ClosureError("E_TARGET_CAPABILITY_ORDER")
    theme, scheme = resources[2], resources[3]
    try:
        value = resolve_theme(theme.contract.document, scheme.contract.document, scheme_content_identity=scheme.content_identity)
        resolved_theme = ResolvedThemeContract(theme.id, freeze(value))
    except ColorSchemeError as error:
        raise ClosureError(str(error)) from error
    return RenderClosure(context_contract, tuple(resources), resolved_theme)


def _load_reference(reference: dict[str, Any], reader: SnapshotReader, expected_kind: str) -> ClosureResource:
    if reference.get("kind") != expected_kind:
        raise ClosureError("E_CLOSURE_KIND")
    try:
        payload = reader.read(reference)
    except SnapshotReadError as error:
        raise ClosureError(error.diagnostic_id) from error
    computed_identity = f"sha256:{sha256(payload).hexdigest()}"
    value = yaml.safe_load(payload)
    if expected_kind == "project":
        actual_id = value.get("project", {}).get("id") if isinstance(value, dict) else None
    elif expected_kind == "profile-package":
        actual_id = value.get("packageId") if isinstance(value, dict) else None
    elif expected_kind == "review-detail-profile":
        if not isinstance(value, dict) or value.get("version") != "chrona/review-detail-profile/v0.1":
            raise ClosureError("E_CLOSURE_KIND")
        actual_id = value.get("id")
    elif expected_kind == "layout-profile":
        if not isinstance(value, dict) or value.get("version") != "chrona/layout-profile/v0.2":
            raise ClosureError("E_CLOSURE_KIND")
        actual_id = value.get("id")
    else:
        actual_id = value.get("id") if isinstance(value, dict) else None
        expected_version_prefix = f"chrona/{expected_kind}/v"
        if (not isinstance(value, dict) or value.get("kind") != expected_kind
                or not str(value.get("version", "")).startswith(expected_version_prefix)):
            raise ClosureError("E_CLOSURE_KIND")
    if actual_id != reference.get("id"):
        raise ClosureError("E_CLOSURE_ID")
    identity = ClosureIdentity(expected_kind, actual_id, reference["revision"]["token"], reference.get("contentIdentity", computed_identity))
    try:
        contract = parse_contract(identity, value)
    except SchemaContractError as error:
        code = "E_" + expected_kind.upper().replace("-", "_") + "_SCHEMA"
        raise ClosureError(code, error.source_ref) from error
    except ContractError as error:
        raise ClosureError(error.args[0]) from error
    return ClosureResource(expected_kind, actual_id, identity.revision, identity.content_identity, contract)


def _load_presentation(reference: dict[str, Any], reader: SnapshotReader) -> dict[str, Any]:
    item = _load_reference(reference, reader, "render-context")
    return item.contract.document
