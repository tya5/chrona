"""Immutable example/context materialization application service."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
import json
import shutil
import tempfile
from types import MappingProxyType
from collections.abc import Mapping
from typing import Any

import yaml

from chrona.presentation.contracts.resources import ClosureIdentity, RENDER_CONTEXT_VERSIONS, parse_contract
from chrona.presentation.contracts.font_sets import expand_font_set
from chrona.presentation.model.closure import resolve_render_context
from chrona.presentation.model.font_resources import FontProviderUnavailable, FontResourceError, resolve_font_resource
from chrona.presentation.model.theme_inheritance import ThemeInheritanceError, is_derived_theme, theme_base_reference
from chrona.resources import safe_load
from chrona.presentation.renderers.registry import renderer_for
from chrona.core.ports import SnapshotReadError
from chrona.core.store_address import StoreAddressError, check_store_address, check_store_segment, resolve_store_address
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.storage.snapshot_paths import snapshot_directory
from chrona.usecases.render_review import RenderRequest, RenderedReview, render_review
from chrona.usecases.deck_context import SelectedDeckContext, load_deck_manifest, select_deck_context
from chrona.presentation.scene.serialization import SceneSerializationError, serialize_scene


@dataclass(frozen=True)
class MaterializationResult:
    output: Path
    closure_reference: dict[str, Any]
    rendered: RenderedReview


class MaterializationError(ValueError):
    """A materializer failure with a stable code and boundary-neutral detail."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code, self.detail = code, detail


class UnavailableFontProviders(MaterializationError):
    """A valid Context depends on one or more uninstalled package font providers."""

    def __init__(self, providers: tuple[str, ...]):
        self.providers = providers
        super().__init__("E_MATERIALIZER_FONT", "unavailable package font providers: " + ", ".join(providers))


@dataclass(frozen=True)
class _ResolvedFontAsset:
    locator: dict[str, Any]
    content_identity: str | None  # the authored pin; None when the author supplied none
    address: str
    provider: str
    payload: bytes


def _font_copy_plan(body: dict[str, Any], example: Path) -> tuple[_ResolvedFontAsset, ...]:
    """Resolve and verify every available font asset before the caller stages any of them."""
    plan: list[_ResolvedFontAsset] = []
    unavailable: set[str] = set()
    keys = ("metrics",) if body["target"]["kind"] == "svg" else ("metrics", "font")
    for asset in body["environment"]["fontMetrics"]["assets"]:
        for key in keys:
            record = asset.get(key, {})
            locator = record["locator"]
            try:
                source = resolve_font_resource(locator, asset_root=example)
            except FontProviderUnavailable as error:
                unavailable.add(error.identity)
                continue
            except FontResourceError as error:
                raise ValueError(f"E_MATERIALIZER_FONT: cannot resolve {key} asset for {_label(asset.get('id', '<unknown>'))} at {_label(locator.get('address'))}: {error}; {_label(error.detail)}") from error
            payload = source.read_bytes()
            if record.get("contentIdentity") is not None and record["contentIdentity"] != _identity(payload):  # a pin is optional; a supplied one is verified (#1567)
                raise ValueError(f"E_MATERIALIZER_FONT_IDENTITY: fontMetrics asset {_label(asset.get('id', '<unknown>'))} field {key} at {_label(locator.get('address'))}; expected {_label(record.get('contentIdentity'))}, found {_identity(payload)}")
            address = locator.get("address")
            if not isinstance(address, str):
                raise ValueError(f"E_MATERIALIZER_FONT: fontMetrics asset {_label(asset.get('id', '<unknown>'))} field {key} locator requires string address, found {_label(address)}")
            provider = locator.get("provider")
            plan.append(_ResolvedFontAsset(locator, record.get("contentIdentity"), address, provider, payload))
    if unavailable:
        raise UnavailableFontProviders(tuple(sorted(unavailable)))
    return tuple(plan)


