#!/usr/bin/env python3
"""Check that tracked example files belong to a declared corpus closure."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable, Mapping

from chrona.resources import safe_load


ROOT = Path(__file__).resolve().parents[1]
IMAGE = re.compile(r"!\[[^]]*\]\(([^ )]+)")


class ExampleReachabilityError(ValueError):
    pass


def tracked(root: Path) -> tuple[Path, ...]:
    result = subprocess.run(("git", "-C", str(root), "ls-files", "-z", "examples"), check=False,
                            capture_output=True, text=False)
    if result.returncode:
        raise ExampleReachabilityError("E_EXAMPLE_REACHABILITY_TRACKED")
    return tuple(path for item in result.stdout.split(b"\0") if item
                 if (path := root / Path(item.decode("utf-8"))).is_file())


def _inside(root: Path, value: str) -> Path:
    candidate = (root / value).resolve()
    if root.resolve() not in (candidate, *candidate.parents):
        raise ExampleReachabilityError("E_EXAMPLE_REACHABILITY_PATH")
    return candidate


def _local_addresses(value: Any, root: Path) -> Iterable[tuple[Path, bool]]:
    if isinstance(value, Mapping):
        address = value.get("address")
        if isinstance(address, str):
            candidate = _inside(root, address)
            store = value.get("store")
            locator = value.get("locator")
            required = ((isinstance(store, Mapping) and store.get("provider") == "local")
                        or (isinstance(locator, Mapping) and locator.get("provider") in {"context", "local"}))
            if required or candidate.is_file():
                yield candidate, required
        for item in value.values():
            yield from _local_addresses(item, root)
    elif isinstance(value, list):
        for item in value:
            yield from _local_addresses(item, root)


def closure(root: Path) -> tuple[set[Path], dict[Path, set[Path]]]:
    reached: set[Path] = set()
    edges: dict[Path, set[Path]] = {}
    manifests = sorted(root.glob("*/manifest.yaml"))
    for manifest_path in manifests:
        example = manifest_path.parent.resolve()
        manifest = safe_load(manifest_path.read_bytes())
        if not isinstance(manifest, Mapping) or not isinstance(manifest.get("slides"), list):
            raise ExampleReachabilityError("E_EXAMPLE_REACHABILITY_MANIFEST")
        reached.add(manifest_path.resolve())
        queue: list[Path] = []
        default = manifest.get("context")
        for item in manifest["slides"]:
            if not isinstance(item, Mapping):
                raise ExampleReachabilityError("E_EXAMPLE_REACHABILITY_MANIFEST")
            for field in ("expectedSvg", "expectedScene"):
                if isinstance(item.get(field), str):
                    target = _inside(example, item[field])
                    if not target.is_file():
                        raise ExampleReachabilityError("E_EXAMPLE_REACHABILITY_MISSING:" + target.relative_to(root).as_posix())
                    reached.add(target); edges.setdefault(manifest_path.resolve(), set()).add(target)
            context = item.get("context", default)
            if not isinstance(context, str):
                raise ExampleReachabilityError("E_EXAMPLE_REACHABILITY_MANIFEST")
            target = _inside(example, context); queue.append(target); edges.setdefault(manifest_path.resolve(), set()).add(target)
        while queue:
            path = queue.pop()
            if path in reached:
                continue
            if not path.is_file():
                raise ExampleReachabilityError("E_EXAMPLE_REACHABILITY_MISSING:" + path.relative_to(root).as_posix())
            reached.add(path)
            if path.suffix not in {".yaml", ".yml"}:
                continue
            value = safe_load(path.read_bytes())
            for target, required in _local_addresses(value, example):
                if not target.is_file():
                    if required:
                        raise ExampleReachabilityError("E_EXAMPLE_REACHABILITY_MISSING:" + target.relative_to(root).as_posix())
                    continue
                edges.setdefault(path, set()).add(target)
                queue.append(target)
    return reached, edges


def supporting(root: Path) -> set[Path]:
    """Load the finite, reasoned non-materializer example population."""
    path = root / "examples/reachability.yaml"
    value = safe_load(path.read_bytes())
    entries = value.get("supportingFiles") if isinstance(value, Mapping) else None
    if (not isinstance(value, Mapping) or value.get("version") != "chrona/example-reachability/v0.1"
            or not isinstance(entries, list)):
        raise ExampleReachabilityError("E_EXAMPLE_REACHABILITY_SUPPORTING")
    resolved: set[Path] = {path.resolve()}
    for entry in entries:
        if (not isinstance(entry, Mapping) or not isinstance(entry.get("path"), str)
                or not isinstance(entry.get("reason"), str) or not entry["reason"].strip()):
            raise ExampleReachabilityError("E_EXAMPLE_REACHABILITY_SUPPORTING")
        target = _inside(root / "examples", entry["path"])
        if not target.is_file() or target in resolved:
            raise ExampleReachabilityError("E_EXAMPLE_REACHABILITY_SUPPORTING")
        resolved.add(target)
    return resolved


def readme_images(root: Path) -> tuple[str, ...]:
    return tuple(match.group(1) for match in IMAGE.finditer((root / "README.md").read_text(encoding="utf-8"))
                 if match.group(1).startswith("examples/"))


def reachable_view_paths(root: Path = ROOT) -> tuple[Path, ...]:
    """Return only manifest-reachable public View sources in stable order."""
    reached, _edges = closure(root / "examples")
    return tuple(sorted(path for path in reached if path.parent.name == "views" and path.suffix == ".yaml"))


def validate(root: Path) -> None:
    files = {path.resolve() for path in tracked(root)}
    reached, _edges = closure(root / "examples")
    reached.update(supporting(root))
    unreachable = sorted(path.relative_to(root).as_posix() for path in files - reached)
    if unreachable:
        raise ExampleReachabilityError("E_EXAMPLE_REACHABILITY_UNREACHABLE\n" + "\n".join(unreachable))
    evidence: set[str] = set()
    for manifest_path in sorted((root / "examples").glob("*/manifest.yaml")):
        manifest = safe_load(manifest_path.read_bytes())
        for slide in manifest["slides"]:
            expected = slide.get("expectedSvg")
            if isinstance(expected, str):
                evidence.add((manifest_path.parent / expected).relative_to(root).as_posix())
    invalid = sorted(image for image in readme_images(root) if image not in evidence)
    if invalid:
        raise ExampleReachabilityError("E_EXAMPLE_README_EVIDENCE\n" + "\n".join(invalid))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    validate(args.root.resolve())
    print("Example reachability: PASS")


if __name__ == "__main__":
    main()
