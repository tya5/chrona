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
from typing import Any

import yaml

from chrona.presentation.contracts.resources import RENDER_CONTEXT_VERSIONS
from chrona.presentation.model.closure import resolve_render_context
from chrona.presentation.model.font_resources import FontResourceError, resolve_font_resource
from chrona.presentation.model.theme_inheritance import ThemeInheritanceError, is_derived_theme, theme_base_reference
from chrona.resources import safe_load
from chrona.presentation.renderers.registry import renderer_for
from chrona.core.ports import SnapshotReadError
from chrona.core.store_address import StoreAddressError, check_store_address, resolve_store_address
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.storage.snapshot_paths import snapshot_directory
from chrona.usecases.render_review import RenderRequest, RenderedReview, render_review
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
    def __init__(self, root: Path):
        self.root = root / "materialized-overlay"
        self.root.mkdir(parents=True, exist_ok=True)
        self.references: dict[str, tuple[Path, str | None, str]] = {}
        self.assets: dict[str, tuple[Path, str | None, str]] = {}

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


def _reference_payload(example: Path, reference: dict[str, Any]) -> bytes:
    address = reference.get("address")
    if not isinstance(address, str):
        raise _context_error("reference", "string address", address)
    if reference.get("store", {}).get("provider") == "package":
        if reference.get("store", {}).get("identity") != "chrona.resources":
            raise ValueError(f"E_MATERIALIZER_PACKAGE_RESOURCE: {_label(address)} requires store identity chrona.resources, found {_label(reference.get('store', {}).get('identity'))}")
        payload = _package_resource(address).read_bytes()
        if reference.get("contentIdentity") != _identity(payload):
            raise ValueError(f"E_MATERIALIZER_PACKAGE_IDENTITY: package reference {_label(reference.get('id'))} at {_label(address)}; expected {_label(reference.get('contentIdentity'))}, found {_identity(payload)}")
        return payload
    if reference.get("store", {}).get("provider") != "local":
        raise ValueError(f"E_MATERIALIZER_PROVIDER: reference {_label(reference.get('kind'))}:{_label(reference.get('id'))} at {_label(address)} requires local or package provider, found {_label(reference.get('store', {}).get('provider'))}")
    return _inside(example, address).read_bytes()


def _copy_reference(example: Path, reference: dict[str, Any], snapshot: Path, *, target_token: str | None = None,
                    theme_stack: tuple[str, ...] = (), overlay: _OverlayBuilder | None = None) -> bytes:
    token, address = reference.get("revision", {}).get("token"), reference.get("address")
    if not isinstance(token, str) or not isinstance(address, str):
        raise _context_error("reference", "string revision token and address", {"token": token, "address": address})
    payload = _reference_payload(example, reference)
    if reference.get("contentIdentity") not in (None, _identity(payload)):
        raise ValueError(f"E_CONTENT_IDENTITY: reference {_label(reference.get('kind'))}:{_label(reference.get('id'))} at {_label(address)}; expected {_label(reference.get('contentIdentity'))}, found {_identity(payload)}")
    package_reference = reference.get("store", {}).get("provider") == "package"
    if not (overlay is not None and package_reference):
        target = _inside(snapshot_directory(snapshot, target_token or token), address)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    if overlay is not None:
        overlay.add_reference(reference, payload, staged_path=None if package_reference else target)
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
                _copy_reference(example, base, snapshot, theme_stack=(*theme_stack, address), overlay=overlay)
            except ValueError as error:
                if _code(error) == "E_CONTENT_IDENTITY":
                    raise ValueError(f"E_THEME_INHERITANCE_SOURCE_IDENTITY: base theme for {_label(reference.get('id'))} at {_label(address)} failed identity verification ({error})") from error
                raise
            except FileNotFoundError as error:
                raise ValueError(f"E_THEME_INHERITANCE_BASE_MISSING: base theme for {_label(reference.get('id'))} at {_label(address)} is unavailable") from error
    if reference.get("kind") == "snapshot-ref":
        nested = safe_load(payload).get("body", {}).get("project")
        if not isinstance(nested, dict):
            raise _context_error("snapshot reference", "embedded Project reference object", nested)
        _copy_reference(example, nested, snapshot, overlay=overlay)
    return payload


