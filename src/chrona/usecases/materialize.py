"""Immutable example/context materialization application service."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
from pathlib import PurePosixPath
import shutil
import tempfile
from typing import Any

import yaml

from chrona.presentation.model.closure import resolve_render_context
from chrona.presentation.renderers.registry import renderer_for
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.usecases.render_review import RenderRequest, RenderedReview, render_review
from chrona.yaml_codec import safe_load


@dataclass(frozen=True)
class MaterializationResult:
    output: Path
    closure_reference: dict[str, Any]
    rendered: RenderedReview


def _inside(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if path != root.resolve() and root.resolve() not in path.parents:
        raise ValueError("E_MATERIALIZER_PATH")
    return path


def _identity(payload: bytes) -> str:
    return "sha256:" + sha256(payload).hexdigest()


def _package_resource(address: str):
    path = PurePosixPath(address)
    if (not address or path.is_absolute() or address != path.as_posix()
            or any(part in {"", ".", ".."} for part in path.parts)):
        raise ValueError("E_MATERIALIZER_PATH")
    resource = files("chrona.resources").joinpath(address)
    if not resource.is_file():
        raise ValueError("E_MATERIALIZER_PACKAGE_RESOURCE")
    return resource


def _reference_payload(example: Path, reference: dict[str, Any]) -> bytes:
    address = reference.get("address")
    if not isinstance(address, str):
        raise ValueError("E_MATERIALIZER_CONTEXT")
    if reference.get("store", {}).get("provider") == "package":
        if reference.get("store", {}).get("identity") != "chrona.resources":
            raise ValueError("E_MATERIALIZER_PACKAGE_RESOURCE")
        payload = _package_resource(address).read_bytes()
        if reference.get("contentIdentity") != _identity(payload):
            raise ValueError("E_MATERIALIZER_PACKAGE_IDENTITY")
        return payload
    return _inside(example, address).read_bytes()


def _copy_reference(example: Path, reference: dict[str, Any], snapshot: Path, *, target_token: str | None = None) -> None:
    token, address = reference.get("revision", {}).get("token"), reference.get("address")
    if not isinstance(token, str) or not isinstance(address, str):
        raise ValueError("E_MATERIALIZER_CONTEXT")
    payload = _reference_payload(example, reference)
    if reference.get("contentIdentity") not in (None, _identity(payload)):
        raise ValueError("E_CONTENT_IDENTITY")
    target = _inside(snapshot / (target_token or token), address)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    if reference.get("kind") == "snapshot-ref":
        nested = safe_load(payload).get("body", {}).get("project")
        if not isinstance(nested, dict):
            raise ValueError("E_MATERIALIZER_CONTEXT")
        _copy_reference(example, nested, snapshot)


def _copy_icon_assets(example: Path, catalog_reference: dict[str, Any], snapshot: Path) -> None:
    """Copy only declared, identity-pinned catalog bytes into the immutable snapshot."""
    token, address = catalog_reference.get("revision", {}).get("token"), catalog_reference.get("address")
    if not isinstance(token, str) or not isinstance(address, str):
        raise ValueError("E_MATERIALIZER_CONTEXT")
    catalog = safe_load(_reference_payload(example, catalog_reference))
    icons = catalog.get("body", {}).get("icons") if isinstance(catalog, dict) else None
    if not isinstance(icons, dict):
        raise ValueError("E_ICON_CATALOG_SCHEMA")
    for icon_id, entry in sorted(icons.items()):
        if not isinstance(entry, dict) or entry.get("kind") == "vector":
            continue
        source = entry.get("source") if isinstance(entry, dict) else None
        asset_address = source.get("address") if isinstance(source, dict) else None
        expected = source.get("contentIdentity") if isinstance(source, dict) else None
        path = PurePosixPath(asset_address) if isinstance(asset_address, str) else None
        if (not isinstance(asset_address, str) or not asset_address or path is None
                or path.is_absolute() or asset_address != path.as_posix()
                or any(part in {"", ".", ".."} for part in path.parts)):
            raise ValueError("E_ICON_ASSET_PATH")
        if catalog_reference.get("store", {}).get("provider") == "package":
            payload = _package_resource(asset_address).read_bytes()
        else:
            source_path = _inside(example, asset_address)
            if source_path.is_symlink():
                raise ValueError("E_ICON_ASSET_PATH")
            payload = source_path.read_bytes()
        if expected != _identity(payload):
            raise ValueError("E_ICON_ASSET_IDENTITY")
        target = _inside(snapshot / token, asset_address)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)


def copy_context_closure(example: Path, context_path: Path, snapshot: Path) -> tuple[dict[str, Any], str]:
    context = safe_load(context_path.read_bytes())
    if context.get("version") != "chrona/render-context/v0.12" or context.get("kind") != "render-context":
        raise ValueError("E_MATERIALIZER_CONTEXT")
    body = context["body"]
    revision = body["project"]["revision"]["token"]
    references = [body[name] for name in ("project", "view", "theme", "colorScheme", "layout")]
    inputs = body.get("inputs", {})
    references.extend(value for key, value in inputs.items() if key != "iconCatalogs")
    for item in references:
        _copy_reference(example, item, snapshot)
    for icon_catalog in inputs.get("iconCatalogs", ()):
        if not isinstance(icon_catalog, dict) or icon_catalog.get("kind") != "icon-catalog":
            raise ValueError("E_MATERIALIZER_CONTEXT")
        _copy_reference(example, icon_catalog, snapshot,
                        target_token=revision if icon_catalog.get("store", {}).get("provider") == "package" else None)
        _copy_icon_assets(example, icon_catalog, snapshot)
        if icon_catalog.get("store", {}).get("provider") == "package":
            icon_catalog["store"] = body["project"]["store"]
            icon_catalog["revision"] = body["project"]["revision"]
    raw = yaml.safe_dump(context, sort_keys=False).encode()
    destination = snapshot / revision
    target = _inside(destination, context_path.relative_to(example).as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    for asset in body["environment"]["fontMetrics"]["assets"]:
        source = files("chrona.resources").joinpath(str(asset["path"]))
        if not source.is_file():
            raise ValueError("E_MATERIALIZER_FONT")
        payload = source.read_bytes()
        if asset.get("contentIdentity") not in (None, _identity(payload)):
            raise ValueError("E_MATERIALIZER_FONT_IDENTITY")
        asset_target = _inside(destination, str(asset["path"]))
        asset_target.parent.mkdir(parents=True, exist_ok=True)
        asset_target.write_bytes(payload)
    return {"id": context["id"], "kind": "render-context", "store": body["project"]["store"],
            "address": context_path.relative_to(example).as_posix(), "revision": {"token": revision},
            "contentIdentity": _identity(raw)}, revision


def materialize(manifest_path: Path, slide_id: str, output: Path, *, write: bool = False) -> MaterializationResult:
    example = manifest_path.parent.resolve()
    manifest = safe_load(manifest_path.read_text())
    if manifest.get("version") != "chrona/example-materializer/v0.1" or manifest.get("role") != "regression-corpus":
        raise ValueError("E_MATERIALIZER_MANIFEST")
    slide = next((item for item in manifest.get("slides", ()) if item.get("id") == slide_id), None)
    if slide is None or not isinstance(slide.get("evidence"), str) or not slide["evidence"].strip():
        raise ValueError("E_MATERIALIZER_SLIDE")
    expected = _inside(example, str(slide["expectedSvg"]))
    if output.exists() and any(output.iterdir()):
        raise ValueError("E_MATERIALIZER_OUTPUT")
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        snapshot = Path(temporary) / "snapshot"; snapshot.mkdir()
        context_path = _inside(example, str(slide.get("context", manifest["context"])))
        reference, _ = copy_context_closure(example, context_path, snapshot)
        closure = resolve_render_context(reference, LocalSnapshotReader(snapshot, reference["store"]["identity"]))
        rendered = render_review(RenderRequest(closure, snapshot, ReferenceScheduler(), renderer_for(
            {"kind": closure.context.target.kind, "capabilities": list(closure.context.target.capabilities)},
            closure.context.environment.renderer_environment(),
        )))
        derived = output / "review.svg"
        derived.write_bytes(rendered.artifact.content)
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
        (output / "closure.yaml").write_text(yaml.safe_dump(evidence, sort_keys=True))
        if write:
            expected.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(derived, expected)
        elif not expected.is_file() or derived.read_bytes() != expected.read_bytes():
            raise ValueError("E_MATERIALIZER_MISMATCH")
        return MaterializationResult(derived, reference, rendered)
