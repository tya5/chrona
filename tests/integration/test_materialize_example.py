from hashlib import sha256
from importlib.util import find_spec
import json
from pathlib import Path
import re
import shutil

import pytest
import yaml
from PIL import Image

from chrona.presentation.model.closure import ClosureError, resolve_render_context
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.storage.revision_store import ProjectSnapshot
from chrona.storage.snapshot_paths import snapshot_directory
from chrona.storage.snapshots import LocalBaselineRegistry, capture_baseline_v02
from chrona.usecases.materialize import copy_context_closure
from chrona.usecases.render_review import RenderRequest, render_review
from tools.materialize_example import _copy_context_closure, materialize


ROOT = Path(__file__).resolve().parents[2]


def _require_cjk_provider() -> None:
    pytest.importorskip("chrona_fonts_noto_cjk", reason="requires the optional local CJK font provider")


class _FixedProjectStore:
    def __init__(self, snapshot: ProjectSnapshot):
        self.snapshot = snapshot

    def read(self) -> ProjectSnapshot:
        return self.snapshot


def test_declared_examples_reproduce_by_public_cli(tmp_path):
    """Every slide of every declared corpus manifest reproduces its committed evidence."""
    manifests = [manifest for manifest in sorted(ROOT.glob("examples/*/manifest.yaml"))
                 if manifest.parent.name != "controller-z-ja" or find_spec("chrona_fonts_noto_cjk") is not None]
    assert manifests, "no corpus manifests found"
    for manifest in manifests:
        for slide in yaml.safe_load(manifest.read_text(encoding="utf-8"))["slides"]:
            materialize(manifest, slide["id"], tmp_path / manifest.parent.name / slide["id"], write=False)


def test_controller_executive_public_evidence_exercises_inside_and_fallback_labels(tmp_path):
    materialize(ROOT / "examples/controller-z/manifest.yaml", "executive", tmp_path / "controller", write=False)
    artifact = (tmp_path / "controller/review.svg").read_text(encoding="utf-8")
    assert 'data-scene-id="member-label:firmware:firmware"' in artifact
    assert 'data-scene-id="member-label:dvt:dvt"' in artifact and 'opacity="1" fill="#000000">DVT Qualification' in artifact
    assert 'data-scene-id="member-label:evb-arrival:evb-arrival"' in artifact and 'opacity="1" fill="#172033">EVB Arrival' in artifact


def test_controller_annotation_evidence_realizes_each_purpose_through_layout_completed_primitives(tmp_path):
    example = ROOT / "examples/controller-z"
    materialize(example / "manifest.yaml", "annotations", tmp_path / "annotations", write=False)
    artifact = (tmp_path / "annotations/review.svg").read_text(encoding="utf-8")
    for identifier in ("architecture-callout", "evb-highlight", "performance-note", "firmware-slip", "bringup-risk"):
        assert f'data-scene-id="annotation-box:{identifier}"' in artifact
        assert f'data-scene-id="annotation-text:{identifier}"' in artifact
    for identifier in ("architecture-callout", "performance-note", "firmware-slip", "bringup-risk"):
        assert f'data-scene-id="annotation-leader:{identifier}"' in artifact
    assert 'data-scene-id="annotation-leader:evb-highlight"' not in artifact
    leader = re.search(r'data-scene-id="annotation-leader:bringup-risk"[^>]* d="([^"]+)"', artifact)
    assert leader is not None and leader.group(1).count("L") >= 5
    assert re.search(r'data-scene-id="annotation-leader:bringup-risk"[^>]*marker-end="url\(#marker-[^"]+\)"', artifact)
    scene_source = (ROOT / "src/chrona/presentation/scene/v05_builder.py").read_text(encoding="utf-8")
    adapter_source = (ROOT / "src/chrona/presentation/renderers/v05_svg.py").read_text(encoding="utf-8")
    assert "route_annotation_leader" not in scene_source
    assert "route_annotation_leader" not in adapter_source


def test_controller_japanese_public_evidence_uses_the_explicit_cjk_provider(tmp_path):
    _require_cjk_provider()
    materialize(ROOT / "examples/controller-z-ja/manifest.yaml", "executive", tmp_path / "controller-z-ja", write=False)
    artifact = (tmp_path / "controller-z-ja/review.svg").read_text(encoding="utf-8")
    assert "コントローラZ — シリコン立ち上げから量産まで" in artifact
    assert "量産検証（PVT）および工場工程バリデーション" in artifact


