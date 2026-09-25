from __future__ import annotations

import json
from pathlib import Path

from tools.presentation_font_identity import evaluate_committed_scenes, render_markdown, report_document


def _context(path: Path) -> Path:
    path.write_text(
        """
version: chrona/render-context/v0.16
kind: render-context
id: demo-context
body:
  environment:
    fontMetrics:
      assets:
        - family: Demo Sans
          weight: 400
          font: {contentIdentity: sha256:regular}
        - family: Demo Sans
          weight: 700
          font: {contentIdentity: sha256:bold}
""".lstrip(),
        encoding="utf-8",
    )
    return path


def _scene(path: Path, *, identity: str) -> Path:
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "provenance": {"resources": [{"kind": "render-context", "id": "demo-context"}]},
        "surfaces": [{"primitives": [{
            "id": "title", "kind": "Text",
            "textLayout": {"family": "Demo Sans, sans-serif", "weight": 700, "assetIdentity": identity},
        }]}],
    }), encoding="utf-8")
    return path


def test_completed_text_identity_is_checked_against_the_context_face_catalog(tmp_path):
    scene = _scene(tmp_path / "examples/demo/generated/slide.scene.json", identity="sha256:bold")
    records = evaluate_committed_scenes((scene,), root=tmp_path,
                                        contexts={scene.resolve(): _context(tmp_path / "context.yaml")})

    assert records[0]["code"] == "I_FONT_IDENTITY_EXACT"
    report = report_document(records)
    assert report["weight700PlacementCount"] == 1
    assert report["weight700RegularFaceCount"] == 0
    assert report["errorCount"] == 0
    assert "Demo Sans, sans-serif" in render_markdown(report)


def test_completed_weight_700_cannot_claim_the_regular_face_identity(tmp_path):
    scene = _scene(tmp_path / "examples/demo/generated/slide.scene.json", identity="sha256:regular")
    records = evaluate_committed_scenes((scene,), root=tmp_path,
                                        contexts={scene.resolve(): _context(tmp_path / "context.yaml")})

    assert records[0]["code"] == "E_FONT_IDENTITY_WEIGHT"
    assert records[0]["severity"] == "error"
    report = report_document(records)
    assert report["errorCount"] == 1
    assert report["weight700RegularFaceCount"] == 1