def _context_error(scope: str, expected: str, actual: object) -> MaterializationError:
    if isinstance(actual, dict):
        found = f"object with keys {sorted(_label(key) for key in actual)}"
    elif isinstance(actual, (list, tuple)):
        found = f"{type(actual).__name__} of length {len(actual)}"
    else:
        found = _label(actual)
    return MaterializationError("E_MATERIALIZER_CONTEXT", f"{scope}; expected {expected}; found {found}")


def _inside(root: Path, relative: str) -> Path:
    try:
        return resolve_store_address(root, relative)
    except StoreAddressError as error:
        raise ValueError(f"E_MATERIALIZER_PATH: invalid relative store address {_label(relative)}") from error


def _identity(payload: bytes) -> str:
    return "sha256:" + sha256(payload).hexdigest()


def _label(value: object, *, limit: int = 120) -> str:
    """Render a bounded identifier/address without exposing resource payloads."""
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit - 1] + "…"
    if isinstance(value, Path):
        rendered = value.as_posix()
        return rendered if len(rendered) <= limit else "…" + rendered[-(limit - 1):]
    if value is None or isinstance(value, (int, float, bool)):
        return repr(value)
    return f"<{type(value).__name__}>"


def _code(error: BaseException) -> str:
    return str(error).partition(":")[0]


def _reference_key(reference: dict[str, Any]) -> str:
    return json.dumps({key: reference.get(key) for key in
                       ("kind", "id", "store", "address", "revision", "contentIdentity")},
                      sort_keys=True, separators=(",", ":"))


def _asset_key(locator: dict[str, Any], identity: str | None) -> str:
    return json.dumps((locator.get("provider"), locator.get("identity"), locator.get("address"), identity),
                      separators=(",", ":"))


@dataclass(frozen=True)
class MaterializedResourceOverlay:
    """Immutable, per-materialization lookup for verified authored resources."""
    _references: Any
    _assets: Any

    def read(self, reference: dict[str, Any]) -> bytes:
        try:
            path, expected, staged_identity = self._references[_reference_key(reference)]
        except KeyError as error:
            raise SnapshotReadError("E_STORE_REFERENCE", f"{_label(reference.get('kind'))}:{_label(reference.get('id'))} at {_label(reference.get('address'))} is not staged") from error
        try:
            payload = path.read_bytes()
        except OSError as error:
            raise SnapshotReadError("E_STORE_REFERENCE", f"staged {_label(reference.get('kind'))}:{_label(reference.get('id'))} at {_label(reference.get('address'))} is missing") from error
        actual = _identity(payload)
        if actual != staged_identity or (expected is not None and actual != expected):
            raise SnapshotReadError("E_CONTENT_IDENTITY", f"{_label(reference.get('kind'))}:{_label(reference.get('id'))} at {_label(reference.get('address'))}; expected {_label(expected or staged_identity)}, found {actual}")
        return payload

    def resolve_asset(self, locator: dict[str, Any], expected_identity: str | None) -> Path:
        path, identity, staged_identity = self._assets[_asset_key(locator, expected_identity)]
        payload = path.read_bytes()
        actual = _identity(payload)
        if actual != staged_identity or (identity is not None and actual != identity):
            raise ValueError(f"E_CONTENT_IDENTITY: asset {_label(locator.get('provider'))}:{_label(locator.get('identity'))} at {_label(locator.get('address'))}; expected {_label(identity or staged_identity)}, found {actual}")
        return path