def test_controller_elevated_public_evidence_uses_only_portable_completed_treatments(tmp_path):
    materialize(ROOT / "examples/controller-z/manifest.yaml", "elevated", tmp_path / "elevated", write=False)
    artifact = (tmp_path / "elevated/review.svg").read_text(encoding="utf-8")
    assert '<linearGradient id="gradient-' in artifact and '<feDropShadow ' in artifact
    assert 'fill="url(#gradient-' in artifact and 'filter="url(#shadow-' in artifact
    assert 'data-source-ref="firmware"' in artifact and '>FW Feature Complete</text>' in artifact


def test_halcyon_programme_board_derives_owner_scale_paint_and_legend(tmp_path):
    materialize(ROOT / "examples/halcyon-1/manifest.yaml", "programme-board", tmp_path / "board", write=False)
    svg = (tmp_path / "board/review.svg").read_text(encoding="utf-8")
    assert 'data-scene-id="planned:payload-tvac:payload-tvac"' in svg
    assert 'data-scene-id="legend-swatch:scale:owner:payload"' in svg
    assert 'data-scene-id="legend:scale:owner:payload"' in svg
    assert 'data-scene-id="progress-fill:planned:campaign:campaign"' in svg
    assert 'data-purpose="progress-fill"' in svg


def test_halcyon_overlay_briefing_materializes_guide_and_barrier_anchored_slots(tmp_path):
    materialize(ROOT / "examples/halcyon-1/manifest.yaml", "overlay-briefing", tmp_path / "overlay", write=False)
    scene = json.loads((tmp_path / "overlay/review.scene.json").read_text(encoding="utf-8"))
    slots = {item["source"]: item["bounds"] for item in scene["surfaces"][0]["slots"]}
    assert slots["title"]["block"] == slots["table"]["block"] == slots["timeline-axis"]["block"] == 225.0
    assert slots["table"]["inline"] == 484.0
    assert slots["timeline-axis"]["inline"] == slots["table"]["inline"] + slots["table"]["inlineSize"] + 24.0
    assert slots["timeline"]["block"] == slots["timeline-axis"]["block"] + slots["timeline-axis"]["blockSize"]
    assert slots["timeline"]["blockSize"] >= 900.0


def test_orion_gates_measures_the_colour_scale_legend_before_layout(tmp_path):
    """Scale legend rows are part of the legend slot's measured size, so they stay on the canvas."""
    materialize(ROOT / "examples/orion-asic/manifest.yaml", "gates", tmp_path / "gates", write=False)
    svg = (tmp_path / "gates/review.svg").read_text(encoding="utf-8")
    context = yaml.safe_load((ROOT / "examples/orion-asic/contexts/gates.yaml").read_text(encoding="utf-8"))
    block = float(context["body"]["environment"]["viewport"]["blockSize"])
    baselines = [float(match) for match in re.findall(r'data-purpose="legend-label"[^>]* y="([0-9.]+)"', svg)]
    assert len(baselines) == 5 and max(baselines) < block
    assert 'data-scene-id="legend:scale:revision:B0"' in svg
    assert 'data-purpose="progress-fill"' in svg
    scene = json.loads((tmp_path / "gates/review.scene.json").read_text(encoding="utf-8"))
    assert "W_LAYOUT_AXIS_LABEL_THINNED:axis-label:3:0:label-does-not-fit" in scene["diagnostics"]
    assert "W_LAYOUT_AXIS_DENSITY:axis-tier:3:stride=2:phase=1" in scene["diagnostics"]


def test_replan_baseline_records_the_nonfitting_partial_quarter_label(tmp_path):
    materialize(ROOT / "examples/halcyon-1/manifest.yaml", "replan-baseline", tmp_path / "replan", write=False)
    scene = json.loads((tmp_path / "replan/review.scene.json").read_text(encoding="utf-8"))
    assert "W_LAYOUT_AXIS_LABEL_THINNED:axis-label:2:0:label-does-not-fit" in scene["diagnostics"]
    assert "W_LAYOUT_AXIS_DENSITY:axis-tier:2:stride=2:phase=1" in scene["diagnostics"]


