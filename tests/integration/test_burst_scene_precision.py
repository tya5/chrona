"""Declared Scene precision reaches completed burst as-of geometry (#1818)."""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from hashlib import sha256
from html import escape
from pathlib import Path
import re

import pytest

import yaml

from chrona.presentation.model.closure import resolve_draft_render, resolve_render_context
from chrona.presentation.scene.serialization import scene_document, validate_scene_document
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.storage.snapshot_paths import snapshot_directory
from chrona.usecases.render_review import RenderRequest, render_review
from tests.support import synthetic_review as sr


ACTUAL = {
    "version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
    "body": {"asOf": "2026-02-20", "observations": []},
}


def _parts(fit: str) -> dict[str, dict]:
    parts = sr.bundle("executive-light")
    theme = parts["theme"]["body"]
    theme["values"]["precision-test-chip"] = {
        "type": "chipShape",
        "value": {"kind": "burst", "points": 7, "innerRatio": .7, "fit": fit},
    }
    theme["values"]["chip-padding"]["value"] = .8
    theme["roles"]["as-of-label-chip"] = {
        "backgroundTreatment": "fill", "chipPadding": "chip-padding",
        "chipShape": "precision-test-chip",
    }
    theme["colorBindings"]["as-of-label-chip.fill"] = "surfaceRaised"
    marker = next(item for item in parts["view"]["body"]["markers"] if item["kind"] == "asOf")
    marker.update(placement="below-plot", label="TODAY!", date={"form": "day-month-year"})
    return parts


def _inside(point: tuple[float, float], polygon: tuple[tuple[float, float], ...]) -> bool:
    x, y = point
    inside = False
    for (ax, ay), (bx, by) in zip(polygon, (*polygon[1:], polygon[0])):
        if (ay > y) != (by > y):
            crossing = ax + (y - ay) * (bx - ax) / (by - ay)
            if x < crossing:
                inside = not inside
    return inside


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _render(tmp_path: Path, fit: str, precision: int):
    parts = _parts(fit)
    paths = {kind: sr._write(tmp_path / f"{kind}.yaml", value) for kind, value in parts.items()}
    draft = resolve_draft_render(
        project_path=sr._write(tmp_path / "project.yaml", sr.project({
            "alpha": sr.span("alpha", date(2026, 2, 2), 35, title="Alpha synthetic task"),
            "beta": sr.span("beta", date(2026, 2, 5), 28, owner="b", title="Beta synthetic task"),
        })),
        view_path=paths["view"], theme_path=paths["theme"], scheme_path=paths["scheme"],
        layout_path=paths["layout"], actual_path=sr._write(tmp_path / "actual.yaml", ACTUAL),
        viewport=(1200, 760),
    )
    # Pin a real Context resource whose serialized environment declares the
    # precision being exercised; the render then follows the immutable path.
    values = {"project": sr.project({
        "alpha": sr.span("alpha", date(2026, 2, 2), 35, title="Alpha synthetic task"),
        "beta": sr.span("beta", date(2026, 2, 5), 28, owner="b", title="Beta synthetic task"),
    }), **parts, "actual": ACTUAL}
    root = tmp_path / "snapshot"
    revision = "precision-r1"
    directory = snapshot_directory(root, revision)
    directory.mkdir(parents=True)

    def store(name, value):
        kind = {"scheme": "color-scheme", "layout": "layout-profile", "context": "render-context",
                "actual": "actual-set"}.get(name, name)
        identifier = value["project"]["id"] if kind == "project" else value["id"]
        payload = yaml.safe_dump(value, sort_keys=True).encode("utf-8")
        (directory / f"{name}.yaml").write_bytes(payload)
        return {"id": identifier, "kind": kind, "address": f"{name}.yaml",
                "store": {"provider": "local", "identity": "precision-test"},
                "revision": {"token": revision},
                "contentIdentity": "sha256:" + sha256(payload).hexdigest()}

    refs = {name: store(name, value) for name, value in values.items()}
    environment = draft.closure.context.environment
    context = {
        "version": "chrona/render-context/v0.17", "kind": "render-context", "id": "precision-context",
        "body": {
            "project": refs["project"], "view": refs["view"], "theme": refs["theme"],
            "colorScheme": refs["scheme"], "layout": refs["layout"],
            "inputs": {"actual": refs["actual"]},
            "environment": {"viewport": {"inlineSize": 1200, "blockSize": 760},
                            "locale": environment.locale, "fontMetrics": _plain(environment.font_metrics),
                            "scenePrecision": precision},
            "target": {"kind": "svg", "capabilities": [],
                       "visualProfile": draft.closure.context.target.visual_profile},
        },
    }
    context_ref = store("context", context)
    closure = resolve_render_context(context_ref, LocalSnapshotReader(
        root, "precision-test", require_content_identity=False))
    return render_review(RenderRequest(
        closure=closure, snapshot_root=root, asset_root=root,
        scheduler=ReferenceScheduler(), renderer=V05SvgRenderer(),
    ))


