from __future__ import annotations

import json
from pathlib import Path

from chrona.resources import safe_load
from chrona.usecases.deck_context import SelectedDeckContext
from tools.presentation_font_identity import evaluate_committed_scenes, render_markdown, report_document


def _selected_context(path: Path) -> SelectedDeckContext:
    payload = path.read_bytes()
    return SelectedDeckContext(safe_load(payload), payload, path.name, path.resolve(),
                               path.parent.parent / "manifest.yaml", "slide", "explicit", {})


def _context(path: Path) -> SelectedDeckContext:
    path.write_text(
        """
version: chrona/render-context/v0.17
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
    return _selected_context(path)


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


def _faces_context(path: Path, regular: str | None, bold: str | None) -> SelectedDeckContext:
    def face(weight: int, identity: str | None) -> str:
        font = "{}" if identity is None else "{contentIdentity: %s}" % identity
        return f"        - family: Demo Sans\n          weight: {weight}\n          font: {font}\n"

    path.write_text(
        "version: chrona/render-context/v0.17\nkind: render-context\nid: demo-context\n"
        "body:\n  environment:\n    fontMetrics:\n      assets:\n"
        + face(400, regular) + face(700, bold),
        encoding="utf-8",
    )
    return _selected_context(path)


def _run(tmp_path: Path, regular: str | None, bold: str | None, identity: str):
    scene = _scene(tmp_path / "examples/demo/generated/slide.scene.json", identity=identity)
    context = _faces_context(tmp_path / "context.yaml", regular, bold)
    return evaluate_committed_scenes((scene,), root=tmp_path, contexts={scene.resolve(): context})


def test_all_pinned_faces_keep_exact_verification(tmp_path):
    records = _run(tmp_path, "sha256:regular", "sha256:bold", "sha256:bold")

    assert records[0]["code"] == "I_FONT_IDENTITY_EXACT"
    assert records[0]["expectedIdentity"] == "sha256:bold"
    assert report_document(records)["errorCount"] == 0


def test_unpinned_faces_are_reported_without_error_or_claimed_identity(tmp_path):
    records = _run(tmp_path, None, None, "sha256:anything")

    assert records[0]["code"] == "I_FONT_IDENTITY_UNPINNED"
    assert records[0]["severity"] == "info"
    assert records[0]["expectedIdentity"] is None
    report = report_document(records)
    assert report["errorCount"] == 0
    assert report["rows"][0]["expectedIdentity"] is None
    assert render_markdown(report) == render_markdown(report_document(records))


def test_mixed_pinned_and_unpinned_faces(tmp_path):
    pinned = _run(tmp_path / "a", "sha256:regular", None, "sha256:regular")
    assert pinned == _run(tmp_path / "b", "sha256:regular", None, "sha256:regular")
    scene = _scene(tmp_path / "c/examples/demo/generated/slide.scene.json", identity="sha256:x")
    context = _faces_context(tmp_path / "c/context.yaml", "sha256:regular", None)
    records = evaluate_committed_scenes((scene,), root=tmp_path / "c", contexts={scene.resolve(): context})
    assert records[0]["code"] == "I_FONT_IDENTITY_UNPINNED"
    assert report_document(records)["errorCount"] == 0


def test_wrong_pin_is_still_an_error_when_another_face_is_unpinned(tmp_path):
    records = _run(tmp_path, None, "sha256:bold", "sha256:other")

    assert records[0]["code"] == "E_FONT_IDENTITY_ASSET"
    assert records[0]["severity"] == "error"
    assert report_document(records)["errorCount"] == 1


def test_weight_700_pin_rules_with_unpinned_and_pinned_bold(tmp_path):
    records = _run(tmp_path, "sha256:regular", None, "sha256:regular")

    assert records[0]["code"] == "I_FONT_IDENTITY_UNPINNED"
    records = _run(tmp_path / "d", "sha256:regular", "sha256:bold", "sha256:regular")
    assert records[0]["code"] == "E_FONT_IDENTITY_WEIGHT"