def test_materializer_detects_changed_expected_svg(tmp_path):
    copied_example = tmp_path / "controller-z"
    shutil.copytree(ROOT / "examples/controller-z", copied_example)
    manifest = copied_example / "manifest.yaml"
    expected = copied_example / "generated/executive.svg"
    original = expected.read_bytes()
    try:
        expected.write_bytes(original + b"changed")
        with pytest.raises(ValueError, match="E_MATERIALIZER_MISMATCH"):
            materialize(manifest, "executive", tmp_path / "controller", write=False)
    finally:
        expected.write_bytes(original)


def test_materializer_requires_declared_regression_role_and_slide_evidence(tmp_path):
    copied_example = tmp_path / "controller-z"
    shutil.copytree(ROOT / "examples/controller-z", copied_example)
    manifest_path = copied_example / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("role")
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False))
    with pytest.raises(ValueError, match="E_MATERIALIZER_MANIFEST"):
        materialize(manifest_path, "executive", tmp_path / "missing-role", write=False)
    manifest["role"] = "regression-corpus"
    manifest["slides"][0].pop("evidence")
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False))
    with pytest.raises(ValueError, match="E_MATERIALIZER_SLIDE"):
        materialize(manifest_path, "executive", tmp_path / "missing-evidence", write=False)


def test_materializer_rewrites_provider_font_locators_to_a_self_contained_snapshot(tmp_path):
    example = ROOT / "examples/aster-ssd"
    context_path = example / "contexts/01-overview.yaml"
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()

    reference, revision = _copy_context_closure(example, context_path, snapshot)

    copied = snapshot_directory(snapshot, revision) / "contexts/01-overview.yaml"
    copied_context = yaml.safe_load(copied.read_text(encoding="utf-8"))
    source_context = yaml.safe_load(context_path.read_text(encoding="utf-8"))
    assert reference["contentIdentity"] == "sha256:" + sha256(copied.read_bytes()).hexdigest()
    assert copied_context["body"]["environment"]["fontMetrics"]["assets"][0]["metrics"]["locator"]["provider"] == "context"
    assert source_context["body"]["environment"]["fontMetrics"]["assets"][0]["metrics"]["locator"]["provider"] == "package"


def test_baseline_capture_materializes_a_context_through_its_windows_safe_token(tmp_path):
    example = tmp_path / "controller-z"
    shutil.copytree(ROOT / "examples/controller-z", example)
    project_path = example / "project.yaml"
    project_payload = project_path.read_bytes()
    project = yaml.safe_load(project_payload)
    identity = "controller-z-example"
    project_ref = {
        "id": project["project"]["id"], "kind": "project",
        "store": {"provider": "local", "identity": identity}, "address": "project.yaml",
        "revision": {"token": "example-v1"},
    }
    captured = capture_baseline_v02(
        _FixedProjectStore(ProjectSnapshot("example-v1", "sha256:" + sha256(project_payload).hexdigest(), project)),
        "example-v1", project_ref, "q2", LocalBaselineRegistry(example, identity),
    )
    assert captured.status == "accepted"

    context_path = example / "contexts/executive.yaml"
    context = yaml.safe_load(context_path.read_text(encoding="utf-8"))
    context["body"]["inputs"]["snapshot"] = captured.snapshot_ref
    context_path.write_text(yaml.safe_dump(context, sort_keys=False), encoding="utf-8")

    snapshot = tmp_path / "snapshot"
    reference, revision = copy_context_closure(example, context_path, snapshot)

    token = captured.snapshot_ref["revision"]["token"]
    assert (snapshot_directory(snapshot, token) / "snapshots/q2.yaml").is_file()
    assert (snapshot_directory(snapshot, revision) / "contexts/executive.yaml").is_file()
    closure = resolve_render_context(reference, LocalSnapshotReader(snapshot, identity))
    assert any(resource.kind == "snapshot-project" for resource in closure.resources)


def test_materializer_rejects_an_authored_stale_pin_before_write(tmp_path):
    copied_example = tmp_path / "halcyon"
    shutil.copytree(ROOT / "examples/halcyon-1", copied_example)
    context = copied_example / "contexts/01-mission-brief.yaml"
    value = yaml.safe_load(context.read_text(encoding="utf-8"))
    value["body"]["inputs"]["actual"]["contentIdentity"] = "sha256:" + "0" * 64
    context.write_text(yaml.safe_dump(value, sort_keys=False))
    with pytest.raises(ValueError, match="E_CONTENT_IDENTITY"):
        materialize(copied_example / "manifest.yaml", "mission-brief", tmp_path / "out", write=True)

