"""Materialize one v0.8 example through Chrona's public render-review CLI."""
from __future__ import annotations

import argparse
from hashlib import sha256
from importlib.resources import files
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
import yaml
from chrona.resources import safe_load
from chrona.usecases.materialize import copy_context_closure, materialize as _materialize
from chrona.storage.snapshot_paths import snapshot_directory


def _inside(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if path != root.resolve() and root.resolve() not in path.parents:
        raise ValueError("E_MATERIALIZER_PATH")
    return path


def _identity(payload: bytes) -> str:
    return "sha256:" + sha256(payload).hexdigest()


def _verify_identity(reference: dict[str, Any], payload: bytes) -> str:
    identity = _identity(payload)
    expected = reference.get("contentIdentity")
    if expected is not None and expected != identity:
        raise ValueError("E_CONTENT_IDENTITY")
    return identity


def _copy_reference(example: Path, reference: dict[str, Any], snapshot: Path) -> None:
    token = reference.get("revision", {}).get("token")
    address = reference.get("address")
    if not isinstance(token, str) or not isinstance(address, str):
        raise ValueError("E_MATERIALIZER_CONTEXT")
    source = _inside(example, address)
    payload = source.read_bytes()
    _verify_identity(reference, payload)
    target = _inside(snapshot_directory(snapshot, token), address)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    if reference.get("kind") == "snapshot-ref":
        nested = safe_load(payload).get("body", {}).get("project")
        if not isinstance(nested, dict):
            raise ValueError("E_MATERIALIZER_CONTEXT")
        _copy_reference(example, nested, snapshot)


def _legacy_copy_context_closure(example: Path, context_path: Path, snapshot: Path) -> tuple[dict[str, Any], str]:
    raw = context_path.read_bytes()
    context = safe_load(raw)
    if context.get("version") != "chrona/render-context/v0.8" or context.get("kind") != "render-context":
        raise ValueError("E_MATERIALIZER_CONTEXT")
    body = context["body"]
    revision = body["project"]["revision"]["token"]
    references = [body[name] for name in ("project", "view", "theme", "colorScheme", "layout")]
    references.extend(body.get("inputs", {}).values())
    for item in references:
        _copy_reference(example, item, snapshot)

    destination = snapshot_directory(snapshot, revision)
    context_target = _inside(destination, context_path.relative_to(example).as_posix())
    context_target.parent.mkdir(parents=True, exist_ok=True)
    context_target.write_bytes(raw)
    for asset in body["environment"]["fontMetrics"]["assets"]:
        relative = str(asset["path"])
        source = files("chrona.resources").joinpath(relative)
        if not source.is_file():
            raise ValueError("E_MATERIALIZER_FONT")
        payload = source.read_bytes()
        if asset.get("contentIdentity") not in (None, _identity(payload)):
            raise ValueError("E_MATERIALIZER_FONT_IDENTITY")
        target = _inside(destination, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    reference = {
        "id": context["id"], "kind": "render-context", "store": body["project"]["store"],
        "address": context_path.relative_to(example).as_posix(), "revision": {"token": revision},
        "contentIdentity": _identity(raw),
    }
    return reference, revision


def _legacy_materialize(manifest_path: Path, slide_id: str, output: Path, *, write: bool) -> None:
    example = manifest_path.parent.resolve()
    manifest = safe_load(manifest_path.read_bytes())
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
        snapshot = Path(temporary) / "snapshot"
        snapshot.mkdir()
        context_path = _inside(example, str(slide.get("context", manifest["context"])))
        reference, _ = _legacy_copy_context_closure(example, context_path, snapshot)
        ref_path = Path(temporary) / "context-ref.yaml"
        ref_path.write_text(yaml.safe_dump(reference, sort_keys=False), encoding="utf-8")
        derived = output / "review.svg"
        command = [sys.executable, "-c", "from chrona.app.cli import main; main()", "render-review",
                   "--context-reference", str(ref_path), "--snapshot-root", str(snapshot),
                   "--store-identity", reference["store"]["identity"],
                   "--output", str(derived)]
        completed = subprocess.run(command, check=False, text=True, capture_output=True)
        if completed.returncode:
            raise ValueError("E_MATERIALIZER_RENDER:" + completed.stdout)
        (output / "closure.yaml").write_text(yaml.safe_dump(reference, sort_keys=True), encoding="utf-8")
        if write:
            expected.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(derived, expected)
        elif not expected.is_file() or derived.read_bytes() != expected.read_bytes():
            raise ValueError("E_MATERIALIZER_MISMATCH")


_copy_context_closure = copy_context_closure


def materialize(manifest_path: Path, slide_id: str, output: Path, *, write: bool) -> None:
    """Compatibility developer wrapper around the public application service."""
    _materialize(manifest_path, slide_id, output, write=write)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("--slide", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    materialize(Path(args.manifest), args.slide, Path(args.output), write=args.write)


if __name__ == "__main__":
    main()