class _OverlayBuilder:
    def __init__(self, root: Path, *, stage_packages: bool = False):
        self.root = root / "materialized-overlay"
        self.root.mkdir(parents=True, exist_ok=True)
        self.references: dict[str, tuple[Path, str | None, str]] = {}
        self.assets: dict[str, tuple[Path, str | None, str]] = {}
        self._owned_context_paths: set[Path] = set()
        self.stage_packages = stage_packages

    def reserve_context_path(self, path: Path) -> None:
        """Protect a composed Context from every resource/asset staging path."""
        self._owned_context_paths.add(path.resolve())

    def check_resource_path(self, path: Path) -> None:
        resolved = path.resolve()
        if any(resolved == owned or resolved in owned.parents or owned in resolved.parents
               for owned in self._owned_context_paths):
            raise MaterializationError("E_MATERIALIZER_OVERLAY_COLLISION",
                                       "resource shadows composed Context address")

    def _stage(self, key: str, payload: bytes) -> Path:
        path = self.root / sha256(key.encode()).hexdigest()
        staged_identity = _identity(payload)
        if path.exists():
            if _identity(path.read_bytes()) != staged_identity:
                raise ValueError(f"E_MATERIALIZER_OVERLAY_COLLISION: staging key sha256:{sha256(key.encode()).hexdigest()}; existing {_identity(path.read_bytes())}, attempted {staged_identity}")
        else:
            path.write_bytes(payload)
        return path

    def add_reference(self, reference: dict[str, Any], payload: bytes, *, staged_path: Path | None = None) -> None:
        expected = reference.get("contentIdentity")
        if expected is not None and expected != _identity(payload):
            raise ValueError(f"E_CONTENT_IDENTITY: reference {_label(reference.get('kind'))}:{_label(reference.get('id'))} at {_label(reference.get('address'))}; expected {_label(expected)}, found {_identity(payload)}")
        key = _reference_key(reference)
        path = staged_path if staged_path is not None else self._stage("ref:" + key, payload)
        if path.read_bytes() != payload:
            raise ValueError(f"E_MATERIALIZER_OVERLAY_COLLISION: reference {_label(reference.get('kind'))}:{_label(reference.get('id'))} at {_label(reference.get('address'))}; staged path bytes differ from supplied {_identity(payload)}")
        staged_identity = _identity(payload)
        previous = self.references.get(key)
        if previous is not None and previous[2] != staged_identity:
            raise ValueError(f"E_MATERIALIZER_OVERLAY_COLLISION: reference {_label(reference.get('kind'))}:{_label(reference.get('id'))} at {_label(reference.get('address'))}; existing {previous[2]}, attempted {staged_identity}")
        self.references[key] = (path, expected, staged_identity)

    def add_asset(self, locator: dict[str, Any], expected: str | None, payload: bytes,
                  *, staged_path: Path | None = None) -> None:
        if expected is not None and expected != _identity(payload):
            raise ValueError(f"E_MATERIALIZER_FONT_IDENTITY: asset {_label(locator.get('provider'))}:{_label(locator.get('identity'))} at {_label(locator.get('address'))}; expected {_label(expected)}, found {_identity(payload)}")
        key = _asset_key(locator, expected)
        path = staged_path if staged_path is not None else self._stage("asset:" + key, payload)
        if path.read_bytes() != payload:
            raise ValueError(f"E_MATERIALIZER_OVERLAY_COLLISION: asset {_label(locator.get('provider'))}:{_label(locator.get('identity'))} at {_label(locator.get('address'))}; staged path bytes differ from supplied {_identity(payload)}")
        staged_identity = _identity(payload)
        previous = self.assets.get(key)
        if previous is not None and previous[2] != staged_identity:
            raise ValueError(f"E_MATERIALIZER_OVERLAY_COLLISION: asset {_label(locator.get('provider'))}:{_label(locator.get('identity'))} at {_label(locator.get('address'))}; existing {previous[2]}, attempted {staged_identity}")
        self.assets[key] = (path, expected, staged_identity)

    def finish(self) -> MaterializedResourceOverlay:
        return MaterializedResourceOverlay(MappingProxyType(dict(self.references)),
                                           MappingProxyType(dict(self.assets)))


def _package_resource(address: str):
    try:
        segments = check_store_address(address)
    except StoreAddressError as error:
        raise ValueError(f"E_MATERIALIZER_PATH: invalid package resource address {_label(address)}") from error
    resource = files("chrona.resources").joinpath(*segments)
    if not resource.is_file():
        raise ValueError(f"E_MATERIALIZER_PACKAGE_RESOURCE: package resource {_label(address)} was not found")
    return resource