@pytest.mark.parametrize("fit", ["circle", "ellipse"])
@pytest.mark.parametrize("precision", [0, 3, 6])
def test_declared_scene_precision_reaches_completed_asof_burst_and_keeps_text_ground(
        tmp_path, fit, precision):
    rendered = _render(tmp_path, fit, precision)
    chip = next(item for item in rendered.surface.primitives if item.scene_id == "chip:as-of-label")
    label = next(item for item in rendered.surface.primitives if item.scene_id == "as-of-label")
    assert chip.kind == "Symbol" and chip.symbol is not None
    assert label.kind == "Text" and label.text.endswith("20 Feb 2026")

    document = scene_document(rendered.scene)
    validate_scene_document(document)
    quantum = Decimal(1).scaleb(-precision)
    vertices = tuple(command.points[0] for command in chip.symbol.outline[:-1])
    assert len(vertices) == 14
    for x, y in vertices:
        assert Decimal(str(x)) == Decimal(str(x)).quantize(quantum)
        assert Decimal(str(y)) == Decimal(str(y)).quantize(quantum)
        bx, by, bw, bh = chip.bounds
        assert bx <= x <= bx + bw
        assert by <= y <= by + bh

    svg = rendered.artifact.content.decode("utf-8")
    path = re.search(rf'<path\b(?=[^>]*data-scene-id="{re.escape(escape(chip.scene_id, quote=True))}")'
                     r'[^>]*\bd="([^"]+)"', svg)
    assert path is not None
    emitted = tuple((verb, float(x), float(y)) for verb, x, y in re.findall(
        r"([ML])\s*([-+]?(?:\d+\.?\d*|\.\d+))\s+([-+]?(?:\d+\.?\d*|\.\d+))",
        path.group(1)))
    expected = tuple(("M" if command.kind == "move" else "L", *command.points[0])
                     for command in chip.symbol.outline)
    assert len(emitted) == len(expected)
    for actual, wanted in zip(emitted, expected):
        assert actual[0] == wanted[0]
        assert actual[1:] == pytest.approx(tuple(round(value, 3) for value in wanted[1:]), abs=5e-10)

    # The completed fill must still contain the chip's padded text ground;
    # this checks the selected circle/ellipse contour, not just Scene validity.
    tx, ty, tw, th = label.text_layout.bounds
    font_size = label.text_layout.font_size
    pad_inline, pad_block = .8 * font_size, .4 * font_size
    padded_corners = ((tx - pad_inline, ty - pad_block), (tx + tw + pad_inline, ty - pad_block),
                      (tx + tw + pad_inline, ty + th + pad_block),
                      (tx - pad_inline, ty + th + pad_block))
    assert all(_inside(corner, vertices) for corner in padded_corners)

    # Paint bounds cover the quantized contour as well as the label rectangle.
    px, py, pw, ph = chip.bounds
    assert all(px <= x <= px + pw and py <= y <= py + ph for x, y in vertices)
    lx, ly, lw, lh = label.bounds
    assert px <= lx and py <= ly and px + pw >= lx + lw and py + ph >= ly + lh