def _copy_icon_assets(example: Path, catalog_reference: dict[str, Any], snapshot: Path,
                      catalog_payload: bytes, overlay: _OverlayBuilder | None = None) -> dict[str, Any]:
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
            source_path = _inside(example, asset_address)
            if source_path.is_symlink():
                raise ValueError(f"E_ICON_ASSET_PATH: icon {_label(icon_id)} asset at {_label(asset_address)} must not be a symlink")
            payload = source_path.read_bytes()
        if expected != _identity(payload):
            raise ValueError(f"E_ICON_ASSET_IDENTITY: icon {_label(icon_id)} asset at {_label(asset_address)}; expected {_label(expected)}, found {_identity(payload)}")
        package_asset = catalog_reference.get("store", {}).get("provider") == "package"
        staged_path = None
        if not (overlay is not None and package_asset):
            target = _inside(snapshot_directory(snapshot, token), asset_address)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            staged_path = target
        if overlay is not None:
            overlay.add_reference({"id": icon_id, "kind": "icon-asset",
                                   "store": catalog_reference["store"], "address": asset_address,
                                   "revision": catalog_reference["revision"],
                                   "contentIdentity": expected}, payload,
                                  staged_path=None if package_asset else staged_path)
            locator = {"provider": catalog_reference.get("store", {}).get("provider"),
                       "identity": catalog_reference.get("store", {}).get("identity"),
                       "address": asset_address}
            overlay.add_asset(locator, expected, payload,
                              staged_path=None if package_asset else staged_path)
    return catalog


def _copy_extension_packages(example: Path, project_reference: dict[str, Any], snapshot: Path,
                             project_payload: bytes, overlay: _OverlayBuilder | None = None) -> None:
    """Copy the pinned profile packages a Project declares, so the closure can read them."""
    project = safe_load(project_payload)
    for extension in (project.get("extensions") or []) if isinstance(project, dict) else []:
        resource = extension.get("resource") if isinstance(extension, dict) else None
        if not isinstance(resource, dict):
            continue
        if resource.get("kind") != "profile-package":
            raise _context_error("Project extension resource", "profile-package reference", resource.get("kind"))
        _copy_reference(example, resource, snapshot, overlay=overlay)


