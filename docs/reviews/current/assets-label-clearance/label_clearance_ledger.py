"""Per-slide before/after ledger of the relation-ink label gap over the public slides (#1848).

Run: python docs/reviews/current/assets-label-clearance/label_clearance_ledger.py <worktree> <before-dir> <after-dir> <out.md>
     (PYTHONPATH=<worktree>/src:<worktree>; both directories come from render_public_slides.py)

Each row gives the SVG and Scene SHA-256 (first 12 hex) before and after; for a changed slide the paired-stub fragment
count, the member-name count (and any name that is gone), note indices, relations whose route changed, and the number
of relation-ink/name/index pairs closer than the label gap with the smallest such distance. The gap is the Spec 07
fallback (a quarter of the label font size, at least one pixel) because no public slide but a reviewer overlay binds one.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from chrona.resources import safe_load
from tests.support.label_clearance import ink_gaps, violations

FIRST = ("02", "11", "12", "16", "19", "21", "22", "23", "24", "25")  # HALCYON slide numbers, reviewed first


def _labels(root: Path) -> dict[str, str]:
    """`<example>/<slide>` to a display name; a HALCYON slide carries the number of its generated file."""
    slide_names: dict[str, str] = {}
    for manifest in sorted((root / "examples").glob("*/manifest.yaml")):
        for slide in safe_load(manifest.read_bytes())["slides"]:
            number = Path(str(slide["expectedSvg"])).name.split("-", 1)[0]
            key = f"{manifest.parent.name}/{slide['id']}"
            slide_names[key] = (f"HALCYON {number} {slide['id']}" if manifest.parent.name == "halcyon-1"
                          and number.isdigit() else key)
    return slide_names


def _load(directory: Path) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for scene in sorted(directory.glob("*/*/review.scene.json")):
        raw, svg = scene.read_bytes(), (scene.parent / "review.svg").read_bytes()
        result[f"{scene.parent.parent.name}/{scene.parent.name}"] = {
            "scene": hashlib.sha256(raw).hexdigest()[:12], "svg": hashlib.sha256(svg).hexdigest()[:12],
            "document": json.loads(raw.decode("utf-8"))}
    return result


def _facts(document: dict) -> dict:
    primitives = document["surfaces"][0]["primitives"]
    routes = {item["id"]: item["points"] for item in primitives
              if item["kind"] == "Path" and item["purpose"] == "dependency"}
    close = violations(ink_gaps(document))
    return {"routes": routes, "stubs": sum(":stub-" in key for key in routes),
            "names": sorted(item["text"] for item in primitives
                            if item["kind"] == "Text" and item["purpose"] == "member-label"),
            "indices": sorted(item["text"] for item in primitives
                              if item["kind"] == "Text" and item["purpose"] == "note-index"),
            "close": len(close), "least": min((item.gap for item in close), default=None)}


def _gap(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"


def main(argv: list[str]) -> int:
    slide_names = _labels(Path(argv[0]))
    before, after = _load(Path(argv[1])), _load(Path(argv[2]))
    assert before.keys() == after.keys(), "both trees must render the same slides"
    rows = ["| slide | SVG before > after | Scene before > after | stubs | member names | note indices "
            "| routes changed | pairs inside gap (least px) |",
            "| --- | --- | --- | ---: | --- | --- | ---: | --- |"]
    changed = []

    def order(key: str) -> tuple:
        number = slide_names[key].split(" ")[1] if slide_names[key].startswith("HALCYON") else ""
        return (FIRST.index(number) if number in FIRST else len(FIRST), slide_names[key])

    for key in sorted(before, key=order):
        old, new = before[key], after[key]
        if old["svg"] == new["svg"] and old["scene"] == new["scene"]:
            rows.append(f"| {slide_names[key]} | `{old['svg']}` unchanged | `{old['scene']}` unchanged | - | - | - | 0 | - |")
            continue
        changed.append(key)
        fb, fa = _facts(old["document"]), _facts(new["document"])
        lost = sorted(set(fb["names"]) - set(fa["names"]))
        names = f"{len(fb['names'])} > {len(fa['names'])}" + (f", lost {lost}" if lost else "")
        routes = sum(1 for key_ in fa["routes"] if fb["routes"].get(key_) != fa["routes"][key_])
        rows.append(f"| {slide_names[key]} | `{old['svg']}` > `{new['svg']}` | `{old['scene']}` > `{new['scene']}` "
                    f"| {fb['stubs']} > {fa['stubs']} | {names} | {len(fb['indices'])} > {len(fa['indices'])} "
                    f"| {routes} of {len(fa['routes'])} | {fb['close']} ({_gap(fb['least'])}) > "
                    f"{fa['close']} ({_gap(fa['least'])}) |")
    Path(argv[3]).write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    print(f"slides: {len(before)}; changed: {len(changed)}")
    Path(argv[3]).with_suffix(".changed.txt").write_text("\n".join(changed) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