def _shared_root(reference: dict[str, Any], stores: Mapping[str, Path] | None) -> Path | None:
    """The root of the declared read-only shared-design Store a local reference names, else None (the example itself)."""
    store = reference.get("store", {})
    if stores and store.get("provider") == "local":
        return stores.get(store.get("identity"))
    return None


def materializer_store_roots(example: Path, declared: object) -> dict[str, Path]:
    """The manifest's read-only shared-design Stores (`stores: [{identity, root}]`), roots relative to the manifest (#1342)."""
    if declared is None:
        return {}
    if not isinstance(declared, list):
        raise _context_error("manifest stores", "a list of {identity, root}", declared)
    roots: dict[str, Path] = {}
    for entry in declared:
        identity, root = (entry.get("identity"), entry.get("root")) if isinstance(entry, dict) else (None, None)
        if not isinstance(identity, str) or not identity or not isinstance(root, str) or not root or identity in roots:
            raise _context_error("manifest stores entry", "a distinct identity and a root", entry)
        path = (example / root).resolve()
        if not path.is_dir():
            raise ValueError(f"E_MATERIALIZER_STORE: shared design Store {_label(identity)} root {_label(root)} is not a directory")
        try:
            check_store_segment(identity)
        except StoreAddressError as error:
            raise ValueError(f"E_MATERIALIZER_STORE: shared design Store identity {_label(identity)} is not a safe single segment") from error
        roots[identity] = path
    return roots


def _staged_address(reference: dict[str, Any], stores: Mapping[str, Path] | None, address: str) -> str:
    """Where a copied reference sits in the snapshot: a shared Store's files go under their own Store segment."""
    return f"_store-{reference['store']['identity']}/{address}" if _shared_root(reference, stores) is not None else address


def read_materializer_reference(example: Path, reference: dict[str, Any],
                                stores: Mapping[str, Path] | None = None) -> bytes:
    """Read one admitted reference without staging, rewriting or rendering it."""
    token, address = reference.get("revision", {}).get("token"), reference.get("address")
    if not isinstance(token, str) or not isinstance(address, str):
        raise _context_error("reference", "string revision token and address", {"token": token, "address": address})
    if reference.get("store", {}).get("provider") == "package":
        if reference.get("store", {}).get("identity") != "chrona.resources":
            raise ValueError(f"E_MATERIALIZER_PACKAGE_RESOURCE: {_label(address)} requires store identity chrona.resources, found {_label(reference.get('store', {}).get('identity'))}")
        payload = _package_resource(address).read_bytes()
        if reference.get("contentIdentity") not in (None, _identity(payload)):  # unpinned: the identity is computed and recorded (#1342)
            raise ValueError(f"E_MATERIALIZER_PACKAGE_IDENTITY: package reference {_label(reference.get('id'))} at {_label(address)}; expected {_label(reference.get('contentIdentity'))}, found {_identity(payload)}")
        return payload
    if reference.get("store", {}).get("provider") != "local":
        raise ValueError(f"E_MATERIALIZER_PROVIDER: reference {_label(reference.get('kind'))}:{_label(reference.get('id'))} at {_label(address)} requires local or package provider, found {_label(reference.get('store', {}).get('provider'))}")
    payload = _inside(_shared_root(reference, stores) or example, address).read_bytes()
    if reference.get("contentIdentity") not in (None, _identity(payload)):
        raise ValueError(f"E_CONTENT_IDENTITY: reference {_label(reference.get('kind'))}:{_label(reference.get('id'))} at {_label(address)}; expected {_label(reference.get('contentIdentity'))}, found {_identity(payload)}")
    return payload