def test_materializer_uses_each_declared_halcyon_slide_context(tmp_path):
    example = ROOT / "examples/halcyon-1"
    manifest = yaml.safe_load((example / "manifest.yaml").read_text(encoding="utf-8"))
    for index, slide in enumerate(manifest["slides"]):
        relative = slide.get("context", manifest["context"])
        snapshot = tmp_path / str(index)
        snapshot.mkdir()
        reference, revision = _copy_context_closure(example, example / relative, snapshot)
    assert reference["id"] == yaml.safe_load((snapshot_directory(snapshot, revision) / relative).read_text(encoding="utf-8"))["id"]


def test_materializer_copies_only_declared_icon_assets(tmp_path):
    copied = tmp_path / "controller-z"
    shutil.copytree(ROOT / "examples/controller-z", copied)
    context_path = copied / "contexts/executive.yaml"
    context = yaml.safe_load(context_path.read_text(encoding="utf-8"))
    context["body"]["inputs"]["iconCatalogs"] = [{"id": "controller-z-icons", "kind": "icon-catalog", "store": context["body"]["project"]["store"],
                                                         "address": "icons.yaml", "revision": context["body"]["project"]["revision"]}]
    context_path.write_text(yaml.safe_dump(context, sort_keys=False))
    snapshot = tmp_path / "snapshot"; snapshot.mkdir()
    _, revision = _copy_context_closure(copied, context_path, snapshot)
    assert (snapshot_directory(snapshot, revision) / "assets/programme-mark.png").read_bytes() == (copied / "assets/programme-mark.png").read_bytes()
    assert not (snapshot_directory(snapshot, revision) / "assets/risk.svg").exists()


def test_public_icon_evidence_is_bounded_and_decodes_its_purpose_built_raster(tmp_path):
    example = ROOT / "examples/controller-z"
    raster = example / "assets/programme-mark.png"
    assert raster.stat().st_size <= 1024
    with Image.open(raster) as image:
        assert image.size == (24, 24)
        assert image.getbbox() is not None
    materialize(example / "manifest.yaml", "icons", tmp_path / "icons", write=False)
    artifact = (tmp_path / "icons/review.svg").read_bytes()
    assert len(artifact) <= 64 * 1024
    assert b'data:image/png;base64,' in artifact


def test_public_material_icon_evidence_closes_the_packaged_catalog_and_small_text_slots(tmp_path):
    example = ROOT / "examples/controller-z"
    context = yaml.safe_load((example / "contexts/material-icons.yaml").read_text(encoding="utf-8"))
    reference = context["body"]["inputs"]["iconCatalogs"][0]
    assert reference["store"] == {"provider": "package", "identity": "chrona.resources"}
    assert reference["contentIdentity"] == "sha256:c9550b8542dcc586757cee41e4d9ce90a3e12f2b8613056e4fabbc680b271b17"
    materialize(example / "manifest.yaml", "material-icons", tmp_path / "material-icons", write=False)
    artifact = (tmp_path / "material-icons/review.svg").read_text(encoding="utf-8")
    assert artifact == (example / "generated/material-icons.svg").read_text(encoding="utf-8")
    assert artifact.count('data-purpose="label-visual"') == 4
    assert 'data-scene-id="visual:column:Workstream:leading"' in artifact
    assert 'data-scene-id="visual:cell:firmware:Workstream:leading"' in artifact
    assert 'data-asset-identity="sha256:c9550b8542dcc586757cee41e4d9ce90a3e12f2b8613056e4fabbc680b271b17"' in artifact
    assert 'font-size="13"' in artifact and 'font-size="24"' in artifact


def test_successor_view_rejects_removed_icon_bindings(tmp_path):
    copied = tmp_path / "controller-z"; shutil.copytree(ROOT / "examples/controller-z", copied)
    view_path = copied / "views/executive.yaml"; view = yaml.safe_load(view_path.read_text(encoding="utf-8"))
    view["body"]["iconBindings"] = []
    view_path.write_text(yaml.safe_dump(view, sort_keys=False))
    context_path = copied / "contexts/executive.yaml"; context = yaml.safe_load(context_path.read_text(encoding="utf-8"))
    context["body"]["view"]["contentIdentity"] = "sha256:" + sha256(view_path.read_bytes()).hexdigest()
    context_path.write_text(yaml.safe_dump(context, sort_keys=False))
    with pytest.raises(Exception):
        materialize(copied / "manifest.yaml", "executive", tmp_path / "out", write=True)


