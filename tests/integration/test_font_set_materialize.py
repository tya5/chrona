"""Named packaged font sets remain usable through public materialization (#1345)."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil

import pytest
import yaml

from chrona.resources import safe_load
from chrona.presentation.scene.serialization import serialize_scene
from chrona.presentation.contracts.font_sets import expand_font_set
from chrona.storage.snapshot_paths import snapshot_directory
from chrona.usecases.materialize import _OverlayBuilder, copy_context_closure, materialize
from tests.support.deck_contexts import write_explicit_context


ROOT = Path(__file__).resolve().parents[2]


def _without_pins(assets: list) -> list:
    result = deepcopy(assets)
    for asset in result:
        for role in ("metrics", "font"):
            if role in asset:
                asset[role].pop("contentIdentity", None)
    return result


@pytest.mark.parametrize(
    ("example_name", "context_address", "slide_id", "font_set", "cjk"),
    [
        ("aster-ssd", "contexts/01-overview.yaml", "overview", "chrona.noto-sans", False),
        ("halcyon-1", "contexts/19-gallery-text-compression.yaml", "gallery-text-compression",
         "chrona.noto-sans+jp", True),
    ],
)
def test_materializer_expands_font_set_without_rewriting_context_or_scene_provenance(
    tmp_path: Path, example_name: str, context_address: str, slide_id: str, font_set: str, cjk: bool,
) -> None:
    if cjk:
        pytest.importorskip("chrona_fonts_noto_cjk", reason="requires the optional local CJK font provider")

    example = tmp_path / example_name
    shutil.copytree(ROOT / "examples" / example_name, example)
    manifest_path = example / "manifest.yaml"
    manifest = safe_load(manifest_path.read_bytes())
    manifest["slides"] = [slide for slide in manifest["slides"] if slide["id"] == slide_id]
    assert len(manifest["slides"]) == 1
    # The committed Scene pins the old Context bytes. This isolated comparison
    # uses the returned Scene directly so the one disclosed provenance delta
    # can be examined without rewriting any expected corpus artifact.
    manifest["slides"][0].pop("expectedScene", None)
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

    context_path = write_explicit_context(example, slide_id, context_address)
    explicit_bytes = context_path.read_bytes()
    explicit_context = safe_load(explicit_bytes)
    explicit_assets = deepcopy(explicit_context["body"]["environment"]["fontMetrics"]["assets"])

    # Verify explicit assets remain accepted and materializable before replacing them.
    explicit_output = tmp_path / f"{example_name}-explicit"
    explicit_result = materialize(manifest_path, slide_id, explicit_output, write=False)
    assert explicit_result.output.is_file()

    metrics = explicit_context["body"]["environment"]["fontMetrics"]
    del metrics["assets"]
    metrics["fontSet"] = font_set
    named_bytes = yaml.safe_dump(explicit_context, allow_unicode=True, sort_keys=False).encode()
    context_path.write_bytes(named_bytes)
    named_identity = "sha256:" + sha256(named_bytes).hexdigest()

    # Exercise the same public closure-copy ingress independently so staged bytes
    # and every expanded packaged metrics asset can be inspected directly.
    snapshot = tmp_path / f"{example_name}-snapshot"
    snapshot.mkdir()
    overlay_builder = _OverlayBuilder(tmp_path / f"{example_name}-overlay")
    reference, revision = copy_context_closure(
        example, context_path, snapshot, overlay_builder=overlay_builder,
    )
    assert reference["contentIdentity"] == named_identity
    staged_context = snapshot_directory(snapshot, revision) / context_address
    assert staged_context.read_bytes() == named_bytes
    assert "assets" not in safe_load(staged_context.read_bytes())["body"]["environment"]["fontMetrics"]

    expanded = expand_font_set(safe_load(named_bytes))
    expanded_assets = expanded["body"]["environment"]["fontMetrics"]["assets"]
    # Authored lists carry no pins (#1567); compare the expanded set without its packaged identities.
    assert _without_pins(expanded_assets) == _without_pins(explicit_assets)
    overlay = overlay_builder.finish()
    for asset in expanded_assets:
        record = asset["metrics"]
        staged_metric = overlay.resolve_asset(record["locator"], record["contentIdentity"])
        assert "sha256:" + sha256(staged_metric.read_bytes()).hexdigest() == record["contentIdentity"]

    named_output = tmp_path / f"{example_name}-font-set"
    named_result = materialize(manifest_path, slide_id, named_output, write=False)
    assert named_result.output.is_file()
    assert named_result.closure_reference["contentIdentity"] == named_identity
    assert context_path.read_bytes() == named_bytes

    assert named_result.output.read_bytes() == explicit_result.output.read_bytes()
    explicit_scene = json.loads(serialize_scene(explicit_result.rendered.scene))
    named_scene = json.loads(serialize_scene(named_result.rendered.scene))
    explicit_resources = explicit_scene["provenance"]["resources"]
    named_resources = named_scene["provenance"]["resources"]
    explicit_context_resource = next(item for item in explicit_resources if item["kind"] == "render-context")
    named_context_resource = next(item for item in named_resources if item["kind"] == "render-context")
    assert explicit_context_resource["contentIdentity"] == "sha256:" + sha256(explicit_bytes).hexdigest()
    assert named_context_resource["contentIdentity"] == named_identity
    assert explicit_context_resource["contentIdentity"] != named_context_resource["contentIdentity"]

    explicit_context_resource["contentIdentity"] = named_identity
    assert named_scene == explicit_scene
