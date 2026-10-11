#!/usr/bin/env python3
"""Discover and deterministically materialize public derived evidence."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Mapping

from chrona.resources import safe_load
from tools.materialize_example import materialize
from tools.derived_report_inventory import REPORTS


ROOT = Path(__file__).resolve().parents[1]
REPORT_COMMANDS = (
    ("tools.axis_name_tables",),
    ("tools.declared_value_inventory",),
    ("tools.diagnostic_inventory",),
    ("tools.presentation_contrast",),
    ("tools.presentation_font_identity",),
    ("tools.vocabulary_inventory",),
    ("tools.presentation_coverage",),
    ("tools.semantic_realization_coverage",),
    ("tools.corpus_coverage",),
)
_COPY_IGNORE = shutil.ignore_patterns(
    ".git", ".venv", ".venv*", "__pycache__", ".pytest_cache", "build", "dist",
)


def manifest_targets(root: Path = ROOT) -> tuple[tuple[Path, str], ...]:
    """Return stable (manifest, slide ID) entries from authored manifests."""
    targets: list[tuple[Path, str]] = []
    for manifest_path in sorted((root / "examples").glob("*/manifest.yaml")):
        manifest = safe_load(manifest_path.read_bytes())
        slides = manifest.get("slides") if isinstance(manifest, Mapping) else None
        if not isinstance(slides, list):
            raise ValueError(f"E_DERIVED_EVIDENCE_MANIFEST:{manifest_path}")
        slide_ids: set[str] = set()
        for slide in slides:
            slide_id = slide.get("id") if isinstance(slide, Mapping) else None
            if not isinstance(slide_id, str) or not slide_id or slide_id in slide_ids:
                raise ValueError(f"E_DERIVED_EVIDENCE_MANIFEST:{manifest_path}")
            slide_ids.add(slide_id)
            targets.append((manifest_path, slide_id))
    return tuple(targets)


def materializer_outputs(root: Path = ROOT) -> tuple[Path, ...]:
    """Return every manifest-declared SVG and Scene output in stable order."""
    outputs: list[Path] = []
    for manifest_path, slide_id in manifest_targets(root):
        manifest = safe_load(manifest_path.read_bytes())
        slide = next(item for item in manifest["slides"] if item["id"] == slide_id)
        for key in ("expectedSvg", "expectedScene"):
            value = slide.get(key)
            if key == "expectedScene" and value is None:
                continue
            if not isinstance(value, str) or not value:
                raise ValueError(f"E_DERIVED_EVIDENCE_PATH:{manifest_path}:{slide_id}:{key}")
            candidate = (manifest_path.parent / value).resolve()
            base = manifest_path.parent.resolve()
            if candidate == base or base not in candidate.parents:
                raise ValueError(f"E_DERIVED_EVIDENCE_PATH:{manifest_path}:{slide_id}:{key}")
            outputs.append(candidate)
    if len(set(outputs)) != len(outputs):
        raise ValueError("E_DERIVED_EVIDENCE_DUPLICATE_OUTPUT")
    return tuple(sorted(outputs))


def scene_paths(root: Path = ROOT) -> tuple[Path, ...]:
    """Return all manifest-declared Scene files, including untracked ones."""
    scenes = []
    for manifest_path, slide_id in manifest_targets(root):
        manifest = safe_load(manifest_path.read_bytes())
        slide = next(item for item in manifest["slides"] if item["id"] == slide_id)
        value = slide.get("expectedScene")
        if value is not None:
            if not isinstance(value, str) or not value:
                raise ValueError(f"E_DERIVED_EVIDENCE_PATH:{manifest_path}:{slide_id}:expectedScene")
            candidate = (manifest_path.parent / value).resolve()
            base = manifest_path.parent.resolve()
            if candidate == base or base not in candidate.parents:
                raise ValueError(f"E_DERIVED_EVIDENCE_PATH:{manifest_path}:{slide_id}:expectedScene")
            scenes.append(candidate)
    if len(set(scenes)) != len(scenes):
        raise ValueError("E_DERIVED_EVIDENCE_DUPLICATE_SCENE")
    return tuple(sorted(scenes))


def scene_contexts(root: Path = ROOT) -> dict[Path, Path]:
    """Map each manifest-declared Scene to its immutable Context path."""
    contexts: dict[Path, Path] = {}
    for manifest_path, slide_id in manifest_targets(root):
        manifest = safe_load(manifest_path.read_bytes())
        slide = next(item for item in manifest["slides"] if item["id"] == slide_id)
        scene_value = slide.get("expectedScene")
        if not isinstance(scene_value, str) or not scene_value:
            raise ValueError(f"E_DERIVED_EVIDENCE_PATH:{manifest_path}:{slide_id}:expectedScene")
        scene = (manifest_path.parent / scene_value).resolve()
        context_value = slide.get("context", manifest.get("context"))
        if not isinstance(context_value, str):
            raise ValueError(f"E_DERIVED_EVIDENCE_CONTEXT:{manifest_path}:{slide_id}")
        context = (manifest_path.parent / context_value).resolve()
        base = manifest_path.parent.resolve()
        if scene in contexts or context == base or base not in context.parents:
            raise ValueError(f"E_DERIVED_EVIDENCE_CONTEXT:{manifest_path}:{slide_id}")
        contexts[scene] = context
    return contexts


def validate_no_orphan_materializers(root: Path = ROOT) -> None:
    """Reject generated SVG/Scene files that no authored manifest declares."""
    expected = set(materializer_outputs(root))
    actual = set()
    for example in sorted((root / "examples").iterdir()):
        generated = example / "generated"
        if generated.is_dir():
            actual.update(path.resolve() for path in generated.rglob("*.svg"))
            actual.update(path.resolve() for path in generated.rglob("*.scene.json"))
    orphans = sorted(actual - expected)
    if orphans:
        raise ValueError("E_DERIVED_EVIDENCE_UNDECLARED_OUTPUT:" + ",".join(
            path.relative_to(root.resolve()).as_posix() for path in orphans))


def validate_materializers_present(root: Path = ROOT) -> None:
    """Fail check mode when any authored output path has not been generated."""
    missing = [path for path in materializer_outputs(root) if not path.is_file()]
    if missing:
        raise ValueError("E_DERIVED_EVIDENCE_MISSING_OUTPUT:" + ",".join(
            path.relative_to(root.resolve()).as_posix() for path in missing))


def derived_paths(root: Path = ROOT) -> tuple[Path, ...]:
    """Return the closed derived-output inventory: every manifest-declared SVG and Scene, then the reports."""
    return tuple(sorted((*materializer_outputs(root), *(root / item for item in REPORTS))))


def _generate(root: Path, *, write: bool, jobs: int) -> None:
    targets = manifest_targets(root)

    def render(target: tuple[Path, str]) -> None:
        manifest, slide_id = target
        # Materializer outputs are written only after their input closure and
        # renderer have completed successfully.
        with TemporaryDirectory(prefix="chrona-derived-slide-") as temporary:
            materialize(manifest, slide_id, Path(temporary) / "output", write=write)

    with ThreadPoolExecutor(max_workers=jobs) as executor:
        tuple(executor.map(render, targets))
    mode = "--write" if write else "--check"
    for script in REPORT_COMMANDS:
        command = [sys.executable, "-m", *script]
        if script[0] == "tools.axis_name_tables" or not write:
            command.append(mode)
        completed = subprocess.run(command, cwd=root, check=False, capture_output=True, text=True)
        if completed.returncode:
            detail = (completed.stderr or completed.stdout)[-2000:]
            raise RuntimeError(f"E_DERIVED_EVIDENCE_GENERATOR:{script[0]}:{completed.returncode}:{detail}")


def _publish_staged_outputs(staged_root: Path, root: Path, paths: tuple[Path, ...]) -> None:
    """Copy complete staged bytes through same-directory atomic replacements."""
    from tempfile import NamedTemporaryFile

    for relative in paths:
        source = staged_root / relative
        destination = root / relative
        if not source.is_file():
            raise RuntimeError(f"E_DERIVED_EVIDENCE_MISSING_STAGED:{relative.as_posix()}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("wb", dir=destination.parent, delete=False) as temporary:
            temporary.write(source.read_bytes())
            temp_path = Path(temporary.name)
        temp_path.replace(destination)


def main(argv: tuple[str, ...] = tuple(sys.argv[1:])) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args(argv)
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    root = args.root.resolve()
    inventory = derived_paths(root)
    validate_no_orphan_materializers(root)
    if args.check:
        validate_materializers_present(root)
        _generate(root, write=False, jobs=args.jobs)
    else:
        # Stage the complete generation before touching canonical paths. This
        # also makes generator failures leave the source tree unchanged.
        with TemporaryDirectory(prefix="chrona-derived-evidence-") as temporary:
            # macOS may spell the same temporary directory as /var or
            # /private/var; use one canonical root for inventory paths.
            staged_root = Path(temporary).resolve() / "repo"
            shutil.copytree(root, staged_root, ignore=_COPY_IGNORE)
            _generate(staged_root, write=True, jobs=args.jobs)
            staged_inventory = derived_paths(staged_root)
            relative_inventory = tuple(path.relative_to(staged_root) for path in staged_inventory)
            _publish_staged_outputs(staged_root, root, relative_inventory)
    print(f"Derived evidence: {'regenerated' if args.write else 'PASS'} ({len(inventory)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
