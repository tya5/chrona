"""Immutable example/context materialization application service."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
import shutil
import tempfile
from typing import Any

import yaml

from chrona.presentation.model.closure import resolve_render_context
from chrona.presentation.renderers.registry import renderer_for
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.usecases.render_review import RenderRequest, RenderedReview, render_review


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


def _copy_reference(example: Path, reference: dict[str, Any], snapshot: Path) -> None:
    token, address = reference.get("revision", {}).get("token"), reference.get("address")
    if not isinstance(token, str) or not isinstance(address, str):
        raise ValueError("E_MATERIALIZER_CONTEXT")
    payload = _inside(example, address).read_bytes()
    if reference.get("contentIdentity") not in (None, _identity(payload)):
        raise ValueError("E_CONTENT_IDENTITY")
    target = _inside(snapshot / token, address)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    if reference.get("kind") == "snapshot-ref":
        nested = yaml.safe_load(payload).get("body", {}).get("project")
        if not isinstance(nested, dict):
            raise ValueError("E_MATERIALIZER_CONTEXT")
        _copy_reference(example, nested, snapshot)


def copy_context_closure(example: Path, context_path: Path, snapshot: Path) -> tuple[dict[str, Any], str]:
    raw = context_path.read_bytes()
    context = yaml.safe_load(raw)
    if context.get("version") != "chrona/render-context/v0.8" or context.get("kind") != "render-context":
        raise ValueError("E_MATERIALIZER_CONTEXT")
    body = context["body"]
    revision = body["project"]["revision"]["token"]
    references = [body[name] for name in ("project", "view", "theme", "colorScheme", "layout")]
    references.extend(body.get("inputs", {}).values())
    for item in references:
        _copy_reference(example, item, snapshot)
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
    manifest = yaml.safe_load(manifest_path.read_text())
    if manifest.get("version") != "chrona/example-materializer/v0.1":
        raise ValueError("E_MATERIALIZER_MANIFEST")
    slide = next((item for item in manifest.get("slides", ()) if item.get("id") == slide_id), None)
    if slide is None:
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