def _copy_reference(example: Path, reference: dict[str, Any], snapshot: Path, *, target_token: str | None = None,
                    theme_stack: tuple[str, ...] = (), overlay: _OverlayBuilder | None = None,
                    stores: Mapping[str, Path] | None = None) -> bytes:
    token, address = reference.get("revision", {}).get("token"), reference.get("address")
    payload = read_materializer_reference(example, reference, stores)
    package_reference = reference.get("store", {}).get("provider") == "package"
    if not (overlay is not None and package_reference and not overlay.stage_packages):
        target = _inside(snapshot_directory(snapshot, target_token or token), _staged_address(reference, stores, address))
        if overlay is not None:
            overlay.check_resource_path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    if overlay is not None:
        overlay.add_reference(reference, payload,
                              staged_path=None if package_reference and not overlay.stage_packages else target)
    if reference.get("kind") == "theme":
        value = safe_load(payload)
        if is_derived_theme(value):
            if address in theme_stack:
                raise ValueError(f"E_THEME_INHERITANCE_CYCLE: theme reference {_label(reference.get('id'))} repeats address {_label(address)}")
            try:
                base = theme_base_reference(reference, value)
            except ThemeInheritanceError as error:
                raise ValueError(f"{error.code}: {error.detail}" if error.detail else error.code) from error
            try:
                _copy_reference(example, base, snapshot, theme_stack=(*theme_stack, address), overlay=overlay, stores=stores)
            except ValueError as error:
                if _code(error) == "E_CONTENT_IDENTITY":
                    raise ValueError(f"E_THEME_INHERITANCE_SOURCE_IDENTITY: base theme for {_label(reference.get('id'))} at {_label(address)} failed identity verification ({error})") from error
                raise
            except FileNotFoundError as error:
                raise ValueError(f"E_THEME_INHERITANCE_BASE_MISSING: base theme for {_label(reference.get('id'))} at {_label(address)} is unavailable") from error
    if reference.get("kind") == "snapshot-ref":
        document = safe_load(payload)
        body = document.get("body") if isinstance(document, dict) else None
        nested = body.get("project") if isinstance(body, dict) else None
        if not isinstance(nested, dict):
            where = (f"snapshot reference {_label(reference.get('id'))} at {_label(address)}")
            missing = ("has no /body/project" if nested is None
                       else f"has /body/project of type {type(nested).__name__}")
            raise MaterializationError(
                "E_MATERIALIZER_CONTEXT",
                f"{where} {missing}; a snapshot-ref file must embed the baseline Project reference as "
                "/body/project (id, kind: project, store, address, revision)")
        _copy_reference(example, nested, snapshot, overlay=overlay, stores=stores)
    return payload


