"""Build and prove a Stage-3 candidate; persistence belongs to the Command Engine."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import tempfile
from typing import Any

import yaml

from chrona.presentation.contracts import ClosureIdentity, AuthoringWorkspaceContract, PresentationPresetContract, parse_contract
from chrona.presentation.model.authoring import normalize_authoring_workspace
from chrona.presentation.model.closure import _packaged_font_metrics, resolve_draft_render, resolve_guided_draft_render
from chrona.presentation.renderers.registry import renderer_for
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderRequest, render_review
from chrona.resources import safe_load


def materialization_candidate(workspace_path: Path, workspace: dict[str, Any], *, directory: str) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Return a closed explicit candidate only after byte-equivalence proof."""
    root = workspace_path.parent.resolve()
    workspace_contract = parse_contract(_identity("authoring-workspace", workspace), workspace)
    if not isinstance(workspace_contract, AuthoringWorkspaceContract) or workspace_contract.mode != "guided" or workspace_contract.binding is None:
        raise ValueError("E_AUTHORING_EXPLICIT_MODE")
    _relative(directory)
    guided_bytes = _render_bytes(resolve_guided_draft_render(workspace_path=workspace_path))
    preset_path = _child(root, str(workspace_contract.binding["preset"]["path"]))
    preset = safe_load(preset_path.read_text(encoding="utf-8"))
    preset_contract = parse_contract(_identity("presentation-preset", preset), preset)
    if not isinstance(preset_contract, PresentationPresetContract):
        raise ValueError("E_AUTHORING_PRESET_SCHEMA")
    acquired = {str(item["path"]): safe_load(_child(preset_path.parent, str(item["path"])).read_text(encoding="utf-8"))
                for item in (*preset_contract.resources.values(), *preset_contract.compatible_color_schemes)}
    normalized = normalize_authoring_workspace(workspace_contract, preset_contract, acquired)
    sources = dict(normalized.draft_sources())
    names = {"project": "project.yaml", "actual-set": "actual.yaml", "view": "view.yaml", "theme": "theme.yaml", "color-scheme": "scheme.yaml", "layout-profile": "layout.yaml"}
    candidates: dict[str, bytes] = {}
    written: dict[str, dict[str, Any]] = {}
    for kind, filename in names.items():
        if kind not in sources:
            continue
        payload = yaml.safe_dump(sources[kind], sort_keys=True).encode()
        relative = f"{directory}/{filename}"
        candidates[relative] = payload
        identifier = sources[kind].get("id") if kind != "project" else sources[kind]["project"]["id"]
        written[kind] = {"id": str(identifier), "kind": kind, "path": relative, "contentIdentity": _digest_bytes(payload)}
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        staged = Path(temporary)
        for relative, payload in candidates.items():
            path = staged / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        explicit_draft = resolve_draft_render(
            project_path=staged / written["project"]["path"], view_path=staged / written["view"]["path"],
            theme_path=staged / written["theme"]["path"], scheme_path=staged / written["color-scheme"]["path"],
            layout_path=staged / written["layout-profile"]["path"],
            actual_path=(staged / written["actual-set"]["path"]) if "actual-set" in written else None,
        )
        if _render_bytes(explicit_draft) != guided_bytes:
            raise ValueError("E_AUTHORING_MATERIALIZE_OUTPUT_PROOF")
    context = _context(written)
    context_payload = yaml.safe_dump(context, sort_keys=True).encode()
    candidates[f"{directory}/context.yaml"] = context_payload
    written["render-context"] = {"id": context["id"], "kind": "render-context", "path": f"{directory}/context.yaml", "contentIdentity": _digest_bytes(context_payload)}
    receipt = {"version": "chrona/presentation-materialization-receipt/v0.1", "kind": "presentation-materialization-receipt", "id": f"{workspace['id']}-receipt", "body": {"presetContentIdentity": _digest(preset), "bindingContentIdentity": _digest(_plain(workspace_contract.binding)), "normalizerVersion": "chrona/authoring-normalizer/v0.1", "resources": {key: value["contentIdentity"] for key, value in written.items()}}}
    receipt_payload = yaml.safe_dump(receipt, sort_keys=True).encode()
    candidates[f"{directory}/receipt.yaml"] = receipt_payload
    explicit = deepcopy(workspace)
    explicit["body"]["presentation"] = {"mode": "explicit", "resources": {"view": written["view"], "theme": written["theme"], "colorScheme": written["color-scheme"], "layout": written["layout-profile"], "renderContext": written["render-context"]}, "receipt": {"id": receipt["id"], "kind": receipt["kind"], "path": f"{directory}/receipt.yaml", "contentIdentity": _digest_bytes(receipt_payload)}}
    parse_contract(_identity("authoring-workspace", explicit), explicit)
    candidates[workspace_path.name] = yaml.safe_dump(explicit, sort_keys=False).encode()
    return explicit, candidates


def _context(written: dict[str, dict[str, Any]]) -> dict[str, Any]:
    asset_root = Path(__file__).resolve().parents[1] / "resources"
    def ref(key: str) -> dict[str, Any]:
        return {**written[key], "store": {"provider": "draft", "identity": "draft"}, "address": written[key]["path"], "revision": {"token": "draft"}}
    return {"version": "chrona/render-context/v0.15", "kind": "render-context", "id": "materialized-context", "body": {"project": ref("project"), "view": ref("view"), "theme": ref("theme"), "colorScheme": ref("color-scheme"), "layout": ref("layout-profile"), "inputs": ({"actual": ref("actual-set")} if "actual-set" in written else {}), "environment": {"viewport": {"inlineSize": 1600, "blockSize": 900}, "locale": "en-US", "fontMetrics": _packaged_font_metrics(asset_root), "scenePrecision": 3}, "target": {"kind": "svg", "capabilities": ["accessibleText", "hierarchicalAxis", "marker", "semanticRoles", "sourceMetadata", "tableSemantics"], "visualProfile": "chrona-output/visual/v0.5-baseline"}}}


def _render_bytes(draft: Any) -> bytes:
    closure = draft.closure
    rendered = render_review(RenderRequest(closure, draft.asset_root, ReferenceScheduler(), asset_root=draft.asset_root))
    return rendered.artifact.content


def _relative(value: str) -> None:
    if not value or Path(value).is_absolute() or any(part in {"", ".", ".."} for part in Path(value).parts):
        raise ValueError("E_AUTHORING_MATERIALIZE_PATH")


def _child(root: Path, relative: str) -> Path:
    _relative(relative)
    value = (root / relative).resolve()
    if root not in value.parents:
        raise ValueError("E_AUTHORING_MATERIALIZE_PATH")
    return value


def _plain(value: Any) -> Any:
    if isinstance(value, dict): return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [_plain(v) for v in value]
    return value


def _digest(value: Any) -> str:
    return _digest_bytes(yaml.safe_dump(_plain(value), sort_keys=True).encode())


def _digest_bytes(payload: bytes) -> str:
    return "sha256:" + sha256(payload).hexdigest()


def _identity(kind: str, value: dict[str, Any]) -> ClosureIdentity:
    return ClosureIdentity(kind, str(value["id"]), "draft", _digest(value))
