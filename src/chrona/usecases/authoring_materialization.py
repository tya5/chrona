"""One-way guided-preset materialization into a locally owned explicit bundle."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import tempfile
from typing import Any

import yaml

from chrona.presentation.contracts import ClosureIdentity, AuthoringWorkspaceContract, PresentationPresetContract, parse_contract
from chrona.presentation.model.authoring import normalize_authoring_workspace
from chrona.presentation.model.closure import _packaged_font_metrics


def materialize_presentation_preset(workspace_path: Path, *, directory: str = "presentation") -> dict[str, Any]:
    """Write an explicit bundle, then atomically switch a guided workspace to it."""
    root = workspace_path.parent.resolve()
    workspace = yaml.safe_load(workspace_path.read_text())
    workspace_contract = parse_contract(_identity("authoring-workspace", workspace), workspace)
    if not isinstance(workspace_contract, AuthoringWorkspaceContract) or workspace_contract.mode != "guided" or workspace_contract.binding is None:
        raise ValueError("E_AUTHORING_EXPLICIT_MODE")
    preset_path = _child(root, str(workspace_contract.binding["preset"]["path"]))
    preset = yaml.safe_load(preset_path.read_text())
    preset_contract = parse_contract(_identity("presentation-preset", preset), preset)
    if not isinstance(preset_contract, PresentationPresetContract):
        raise ValueError("E_AUTHORING_PRESET_SCHEMA")
    acquired = {str(item["path"]): yaml.safe_load(_child(preset_path.parent, str(item["path"])).read_text())
                for item in (*preset_contract.resources.values(), *preset_contract.compatible_color_schemes)}
    normalized = normalize_authoring_workspace(workspace_contract, preset_contract, acquired)
    target = _child(root, directory)
    if target.exists():
        raise ValueError("E_AUTHORING_MATERIALIZE_COLLISION")
    binding_identity = _digest(_plain(workspace_contract.binding))
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        staged = Path(temporary) / directory
        staged.mkdir()
        sources = dict(normalized.draft_sources())
        names = {"project": "project.yaml", "actual-set": "actual.yaml", "view": "view.yaml", "theme": "theme.yaml", "color-scheme": "scheme.yaml", "layout-profile": "layout.yaml"}
        written: dict[str, dict[str, Any]] = {}
        for kind, filename in names.items():
            if kind not in sources:
                continue
            payload = yaml.safe_dump(sources[kind], sort_keys=False).encode()
            (staged / filename).write_bytes(payload)
            identifier = sources[kind].get("id") if kind != "project" else sources[kind]["project"]["id"]
            written[kind] = {"id": str(identifier), "kind": kind, "path": f"{directory}/{filename}", "contentIdentity": _digest_bytes(payload)}
        context = _context(sources, written)
        context_payload = yaml.safe_dump(context, sort_keys=False).encode()
        (staged / "context.yaml").write_bytes(context_payload)
        written["render-context"] = {"id": context["id"], "kind": "render-context", "path": f"{directory}/context.yaml", "contentIdentity": _digest_bytes(context_payload)}
        receipt = {"version": "chrona/presentation-materialization-receipt/v0.1", "kind": "presentation-materialization-receipt", "id": f"{workspace['id']}-receipt", "body": {"presetContentIdentity": _digest(preset), "bindingContentIdentity": binding_identity, "normalizerVersion": "chrona/authoring-normalizer/v0.1", "resources": {key: value["contentIdentity"] for key, value in written.items()}}}
        receipt_payload = yaml.safe_dump(receipt, sort_keys=False).encode()
        (staged / "receipt.yaml").write_bytes(receipt_payload)
        explicit = deepcopy(workspace)
        explicit["body"]["presentation"] = {"mode": "explicit", "resources": {"view": written["view"], "theme": written["theme"], "colorScheme": written["color-scheme"], "layout": written["layout-profile"], "renderContext": written["render-context"]}, "receipt": {"id": receipt["id"], "kind": receipt["kind"], "path": f"{directory}/receipt.yaml", "contentIdentity": _digest_bytes(receipt_payload)}}
        parse_contract(_identity("authoring-workspace", explicit), explicit)
        staged.replace(target)
        temporary_workspace = workspace_path.with_name(f".{workspace_path.name}.materialize")
        temporary_workspace.write_text(yaml.safe_dump(explicit, sort_keys=False))
        temporary_workspace.replace(workspace_path)
    return explicit


def _context(sources: dict[str, Any], written: dict[str, dict[str, Any]]) -> dict[str, Any]:
    asset_root = Path(__file__).resolve().parents[1] / "resources"
    ref = lambda key: {**written[key], "store": {"provider": "draft", "identity": "draft"}, "address": written[key]["path"], "revision": {"token": "draft"}}
    return {"version": "chrona/render-context/v0.8", "kind": "render-context", "id": "materialized-context", "body": {"project": ref("project"), "view": ref("view"), "theme": ref("theme"), "colorScheme": ref("color-scheme"), "layout": ref("layout-profile"), "inputs": ({"actual": ref("actual-set")} if "actual-set" in written else {}), "environment": {"viewport": {"inlineSize": 1600, "blockSize": 900}, "locale": "en-US", "fontMetrics": _packaged_font_metrics(asset_root), "scenePrecision": 3}, "target": {"kind": "svg", "capabilities": ["accessibleText", "hierarchicalAxis", "marker", "semanticRoles", "sourceMetadata", "tableSemantics"]}}}


def _child(root: Path, relative: str) -> Path:
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
    identifier = value["id"]
    return ClosureIdentity(kind, str(identifier), "draft", _digest(value))
