"""Independent acceptance tests for the finite shared-deck Context composer."""
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from chrona.usecases.deck_context import load_deck_manifest, select_deck_context
from chrona.usecases.failure_report import StableFailure


ROOT = Path(__file__).resolve().parents[4]
CONTEXT_PATH = ROOT / "tests/fixtures/aster-ssd/contexts/01-overview.yaml"


def _body():
    return yaml.safe_load(CONTEXT_PATH.read_bytes())["body"]


def _manifest(tmp_path: Path, *, body=None, slides=None, fallback=None, deck_id="shared-deck"):
    document = {
        "version": "chrona/example-materializer/v0.1",
        "id": deck_id,
        "role": "regression-corpus",
        "contextDefaults": deepcopy(_body() if body is None else body),
        "slides": slides if slides is not None else [
            {"id": "overview", "contextOverrides": {"id": "overview-context"},
             "evidence": "test", "expectedSvg": "generated/overview.svg"},
        ],
    }
    if fallback is not None:
        document["context"] = fallback
    path = tmp_path / f"{deck_id}.yaml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return path


def _select(path: Path, slide_id: str):
    return select_deck_context(path, load_deck_manifest(path), slide_id)


def _slide(slide_id: str, context_id: str):
    return {"id": slide_id, "contextOverrides": {"id": context_id},
            "evidence": f"{slide_id}.md", "expectedSvg": f"generated/{slide_id}.svg"}


def test_one_shared_theme_edit_reaches_eleven_slides_without_cross_deck_effect(tmp_path):
    body = _body()
    slides = [_slide(f"slide-{index}", f"context-{index}") for index in range(11)]
    deck = _manifest(tmp_path, body=body, slides=slides, deck_id="eleven-slide-deck")
    other = _manifest(tmp_path, body=body, slides=[_slide("only", "other-context")],
                      deck_id="unrelated-deck")

    before_other = _select(other, "only")
    edited = yaml.safe_load(deck.read_bytes())
    edited["contextDefaults"]["theme"]["address"] = "themes/onboarding-variation.yaml"
    deck.write_text(yaml.safe_dump(edited, sort_keys=False), encoding="utf-8")
    completed = [_select(deck, slide["id"]) for slide in slides]

    assert [item.document["id"] for item in completed] == [f"context-{index}" for index in range(11)]
    assert all(item.body["theme"]["address"] == "themes/onboarding-variation.yaml" for item in completed)
    assert before_other.body["theme"] == _select(other, "only").body["theme"]
    assert before_other.body["theme"]["address"] == "themes/executive-light.yaml"


def test_finite_boundaries_merge_body_and_maps_but_replace_references_and_arrays(tmp_path):
    body = _body()
    catalog = {"id": "catalog-a", "kind": "icon-catalog",
               "store": {"provider": "local", "identity": "aster-ssd-example"},
               "address": "catalogs/a.yaml", "revision": {"token": "example-v1"}}
    second_catalog = {**catalog, "id": "catalog-b", "address": "catalogs/b.yaml"}
    replacement_catalog = {**catalog, "id": "replacement", "address": "catalogs/replacement.yaml"}
    body["inputs"]["iconCatalogs"] = [catalog, second_catalog]
    body["forecast"] = True
    project = deepcopy(body["project"])
    project["id"] = "replacement-project"
    font_metrics = deepcopy(body["environment"]["fontMetrics"])
    font_metrics["assets"] = font_metrics["assets"][:1]
    override = {
        "id": "composed",
        "body": {
            "project": project,
            "forecast": None,
            "inputs": {"iconCatalogs": [replacement_catalog], "detailProfile": None},
            "environment": {
                "locale": "ja-JP",
                "viewport": {"inlineSize": 1200, "blockSize": 700},
                "fontMetrics": font_metrics,
            },
        },
    }
    path = _manifest(tmp_path, body=body, slides=[{**_slide("overview", "composed"),
                                                    "contextOverrides": override}])

    selected = _select(path, "overview")

    assert selected.body["project"] == project  # a reference is atomic, not field-merged
    assert "forecast" not in selected.body
    assert "detailProfile" not in selected.body["inputs"]
    assert selected.body["inputs"]["actual"] == body["inputs"]["actual"]
    assert selected.body["inputs"]["iconCatalogs"] == [replacement_catalog]  # arrays replace, never extend
    assert selected.body["environment"]["locale"] == "ja-JP"
    assert selected.body["environment"]["viewport"] == {"inlineSize": 1200, "blockSize": 700}
    assert selected.body["environment"]["fontMetrics"] == font_metrics  # whole member replacement
    assert len(selected.body["environment"]["fontMetrics"]["assets"]) == 1