def _copy_icon_assets(example: Path, catalog_reference: dict[str, Any], snapshot: Path,
                      catalog_payload: bytes, overlay: _OverlayBuilder | None = None,
                      stores: Mapping[str, Path] | None = None) -> dict[str, Any]:
    """Copy only declared, identity-pinned catalog bytes into the immutable snapshot."""
    token, address = catalog_reference.get("revision", {}).get("token"), catalog_reference.get("address")
    if not isinstance(token, str) or not isinstance(address, str):
        raise _context_error("icon catalog reference", "string revision token and address", {"token": token, "address": address})
    catalog = safe_load(catalog_payload)
    icons = catalog.get("body", {}).get("icons") if isinstance(catalog, dict) else None
    if not isinstance(icons, dict):
        raise ValueError(f"E_ICON_CATALOG_SCHEMA: catalog {_label(catalog_reference.get('id'))} at {_label(address)} must contain an icons object")
    for icon_id, entry in sorted(icons.items()):
        if not isinstance(entry, dict) or entry.get("kind") == "vector":
            continue
        source = entry.get("source") if isinstance(entry, dict) else None
        asset_address = source.get("address") if isinstance(source, dict) else None
        expected = source.get("contentIdentity") if isinstance(source, dict) else None
        try:
            check_store_address(asset_address)
        except StoreAddressError as error:
            raise ValueError(f"E_ICON_ASSET_PATH: icon {_label(icon_id)} has invalid asset address {_label(asset_address)}") from error
        if catalog_reference.get("store", {}).get("provider") == "package":
            payload = _package_resource(asset_address).read_bytes()
        else:
            source_path = _inside(_shared_root(catalog_reference, stores) or example, asset_address)
            if source_path.is_symlink():
                raise ValueError(f"E_ICON_ASSET_PATH: icon {_label(icon_id)} asset at {_label(asset_address)} must not be a symlink")
            payload = source_path.read_bytes()
        if expected is not None and expected != _identity(payload):
            raise ValueError(f"E_ICON_ASSET_IDENTITY: icon {_label(icon_id)} asset at {_label(asset_address)}; expected {_label(expected)}, found {_identity(payload)}")
        package_asset = catalog_reference.get("store", {}).get("provider") == "package"
        staged_path = None
        if not (overlay is not None and package_asset and not overlay.stage_packages):
            target = _inside(snapshot_directory(snapshot, token), _staged_address(catalog_reference, stores, asset_address))
            if overlay is not None:
                overlay.check_resource_path(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            staged_path = target
        if overlay is not None:
            overlay.add_reference({"id": icon_id, "kind": "icon-asset",
                                   "store": catalog_reference["store"], "address": asset_address,
                                   "revision": catalog_reference["revision"],
                                   "contentIdentity": expected}, payload,
                                  staged_path=None if package_asset and not overlay.stage_packages else staged_path)
            locator = {"provider": catalog_reference.get("store", {}).get("provider"),
                       "identity": catalog_reference.get("store", {}).get("identity"),
                       "address": asset_address}
            overlay.add_asset(locator, expected, payload,
                              staged_path=None if package_asset and not overlay.stage_packages else staged_path)
    return catalog


def _copy_extension_packages(example: Path, project_reference: dict[str, Any], snapshot: Path,
                             project_payload: bytes, overlay: _OverlayBuilder | None = None,
                             stores: Mapping[str, Path] | None = None) -> None:
    """Copy the pinned profile packages a Project declares, so the closure can read them."""
    project = safe_load(project_payload)
    for extension in (project.get("extensions") or []) if isinstance(project, dict) else []:
        resource = extension.get("resource") if isinstance(extension, dict) else None
        if not isinstance(resource, dict):
            continue
        if resource.get("kind") != "profile-package":
            raise _context_error("Project extension resource", "profile-package reference", resource.get("kind"))
        _copy_reference(example, resource, snapshot, overlay=overlay, stores=stores)


def copy_context_closure(example: Path, context_path: Path | SelectedDeckContext, snapshot: Path,
                         *, decoded_catalogs: dict[str, Any] | None = None,
                         overlay_builder: _OverlayBuilder | None = None,
                         stores: Mapping[str, Path] | None = None) -> tuple[dict[str, Any], str]:
    selected = context_path if isinstance(context_path, SelectedDeckContext) else None
    if selected is not None and selected.source_path is None and overlay_builder is None:
        # Init retains only the snapshot tree. Keep identity-keyed package
        # staging outside it, with the same lifetime as this closure copy.
        with tempfile.TemporaryDirectory(prefix="chrona-context-overlay-") as temporary:
            return copy_context_closure(
                example, selected, snapshot, decoded_catalogs=decoded_catalogs,
                overlay_builder=_OverlayBuilder(Path(temporary), stage_packages=True), stores=stores)
    raw_context = selected.payload if selected is not None else context_path.read_bytes()
    context_address = selected.address if selected is not None else context_path.relative_to(example).as_posix()
    # Normalize resource declarations for copying, not the authored bytes
    # staged below and used to compute the Context's content identity.
    context = expand_font_set(safe_load(raw_context))
    if not isinstance(context, dict):
        raise _context_error("context", "Render Context object", context)
    if context.get("version") not in RENDER_CONTEXT_VERSIONS or context.get("kind") != "render-context":
        raise _context_error("context", " or ".join(RENDER_CONTEXT_VERSIONS) + " render-context", {"version": context.get("version"), "kind": context.get("kind")})
    context_id = context.get("id")
    identity_id = context_id if isinstance(context_id, str) else "<invalid-context>"
    parse_contract(ClosureIdentity("render-context", identity_id, "initialization", _identity(raw_context)), context)
    body = context["body"]
    revision = body["project"]["revision"]["token"]
    destination = snapshot_directory(snapshot, revision)
    target = _inside(destination, context_address)
    if selected is not None and selected.source_path is None:
        authored_target = _inside(example, context_address)
        if (authored_target.exists() or target.exists()
                or any(parent.is_file() for parent in authored_target.parents if parent != example)):
            raise MaterializationError("E_MATERIALIZER_OVERLAY_COLLISION",
                                       f"composed Context address {_label(context_address)} already exists")
        overlay_builder.reserve_context_path(target)
    references = [body[name] for name in ("project", "view", "theme", "colorScheme", "layout")]
    if "style" in body:
        references.insert(2, body["style"])
    inputs = body.get("inputs", {})
    references.extend(value for key, value in inputs.items() if key != "iconCatalogs")
    copied_payloads = { _reference_key(item): _copy_reference(example, item, snapshot, overlay=overlay_builder, stores=stores)
                        for item in references }
    _copy_extension_packages(example, body["project"], snapshot,
                             copied_payloads[_reference_key(body["project"])], overlay_builder, stores)
    for icon_catalog in inputs.get("iconCatalogs", ()):
        if not isinstance(icon_catalog, dict) or icon_catalog.get("kind") != "icon-catalog":
            raise _context_error("context inputs.iconCatalogs", "icon-catalog reference object", icon_catalog)
        catalog_payload = _copy_reference(
            example, icon_catalog, snapshot,
            target_token=revision if icon_catalog.get("store", {}).get("provider") == "package" else None,
            overlay=overlay_builder, stores=stores)
        catalog = _copy_icon_assets(example, icon_catalog, snapshot, catalog_payload, overlay_builder, stores)
        if decoded_catalogs is not None:
            decoded_catalogs[_identity(catalog_payload)] = catalog
    for asset in _font_copy_plan(body, example):
        asset_target = None
        if not (overlay_builder is not None and asset.provider == "package" and not overlay_builder.stage_packages):
            asset_target = _inside(destination, asset.address)
            if overlay_builder is not None:
                overlay_builder.check_resource_path(asset_target)
            asset_target.parent.mkdir(parents=True, exist_ok=True)
            asset_target.write_bytes(asset.payload)
        if overlay_builder is not None:
            overlay_builder.add_asset(asset.locator, asset.content_identity, asset.payload,
                                      staged_path=asset_target if asset.provider == "context" else None)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw_context)
    context_reference = {"id": context["id"], "kind": "render-context", "store": body["project"]["store"],
                         "address": context_address, "revision": {"token": revision},
                         "contentIdentity": _identity(raw_context)}
    if overlay_builder is not None:
        overlay_builder.add_reference(context_reference, raw_context, staged_path=target)
    return context_reference, revision