def copy_context_closure(example: Path, context_path: Path, snapshot: Path,
                         *, decoded_catalogs: dict[str, Any] | None = None,
                         overlay_builder: _OverlayBuilder | None = None) -> tuple[dict[str, Any], str]:
    raw_context = context_path.read_bytes()
    context = safe_load(raw_context)
    if context.get("version") not in RENDER_CONTEXT_VERSIONS or context.get("kind") != "render-context":
        raise _context_error("context", " or ".join(RENDER_CONTEXT_VERSIONS) + " render-context", {"version": context.get("version"), "kind": context.get("kind")})
    body = context["body"]
    revision = body["project"]["revision"]["token"]
    references = [body[name] for name in ("project", "view", "theme", "colorScheme", "layout")]
    inputs = body.get("inputs", {})
    references.extend(value for key, value in inputs.items() if key != "iconCatalogs")
    copied_payloads = { _reference_key(item): _copy_reference(example, item, snapshot, overlay=overlay_builder)
                        for item in references }
    _copy_extension_packages(example, body["project"], snapshot,
                             copied_payloads[_reference_key(body["project"])], overlay_builder)
    for icon_catalog in inputs.get("iconCatalogs", ()):
        if not isinstance(icon_catalog, dict) or icon_catalog.get("kind") != "icon-catalog":
            raise _context_error("context inputs.iconCatalogs", "icon-catalog reference object", icon_catalog)
        catalog_payload = _copy_reference(
            example, icon_catalog, snapshot,
            target_token=revision if icon_catalog.get("store", {}).get("provider") == "package" else None,
            overlay=overlay_builder)
        catalog = _copy_icon_assets(example, icon_catalog, snapshot, catalog_payload, overlay_builder)
        if decoded_catalogs is not None:
            decoded_catalogs[_identity(catalog_payload)] = catalog
    destination = snapshot_directory(snapshot, revision)
    for asset in body["environment"]["fontMetrics"]["assets"]:
        keys = ("metrics",) if body["target"]["kind"] == "svg" else ("metrics", "font")
        for key in keys:
            record = asset.get(key, {})
            if not isinstance(record, dict) or not isinstance(record.get("locator"), dict):
                raise ValueError(f"E_MATERIALIZER_FONT: fontMetrics asset {_label(asset.get('id', '<unknown>'))} field {key} requires a locator object")
            try:
                source = resolve_font_resource(record["locator"], asset_root=example)
            except FontResourceError as error:
                raise ValueError(f"E_MATERIALIZER_FONT: cannot resolve {key} asset for {_label(asset.get('id', '<unknown>'))} at {_label(record['locator'].get('address'))}: {error}; {_label(error.detail)}") from error
            payload = source.read_bytes()
            if record.get("contentIdentity") != _identity(payload):
                raise ValueError(f"E_MATERIALIZER_FONT_IDENTITY: fontMetrics asset {_label(asset.get('id', '<unknown>'))} field {key} at {_label(record['locator'].get('address'))}; expected {_label(record.get('contentIdentity'))}, found {_identity(payload)}")
            address = record["locator"].get("address")
            if not isinstance(address, str):
                raise ValueError(f"E_MATERIALIZER_FONT: fontMetrics asset {_label(asset.get('id', '<unknown>'))} field {key} locator requires string address, found {_label(address)}")
            locator_provider = record["locator"].get("provider")
            asset_target = None
            if not (overlay_builder is not None and locator_provider == "package"):
                asset_target = _inside(destination, address)
                asset_target.parent.mkdir(parents=True, exist_ok=True)
                asset_target.write_bytes(payload)
            if overlay_builder is not None:
                overlay_builder.add_asset(record["locator"], record.get("contentIdentity"), payload,
                                          staged_path=asset_target if locator_provider == "context" else None)
    target = _inside(destination, context_path.relative_to(example).as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw_context)
    context_reference = {"id": context["id"], "kind": "render-context", "store": body["project"]["store"],
                         "address": context_path.relative_to(example).as_posix(), "revision": {"token": revision},
                         "contentIdentity": _identity(raw_context)}
    if overlay_builder is not None:
        overlay_builder.add_reference(context_reference, raw_context, staged_path=target)
    return context_reference, revision


def materialize(manifest_path: Path, slide_id: str, output: Path, *, write: bool = False) -> MaterializationResult:
    example = manifest_path.parent.resolve()
    manifest = safe_load(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("version") != "chrona/example-materializer/v0.1" or manifest.get("role") != "regression-corpus":
        raise ValueError(f"E_MATERIALIZER_MANIFEST: {_label(manifest_path)} requires version chrona/example-materializer/v0.1 and role regression-corpus; found version={_label(manifest.get('version'))}, role={_label(manifest.get('role'))}")
    slide = next((item for item in manifest.get("slides", ()) if item.get("id") == slide_id), None)
    if slide is None or not isinstance(slide.get("evidence"), str) or not slide["evidence"].strip():
        raise ValueError(f"E_MATERIALIZER_SLIDE: slide {_label(slide_id)} is missing or has no non-empty evidence path")
    expected = _inside(example, str(slide["expectedSvg"]))
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"E_MATERIALIZER_OUTPUT: output directory {_label(output)} is not empty")
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        snapshot = Path(temporary) / "snapshot"; snapshot.mkdir()
        context_path = _inside(example, str(slide.get("context", manifest["context"])))
        decoded_catalogs: dict[str, Any] = {}
        overlay_builder = _OverlayBuilder(Path(temporary))
        reference, _ = copy_context_closure(example, context_path, snapshot, decoded_catalogs=decoded_catalogs,
                                            overlay_builder=overlay_builder)
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