def test_flight_readiness_public_artifact_exercises_advanced_contracts(tmp_path):
    example = ROOT / "examples/halcyon-1"
    materialize(example / "manifest.yaml", "flight-readiness", tmp_path / "flight-readiness", write=False)
    artifact = (tmp_path / "flight-readiness/review.svg").read_text(encoding="utf-8")
    evidence = yaml.safe_load((tmp_path / "flight-readiness/closure.yaml").read_text(encoding="utf-8"))
    assert evidence["scenarios"][0]["scenarioId"] == "tvac-slip"
    assert '<a href="https://example.test/halcyon-1/reviews/frr"' in artifact
    # Only launch→LEOP is driving; its four current/scenario comparison facets
    # remain visible. Endpoint-critical neighbours must not become a critical chain.
    assert artifact.count('marker-end="url(#marker-') == 4
    for object_id, wbs in (("mission-closeout", "6"), ("frr", "6.1"), ("launch", "6.2"), ("leop", "6.3"), ("first-light", "6.4")):
        assert f'data-scene-id="cell:{object_id}:WBS"' in artifact
        assert f'>{wbs}</text>' in artifact
    assert artifact.count('data-scene-id="cell:frr:Float"') == 1


def test_svg_materializer_does_not_read_an_unused_font_byte_pin(tmp_path):
    copied_example = tmp_path / "halcyon-font"
    shutil.copytree(ROOT / "examples/halcyon-1", copied_example)
    context = copied_example / "contexts/02-programme-board.yaml"
    value = yaml.safe_load(context.read_text(encoding="utf-8"))
    value["body"]["environment"]["fontMetrics"]["assets"][0]["font"]["contentIdentity"] = "sha256:" + "0" * 64
    context.write_text(yaml.safe_dump(value, sort_keys=False))
    expected = copied_example / "generated/02-programme-board.svg"
    original = expected.read_bytes()
    materialize(copied_example / "manifest.yaml", "programme-board", tmp_path / "out-font", write=True)
    assert expected.read_bytes() == original


def test_materializer_rejects_draft_substitution_before_evidence_emission(tmp_path):
    copied_example = tmp_path / "halcyon-substitute"
    shutil.copytree(ROOT / "examples/halcyon-1", copied_example)
    context_path = copied_example / "contexts/02-programme-board.yaml"
    context = yaml.safe_load(context_path.read_text(encoding="utf-8"))
    context["body"]["environment"]["fontMetrics"]["missingFont"] = "substitute"
    context_path.write_text(yaml.safe_dump(context, sort_keys=False), encoding="utf-8")
    with pytest.raises(ClosureError, match="E_FONT_SUBSTITUTE_CONTEXT"):
        materialize(copied_example / "manifest.yaml", "programme-board", tmp_path / "out-substitute", write=False)


def test_svg_materializer_closes_declared_local_metrics_without_copying_unused_font_bytes(tmp_path):
    copied_example = tmp_path / "local-font"
    shutil.copytree(ROOT / "examples/controller-z", copied_example)
    source = ROOT / "src/chrona/resources"
    font_target = copied_example / "assets/font.ttf"
    metrics_target = copied_example / "assets/metrics.json"
    font_target.parent.mkdir(exist_ok=True); font_target.write_bytes((source / "fonts/noto-sans-regular-v1.ttf").read_bytes())
    metrics_target.write_bytes((source / "font_metrics/noto-sans-regular-v2.json").read_bytes())
    context_path = copied_example / "contexts/executive.yaml"
    context = yaml.safe_load(context_path.read_text(encoding="utf-8"))
    asset = context["body"]["environment"]["fontMetrics"]["assets"]
    asset[:] = [{"family": "Noto Sans", "weight": 400,
                 "metrics": {"locator": {"provider": "context", "address": "assets/metrics.json"}, "contentIdentity": "sha256:" + sha256(metrics_target.read_bytes()).hexdigest()},
                 "font": {"locator": {"provider": "context", "address": "assets/font.ttf"}, "contentIdentity": "sha256:" + sha256(font_target.read_bytes()).hexdigest()}}]
    context_path.write_text(yaml.safe_dump(context, sort_keys=False), encoding="utf-8")
    reference, revision = _copy_context_closure(copied_example, context_path, tmp_path / "snapshot")
    assert (snapshot_directory(tmp_path / "snapshot", revision) / "assets/metrics.json").read_bytes() == metrics_target.read_bytes()
    assert not (snapshot_directory(tmp_path / "snapshot", revision) / "assets/font.ttf").exists()
    assert reference["id"] == "controller-z-executive"