MATERIALIZED_OUTPUT_FILES = frozenset({"review.svg", "review.scene.json", "closure.yaml"})


def _check_replaceable_output(output: Path) -> None:
    """`--replace` re-runs into a directory this command filled before; any other entry is foreign and refuses it."""
    foreign = sorted(entry.name for entry in output.iterdir()
                     if entry.name not in MATERIALIZED_OUTPUT_FILES or entry.is_symlink() or not entry.is_file())
    if foreign:
        raise ValueError(f"E_MATERIALIZER_OUTPUT: output directory {_label(output)} holds files this command did not write "
                         f"({', '.join(_label(name) for name in foreign)}); --replace refuses to touch them")


def materialize(manifest_path: Path, slide_id: str, output: Path, *, write: bool = False, replace: bool = False) -> MaterializationResult:
    example = manifest_path.parent.resolve()
    loaded_manifest = load_deck_manifest(manifest_path)
    manifest = loaded_manifest.document
    if manifest.get("version") != "chrona/example-materializer/v0.1" or manifest.get("role") != "regression-corpus":
        raise ValueError(f"E_MATERIALIZER_MANIFEST: {_label(manifest_path)} requires version chrona/example-materializer/v0.1 and role regression-corpus; found version={_label(manifest.get('version'))}, role={_label(manifest.get('role'))}")
    slides = manifest.get("slides")
    if not isinstance(slides, list):
        # The shared admission owner reports the pointed manifest failure.
        select_deck_context(manifest_path, loaded_manifest, slide_id)
    slide = next((item for item in slides if isinstance(item, Mapping) and item.get("id") == slide_id), None)
    if slide is None or not isinstance(slide.get("evidence"), str) or not slide["evidence"].strip():
        raise ValueError(f"E_MATERIALIZER_SLIDE: slide {_label(slide_id)} is missing or has no non-empty evidence path")
    if output.exists() and any(output.iterdir()):
        if not replace:
            raise ValueError(f"E_MATERIALIZER_OUTPUT: output directory {_label(output)} is not empty")
        _check_replaceable_output(output)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        snapshot = Path(temporary) / "snapshot"; snapshot.mkdir()
        context_source = select_deck_context(manifest_path, loaded_manifest, slide_id)
        expected = _inside(example, str(slide["expectedSvg"]))
        decoded_catalogs: dict[str, Any] = {}
        overlay_builder = _OverlayBuilder(Path(temporary))
        reference, _ = copy_context_closure(example, context_source, snapshot, decoded_catalogs=decoded_catalogs,
                                            overlay_builder=overlay_builder,
                                            stores=materializer_store_roots(example, manifest.get("stores")))
        overlay = overlay_builder.finish()
        closure = resolve_render_context(reference, overlay,
                                         decoded_resources=decoded_catalogs)
        rendered = render_review(RenderRequest(closure, snapshot, ReferenceScheduler(), asset_resolver=overlay))
        derived = output / "review.svg"
        derived.write_bytes(rendered.artifact.content)
        expected_scene = slide.get("expectedScene")
        if expected_scene is not None:
            if not isinstance(expected_scene, str) or not expected_scene:
                raise MaterializationError("E_MATERIALIZER_SCENE", "expectedScene must be a non-empty relative path")
            try:
                scene_bytes = serialize_scene(rendered.scene)
            except SceneSerializationError as error:
                raise MaterializationError("E_MATERIALIZER_SCENE", str(error)) from error
            scene_output = output / "review.scene.json"
            scene_output.write_bytes(scene_bytes)
            expected_scene_path = _inside(example, expected_scene)
            if write:
                expected_scene_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(scene_output, expected_scene_path)
            elif not expected_scene_path.is_file() or scene_output.read_bytes() != expected_scene_path.read_bytes():
                raise MaterializationError("E_MATERIALIZER_MISMATCH", "generated Scene differs from declared evidence")
        evidence: dict[str, Any] = reference
        if rendered.scenario_provenance:
            evidence = {
                "context": reference,
                "scenarios": [
                    {"scenarioId": item.scenario_id, "title": item.title,
                     "contentIdentity": item.content_identity}
                    for item in rendered.scenario_provenance
                ],
            }
        (output / "closure.yaml").write_text(yaml.safe_dump(evidence, sort_keys=True), encoding="utf-8")
        if write:
            expected.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(derived, expected)
        elif not expected.is_file() or derived.read_bytes() != expected.read_bytes():
            raise MaterializationError("E_MATERIALIZER_MISMATCH", "generated artifact differs from declared evidence")
        return MaterializationResult(derived, reference, rendered)
