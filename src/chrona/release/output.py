"""Declared-capability output coordination over completed Scenes."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from chrona.presentation.renderers.generic import render_svg
from chrona.presentation.scene.schedule import Scene


@dataclass(frozen=True)
class OutputResult:
    artifact: str | None
    manifest: dict[str, Any]
    diagnostics: tuple[str, ...]


def render_output(scene: Scene, evaluation_identity: str, target: dict[str, Any], request: dict[str, Any] | None = None) -> OutputResult:
    request = request or {}
    capabilities = dict(target.get("capabilities", {}))
    required = set(request.get("requires", []))
    missing = sorted(name for name in required if not capabilities.get(name, False))
    manifest = {"evaluationIdentity": evaluation_identity, "target": target.get("target"), "targetVersion": target.get("version"), "diagnostics": []}
    if missing:
        manifest["diagnostics"] = ["E_OUTPUT_CAPABILITY_MISSING"]
        return OutputResult(None, manifest, ("E_OUTPUT_CAPABILITY_MISSING",))
    losses = sorted(name for name in request.get("permitsFidelityLoss", []) if not capabilities.get(name, False))
    diagnostics = tuple("W_OUTPUT_FIDELITY_LOSS" for _ in losses)
    manifest["diagnostics"] = list(diagnostics)
    manifest["fidelityLoss"] = losses
    if target.get("target") != "svg":
        return OutputResult(None, manifest, ("E_OUTPUT_TARGET_UNSUPPORTED",) + diagnostics)
    svg_capabilities = {"marker", "metadata", "text-alternative"}
    artifact = render_svg(scene, svg_capabilities)
    return OutputResult(artifact, manifest, diagnostics)