def test_materialized_context_font_pair_reaches_the_default_png_adapter(tmp_path):
    copied_example = tmp_path / "local-raster-font"
    shutil.copytree(ROOT / "examples/controller-z", copied_example)
    source = ROOT / "src/chrona/resources"
    font_target = copied_example / "assets/font.ttf"
    metrics_target = copied_example / "assets/metrics.json"
    font_target.parent.mkdir(exist_ok=True)
    font_target.write_bytes((source / "fonts/noto-sans-regular-v1.ttf").read_bytes())
    metrics_target.write_bytes((source / "font_metrics/noto-sans-regular-v2.json").read_bytes())
    context_path = copied_example / "contexts/executive.yaml"
    context = yaml.safe_load(context_path.read_text(encoding="utf-8"))
    context["body"]["environment"]["fontMetrics"]["assets"] = [{
        "family": "Noto Sans", "weight": 400,
        "metrics": {"locator": {"provider": "context", "address": "assets/metrics.json"}, "contentIdentity": "sha256:" + sha256(metrics_target.read_bytes()).hexdigest()},
        "font": {"locator": {"provider": "context", "address": "assets/font.ttf"}, "contentIdentity": "sha256:" + sha256(font_target.read_bytes()).hexdigest()},
    }]
    import resvg_py
    context["body"]["environment"]["rasterizer"] = {
        "engine": "resvg-py", "version": resvg_py.__version__, "resvgVersion": resvg_py.__resvg_version__, "dpi": 96,
    }
    context["body"]["target"] = {"kind": "png", "visualProfile": "chrona-output/visual/v0.6-png", "capabilities": []}
    context_path.write_text(yaml.safe_dump(context, sort_keys=False), encoding="utf-8")

    snapshot = tmp_path / "snapshot"; snapshot.mkdir()
    reference, revision = copy_context_closure(copied_example, context_path, snapshot)
    closure = resolve_render_context(reference, LocalSnapshotReader(snapshot, "controller-z-example"))
    rendered = render_review(RenderRequest(closure, snapshot, ReferenceScheduler()))

    assert rendered.artifact.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert (snapshot_directory(snapshot, revision) / "assets/font.ttf").is_file()
    assert sha256(font_target.read_bytes()).hexdigest() in rendered.artifact.adapter_identity


def test_materializer_records_selected_scenario_evidence_and_omits_unselected_scenarios(tmp_path):
    example = ROOT / "examples/halcyon-1"
    manifest = example / "manifest.yaml"
    materialize(manifest, "tvac-slip", tmp_path / "scenario", write=False)
    evidence = yaml.safe_load((tmp_path / "scenario/closure.yaml").read_text(encoding="utf-8"))
    assert evidence["scenarios"][0]["scenarioId"] == "tvac-slip"
    assert evidence["scenarios"][0]["title"] == "System TVAC slips one week"
    assert evidence["scenarios"][0]["contentIdentity"].startswith("sha256:")
    assert "data-purpose=\"snapshot\"" in (tmp_path / "scenario/review.svg").read_text(encoding="utf-8")
    assert "System TVAC slips one week" in (tmp_path / "scenario/review.svg").read_text(encoding="utf-8")

    materialize(manifest, "programme-board", tmp_path / "primary", write=False)
    assert "scenarios" not in yaml.safe_load((tmp_path / "primary/closure.yaml").read_text(encoding="utf-8"))

    copied = tmp_path / "changed"
    shutil.copytree(example, copied)
    project = copied / "project.yaml"
    changed = yaml.safe_load(project.read_text(encoding="utf-8"))
    changed["scenarios"]["tvac-slip"]["objects"]["tvac"]["schedule"]["amount"] = "20d"
    project.write_text(yaml.safe_dump(changed, sort_keys=False))
    materialize(copied / "manifest.yaml", "tvac-slip", tmp_path / "changed-output", write=True)
    changed_evidence = yaml.safe_load((tmp_path / "changed-output/closure.yaml").read_text(encoding="utf-8"))
    assert changed_evidence["scenarios"][0]["contentIdentity"] != evidence["scenarios"][0]["contentIdentity"]
