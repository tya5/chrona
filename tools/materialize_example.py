"""Materialize every slide of an example manifest into immutable Render Contexts and render them.

The authoring resources stay where the author put them; this tool copies their exact bytes into
a temporary local snapshot store, writes one generated `chrona/presentation/v0.5` Render Context per
slide (so no one guesses hashes), runs `chrona render-review` on it, and records the generated
Context next to the example so the binding is reviewable.

    python tools/materialize_example.py examples/halcyon-1/manifest.yaml [--check]

`--check` renders into a temporary directory and fails when any output differs from the checked-in
`expected.svg`, which is how the acceptance tests use it.
"""
from __future__ import annotations

import argparse
import base64
import json
import shutil
import subprocess
import sys
import tempfile
from hashlib import sha256
from html import escape
from pathlib import Path
from typing import Any

import yaml

from importlib.resources import files

TOKEN = "example-v1"
CAPABILITIES = ["accessibleText", "hierarchicalAxis", "marker", "semanticRoles", "sourceMetadata", "tableSemantics"]
DEFAULT_FONTS = ("nimbus-sans-regular-v1.json", "nimbus-sans-bold-v1.json")
DEFAULT_VIEWPORT = {"inlineSize": 1600, "blockSize": 900}


def _reference(store: Path, example: Path, address: str, kind: str, identity: str) -> dict[str, Any]:
    payload = (example / address).read_bytes()
    target = store / TOKEN / address
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    document = yaml.safe_load(payload)
    resource_id = document.get("id") or document.get("project", {}).get("id")
    return {"id": resource_id, "kind": kind, "store": {"provider": "local", "identity": identity},
            "address": address, "revision": {"token": TOKEN},
            "contentIdentity": "sha256:" + sha256(payload).hexdigest()}


def _font_assets(store: Path, names: tuple[str, ...]) -> list[dict[str, Any]]:
    assets = []
    for name in names:
        payload = files("chrona.resources").joinpath("font_metrics", name).read_bytes()
        target = store / TOKEN / "font_metrics" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        meta = json.loads(payload)
        assets.append({"family": meta["family"], "weight": meta["weight"], "revision": name.removesuffix(".json"),
                       "contentIdentity": "sha256:" + sha256(payload).hexdigest(), "path": f"font_metrics/{name}"})
    return assets


def build_context(store: Path, example: Path, manifest: dict[str, Any], slide: dict[str, Any], identity: str) -> dict[str, Any]:
    pick = lambda key: slide.get(key) or manifest[key]  # noqa: E731
    body: dict[str, Any] = {
        "project": _reference(store, example, manifest["project"], "project", identity),
        "view": _reference(store, example, slide["view"], "view", identity),
        "theme": _reference(store, example, pick("theme"), "theme", identity),
        "colorScheme": _reference(store, example, pick("colorScheme"), "color-scheme", identity),
        "layout": _reference(store, example, pick("layout"), "layout-profile", identity),
        "inputs": {},
    }
    if manifest.get("actual"):
        body["inputs"]["actual"] = _reference(store, example, manifest["actual"], "actual-set", identity)
    for key, kind, name in (("summaryProfile", "summary-profile", "summaryProfile"),
                            ("detailProfile", "review-detail-profile", "detailProfile")):
        address = slide.get(name) or manifest.get(name)
        if address:
            body["inputs"][key] = _reference(store, example, address, kind, identity)
    viewport = dict(DEFAULT_VIEWPORT, **(slide.get("viewport") or manifest.get("viewport") or {}))
    body["environment"] = {"viewport": viewport, "locale": manifest.get("locale", "en-US"),
                           "fontMetrics": {"algorithm": "declared-metrics-v1",
                                           "assets": _font_assets(store, tuple(manifest.get("fonts", DEFAULT_FONTS))),
                                           "missingFont": "diagnose"},
                           "scenePrecision": 3}
    body["target"] = {"kind": "svg", "capabilities": CAPABILITIES}
    return {"version": "chrona/presentation/v0.5", "kind": "render-context",
            "id": f"{example.name}-{Path(slide['view']).stem}", "body": body}