def test_null_removes_optional_override_and_required_removal_fails_completion(tmp_path):
    body = _body()
    body["forecast"] = None
    body["inputs"]["snapshot"] = None
    path = _manifest(tmp_path, body=body, slides=[{
        **_slide("null-default", "null-default-context"),
    }, {
        **_slide("optional", "optional-context"),
        "contextOverrides": {"id": "optional-context", "body": {"forecast": None}},
    }, {
        **_slide("required", "required-context"),
        "contextOverrides": {"id": "required-context", "body": {"view": None}},
    }])
    manifest = load_deck_manifest(path)

    null_default = select_deck_context(path, manifest, "null-default")
    assert "forecast" not in null_default.body
    assert "snapshot" not in null_default.body["inputs"]
    optional = select_deck_context(path, manifest, "optional")
    assert "forecast" not in optional.body
    with pytest.raises(StableFailure) as caught:
        select_deck_context(path, manifest, "required")
    assert caught.value.code.startswith("E_RESOURCE_SCHEMA")
    assert "view" in caught.value.message
    assert caught.value.source_ref == "/slides/2/contextOverrides/body"


def test_explicit_slide_and_manifest_fallback_bypass_defaults_and_keep_exact_bytes(tmp_path):
    explicit_path = tmp_path / "contexts/explicit.yaml"
    fallback_path = tmp_path / "contexts/fallback.yaml"
    explicit_path.parent.mkdir()
    source = yaml.safe_load(CONTEXT_PATH.read_bytes())
    explicit_bytes = b"# explicit source bytes\n" + yaml.safe_dump(source, sort_keys=False).encode()
    fallback_bytes = b"# fallback source bytes\n" + yaml.safe_dump(source, sort_keys=False).encode()
    explicit_path.write_bytes(explicit_bytes)
    fallback_path.write_bytes(fallback_bytes)
    slides = [
        {"id": "explicit", "context": "contexts/explicit.yaml", "evidence": "a",
         "expectedSvg": "generated/a.svg"},
        {"id": "fallback", "evidence": "b", "expectedSvg": "generated/b.svg"},
    ]
    path = _manifest(tmp_path, body={"forecast": True}, slides=slides,
                     fallback="contexts/fallback.yaml")

    explicit = _select(path, "explicit")
    fallback = _select(path, "fallback")

    assert explicit.source_mode == fallback.source_mode == "explicit"
    assert explicit.payload == explicit_bytes and explicit.source_path == explicit_path.resolve()
    assert fallback.payload == fallback_bytes and fallback.source_path == fallback_path.resolve()


def test_font_set_is_validated_expanded_but_composed_payload_preserves_authored_bytes(tmp_path):
    body = _body()
    body["environment"]["fontMetrics"] = {
        "algorithm": "declared-metrics-v3", "missingFont": "diagnose",
        "fontSet": "chrona.noto-sans",
    }
    path = _manifest(tmp_path, body=body)

    selected = _select(path, "overview")
    payload_document = yaml.safe_load(selected.payload)

    assert payload_document["body"]["environment"]["fontMetrics"] == body["environment"]["fontMetrics"]
    assert "assets" not in payload_document["body"]["environment"]["fontMetrics"]
