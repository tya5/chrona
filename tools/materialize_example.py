"""Materialize one v0.5 example through Chrona's public render-review CLI."""
from __future__ import annotations

import argparse
from hashlib import sha256
from importlib.resources import files
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


def _inside(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if path != root.resolve() and root.resolve() not in path.parents:
        raise ValueError("E_MATERIALIZER_PATH")
    return path


def _copy_context_closure(example: Path, context_path: Path, snapshot: Path) -> tuple[dict, str]:
    raw = context_path.read_bytes(); context = yaml.safe_load(raw)
    if context.get("version") not in {"chrona/presentation/v0.5", "chrona/presentation/v0.6"} or context.get("kind") != "render-context":
        raise ValueError("E_MATERIALIZER_CONTEXT")
    body = context["body"]
    revision = body["project"]["revision"]["token"]
    def copy_reference(reference: dict) -> None:
        destination = snapshot / reference["revision"]["token"]
        destination.mkdir(parents=True, exist_ok=True)
        source = _inside(example, reference["address"])
        target = _inside(destination, reference["address"])
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
        if reference.get("kind") == "snapshot-ref":
            nested = yaml.safe_load(source.read_text()).get("body", {}).get("project")
            if not isinstance(nested, dict): raise ValueError("E_MATERIALIZER_CONTEXT")
            copy_reference(nested)
    for reference in [body[name] for name in ("project", "view", "theme", "colorScheme", "layout")] + list(body.get("inputs", {}).values()):
        copy_reference(reference)
    destination = snapshot / revision
    context_target = _inside(destination, context_path.relative_to(example).as_posix())
    context_target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(context_path, context_target)
    for asset in body["environment"]["fontMetrics"]["assets"]:
        relative = str(asset["path"])
        target = _inside(destination, relative); target.parent.mkdir(parents=True, exist_ok=True)
        source = files("chrona.resources").joinpath(relative)
        if not source.is_file(): raise ValueError("E_MATERIALIZER_FONT")
        target.write_bytes(source.read_bytes())
    reference = {"id": context["id"], "kind": "render-context", "store": body["project"]["store"],
                 "address": context_path.relative_to(example).as_posix(), "revision": {"token": revision},
                 "contentIdentity": "sha256:" + sha256(raw).hexdigest()}
    return reference, revision


def materialize(manifest_path: Path, slide_id: str, output: Path, *, write: bool) -> None:
    example = manifest_path.parent.resolve(); manifest = yaml.safe_load(manifest_path.read_text())
    if manifest.get("version") != "chrona/example-materializer/v0.1": raise ValueError("E_MATERIALIZER_MANIFEST")
    slide = next((item for item in manifest.get("slides", ()) if item.get("id") == slide_id), None)
    if slide is None: raise ValueError("E_MATERIALIZER_SLIDE")
    expected = _inside(example, str(slide["expectedSvg"]))
    if output.exists() and any(output.iterdir()): raise ValueError("E_MATERIALIZER_OUTPUT")
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        snapshot = Path(temporary) / "snapshot"; snapshot.mkdir()
        context_path = _inside(example, str(slide.get("context", manifest["context"])))
        reference, _ = _copy_context_closure(example, context_path, snapshot)
        ref_path = Path(temporary) / "context-ref.yaml"; ref_path.write_text(yaml.safe_dump(reference, sort_keys=False))
        derived = output / "review.svg"
        command = [sys.executable, "-c", "from chrona.app.cli import main; main()", "render-review", "--context-reference", str(ref_path), "--snapshot-root", str(snapshot), "--store-identity", reference["store"]["identity"], "--output", str(derived)]
        completed = subprocess.run(command, check=False, text=True, capture_output=True)
        if completed.returncode: raise ValueError("E_MATERIALIZER_RENDER:" + completed.stdout)
        closure = output / "closure.yaml"; closure.write_text(yaml.safe_dump(reference, sort_keys=True))
        if write:
            expected.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(derived, expected)
        elif not expected.is_file() or derived.read_bytes() != expected.read_bytes():
            raise ValueError("E_MATERIALIZER_MISMATCH")


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("manifest"); parser.add_argument("--slide", required=True); parser.add_argument("--output", required=True); parser.add_argument("--write", action="store_true")
    args = parser.parse_args(); materialize(Path(args.manifest), args.slide, Path(args.output), write=args.write)


if __name__ == "__main__": main()
