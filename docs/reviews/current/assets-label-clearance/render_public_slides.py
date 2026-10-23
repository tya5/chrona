"""Render every public example slide into <out>/<example>/<slide>/ without touching `examples/` (#1848).

Run: python docs/reviews/current/assets-label-clearance/render_public_slides.py <worktree> <out> [<slide-id> ...]
     (PYTHONPATH=<worktree>/src:<worktree>:<worktree>/packages/chrona-fonts-noto-cjk/src, absolute paths)

`materialize(write=False)` writes review.svg and review.scene.json into the output directory before it compares them
with the committed evidence, so a changed slide raises E_MATERIALIZER_MISMATCH after its files exist. That mismatch is
the expected derived diff of a changed public slide and is only counted here.
"""
from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from chrona.resources import safe_load
from chrona.usecases.materialize import MaterializationError, materialize


def main(argv: list[str]) -> int:
    root, out, only = Path(argv[0]).resolve(), Path(argv[1]), set(argv[2:])
    targets = [(manifest, str(slide["id"])) for manifest in sorted((root / "examples").glob("*/manifest.yaml"))
               for slide in safe_load(manifest.read_bytes())["slides"] if not only or str(slide["id"]) in only]
    mismatched: list[str] = []

    def run(target: tuple[Path, str]) -> None:
        manifest, slide_id = target
        try:
            materialize(manifest, slide_id, out / manifest.parent.name / slide_id, write=False)
        except MaterializationError as error:
            if error.code != "E_MATERIALIZER_MISMATCH":
                raise
            mismatched.append(f"{manifest.parent.name}/{slide_id}")

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(run, targets))
    print(f"slides rendered: {len(targets)}; differing from committed evidence: {len(mismatched)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
