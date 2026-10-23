"""List every relation-ink / member-name / note-index pair within reach of the label gap in a Scene (#1848).

Run: python docs/reviews/current/assets-label-clearance/measure_label_clearance.py <review.scene.json> [<label-gap>]
     (PYTHONPATH=<worktree>/src:<worktree>)

`<label-gap>` is the declared `timeline.mark.labelGap`; without it each box uses a quarter of its font size (at
least one pixel). VIOL rows keep less than the gap; the gap is the painted-ink distance to the box, in px.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from tests.support.label_clearance import ink_gaps


def main(argv: list[str]) -> int:
    scene = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    gap = float(argv[1]) if len(argv) > 1 else None
    for item in ink_gaps(scene, label_gap=gap):
        print(f"{'VIOL' if item.violates else 'ok  '} {item.gap:6.2f} (gap {item.label_gap:g}) "
              f"{item.ink:15} {item.box:12} {item.text!r}  {item.relation}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