def render_slide(store: Path, example: Path, manifest: dict[str, Any], slide: dict[str, Any], output: Path) -> bytes:
    identity = f"{example.name}-example"
    context = build_context(store, example, manifest, slide, identity)
    payload = yaml.safe_dump(context, sort_keys=False).encode()
    address = f"contexts/{Path(slide['view']).stem}.yaml"
    (store / TOKEN / address).parent.mkdir(parents=True, exist_ok=True)
    (store / TOKEN / address).write_bytes(payload)
    reference = {"id": context["id"], "kind": "render-context", "store": {"provider": "local", "identity": identity},
                 "address": address, "revision": {"token": TOKEN}, "contentIdentity": "sha256:" + sha256(payload).hexdigest()}
    reference_path = store / f"{Path(slide['view']).stem}-reference.yaml"
    reference_path.write_text(yaml.safe_dump(reference), encoding="utf-8")
    command = [sys.executable, "-c", "from chrona.app.cli import main; main()", "render-review",
               "--context-reference", str(reference_path), "--snapshot-root", str(store),
               "--store-identity", identity, "--output", str(output)]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise SystemExit(f"{slide['view']}: render-review failed\n{completed.stdout}{completed.stderr}")
    return payload


def gallery_html(title: str, slides: list[tuple[str, Path]]) -> str:
    sections = []
    for name, svg_path in slides:
        encoded = base64.b64encode(svg_path.read_bytes()).decode()
        sections.append(f'<section><h2>{escape(name)}</h2><img alt="{escape(name)}" src="data:image/svg+xml;base64,{encoded}"></section>')
    return ("<!doctype html><html lang=\"en\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            f"<title>{escape(title)}</title><style>body{{margin:0;background:#14171c;color:#d7dde6;font:14px/1.4 system-ui,sans-serif}}"
            "section{max-width:1600px;margin:32px auto;padding:0 16px}h2{font-weight:500;font-size:14px;letter-spacing:.06em;text-transform:uppercase;opacity:.7}"
            "img{display:block;width:100%;height:auto;background:#fff}@page{size:landscape;margin:0}@media print{section{margin:0;break-after:page}body{background:#fff}h2{display:none}}</style>"
            f"<body>{''.join(sections)}</body></html>")


def write_preview(svg_path: Path, png_path: Path, viewport: dict[str, Any]) -> None:
    """Rasterize a review copy; cairosvg is an optional maintainer dependency, not a product one."""
    import cairosvg  # noqa: PLC0415

    png_path.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(url=str(svg_path), write_to=str(png_path),
                     output_width=int(viewport["inlineSize"]), output_height=int(viewport["blockSize"]))


def materialize(manifest_path: Path, *, check: bool, previews: bool = False) -> int:
    example = manifest_path.parent.resolve()
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    store = Path(tempfile.mkdtemp(prefix="chrona-store-"))
    scratch = Path(tempfile.mkdtemp(prefix="chrona-render-")) if check else example
    failures = []
    rendered: list[tuple[str, Path]] = []
    try:
        for slide in manifest["slides"]:
            output = scratch / slide["output"]
            output.parent.mkdir(parents=True, exist_ok=True)
            context_payload = render_slide(store, example, manifest, slide, output)
            context_path = scratch / "contexts" / f"{Path(slide['view']).stem}.yaml"
            context_path.parent.mkdir(parents=True, exist_ok=True)
            context_path.write_bytes(context_payload)
            rendered.append((Path(slide["view"]).stem, output))
            if previews and slide.get("preview") and not check:
                viewport = dict(DEFAULT_VIEWPORT, **(slide.get("viewport") or manifest.get("viewport") or {}))
                write_preview(output, example / slide["preview"], viewport)
            if check:
                for produced, expected in ((output, example / slide["output"]), (context_path, example / "contexts" / context_path.name)):
                    if not expected.is_file() or expected.read_bytes() != produced.read_bytes():
                        failures.append(str(expected.relative_to(example)))
        if manifest.get("gallery"):
            gallery = scratch / manifest["gallery"]
            gallery.write_text(gallery_html(manifest.get("title", example.name), rendered), encoding="utf-8")
            if check:
                expected = example / manifest["gallery"]
                if not expected.is_file() or expected.read_bytes() != gallery.read_bytes():
                    failures.append(manifest["gallery"])
    finally:
        shutil.rmtree(store, ignore_errors=True)
        if check:
            shutil.rmtree(scratch, ignore_errors=True)
    if failures:
        print("stale or missing derived artifacts:\n  " + "\n  ".join(failures))
        return 1
    print(f"materialized {len(rendered)} slide(s) for {example.name}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--check", action="store_true", help="verify checked-in outputs instead of writing them")
    parser.add_argument("--previews", action="store_true", help="also rasterize preview.png files (requires cairosvg)")
    arguments = parser.parse_args()
    raise SystemExit(materialize(arguments.manifest, check=arguments.check, previews=arguments.previews))
