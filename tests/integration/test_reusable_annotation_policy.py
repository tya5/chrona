"""Real Scene/SVG acceptance without modifying reviewer-owned examples."""
from copy import deepcopy
from datetime import date
from pathlib import Path
import shutil
import json
from xml.etree import ElementTree

import pytest
import yaml

from chrona.usecases.failure_report import report_failure
from chrona.usecases.materialize import materialize
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr


ROOT = Path(__file__).resolve().parents[2]
DESIGNS = ("target-b", "yuya", "titlecard", "marquee", "sunday")


def binding(kind, shape, facet="planned", endpoint="body"):
    return {"kind": kind, "temporalKind": shape, "purpose": "note", "facet": facet, "endpoint": endpoint}


def dump(path, value):
    path.write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True), encoding="utf-8")


@pytest.mark.parametrize("design", DESIGNS)
@pytest.mark.corpus
def test_five_designs_drop_per_id_annotations_with_identical_scene_primitives_and_svg(tmp_path, design):
    source = ROOT / "examples/halcyon-1"
    target = tmp_path / "example"
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("generated"))
    (target / "generated").mkdir()
    manifest = yaml.safe_load((target / "manifest.yaml").read_bytes())
    slide = next(item for item in manifest["slides"] if item["id"] == design)
    manifest["slides"] = [slide]
    for field in ("expectedSvg", "expectedScene"):
        shutil.copy2(source / slide[field], target / slide[field])
    dump(target / "manifest.yaml", manifest)
    public_svg = (target / slide["expectedSvg"]).read_bytes()
    public_scene = json.loads((target / slide["expectedScene"]).read_bytes())
    # Only disposable evidence is regenerated. The approved visible baseline
    # remains an independent gate; corrected measurement may add fit findings.
    original = materialize(target / "manifest.yaml", design, tmp_path / "before", write=True).rendered
    assert original.artifact.content == public_svg
    current_scene = json.loads((tmp_path / "before/review.scene.json").read_bytes())
    assert current_scene["surfaces"][0]["primitives"] == public_scene["surfaces"][0]["primitives"]
    context = yaml.safe_load((target / slide["context"]).read_bytes())["body"]
    view_path, layout_path = (target / context[name]["address"] for name in ("view", "layout"))
    view = yaml.safe_load(view_path.read_bytes())
    layout = yaml.safe_load(layout_path.read_bytes())
    declared = view["body"].pop("annotations")
    assert len(declared) == 3
    assert all(item["candidates"] == declared[0]["candidates"] for item in declared)
    point = binding("note", "point", endpoint="at")
    risk = binding("risk", "span", facet="actual")
    span = binding("note", "span", endpoint="body" if design == "sunday" else "end")
    view["body"]["annotationBindings"] = ([point, risk, span] if design in {"target-b", "yuya", "titlecard"}
                                           else [risk, span, point])
    layout.setdefault("viewDefaults", {})["annotationPlacement"] = {
        "note": {"candidates": deepcopy(declared[0]["candidates"])}}
    dump(view_path, view)
    dump(layout_path, layout)
    migrated = materialize(target / "manifest.yaml", design, tmp_path / "after", write=True).rendered
    assert "annotations" not in view["body"]
    assert migrated.surface.primitives == original.surface.primitives
    assert migrated.scene.diagnostics == original.scene.diagnostics
    assert migrated.artifact.content == original.artifact.content
    notes = [item for item in migrated.surface.primitives if item.scene_id.startswith("annotation-text:")]
    assert len(notes) == 3
    svg = ElementTree.fromstring(migrated.artifact.content)
    ids = {node.get("data-scene-id", node.get("id")) for node in svg.iter()}
    assert {item.scene_id for item in notes} <= ids


def parts_and_source():
    source = sr.project({"work": sr.span("work", date(2027, 1, 4), 8),
                         "gate": sr.point("gate", date(2027, 1, 14))})
    source["annotations"] = {
        "new-span": {"kind": "note", "text": "Another project's span.", "anchor": {"object": "work"}},
        "new-gate": {"kind": "note", "text": "Another project's gate.", "anchor": {"object": "gate"}}}
    parts = sr.bundle()
    parts["view"]["body"].pop("annotations", None)
    parts["view"]["body"]["annotationBindings"] = [binding("note", "point", endpoint="at"), binding("note", "span")]
    parts["view"]["body"]["visibility"]["annotations"] = {"mode": "presentation", "marker": "numbered"}
    parts["layout"].setdefault("viewDefaults", {})["annotationPlacement"] = {
        "note": {"candidates": [sr.candidate("plot-near", connector="leader")]}}
    return parts, source


def test_other_project_notes_use_kind_bindings_and_only_one_narrative_occurrence(tmp_path):
    parts, source = parts_and_source()
    before = deepcopy(source), deepcopy(parts)
    rendered = sr.render(tmp_path, source, presentation=parts)
    assert (source, parts) == before
    notes = [item for item in rendered.surface.primitives if item.scene_id.startswith("annotation-text:")]
    assert [item.scene_id for item in notes] == ["annotation-text:new-gate-note", "annotation-text:new-span-note"]
    svg = ElementTree.fromstring(rendered.artifact.content)
    svg_text = {node.get("data-scene-id", node.get("id")): " ".join(node.itertext())
                for node in svg.iter("{http://www.w3.org/2000/svg}text")}
    for key, note in source["annotations"].items():
        texts = [item.text for item in rendered.surface.primitives if item.text and note["text"] in item.text]
        assert len(texts) == 1, (key, texts)
        assert note["text"] in " ".join(svg_text[f"annotation-text:{key}-note"].split())


def test_synthetic_policy_migration_preserves_completed_primitives_and_svg(tmp_path):
    """Fast PR twin of the five-design corpus sweep: the same general closure rule."""
    automatic, source = parts_and_source()
    explicit = deepcopy(automatic)
    policy = explicit["layout"]["viewDefaults"].pop("annotationPlacement")["note"]
    explicit["view"]["body"].pop("annotationBindings")
    explicit["view"]["body"]["annotations"] = [
        {"id": f"{key}-note", "purpose": "note", "projectAnnotation": key,
         "anchor": {"kind": "object", "id": object_id, "facet": "planned", "endpoint": endpoint},
         **deepcopy(policy)}
        for key, object_id, endpoint in (("new-gate", "gate", "at"), ("new-span", "work", "body"))]
    old_root, new_root = tmp_path / "explicit", tmp_path / "automatic"
    old_root.mkdir()
    new_root.mkdir()
    before = sr.render(old_root, source, presentation=explicit)
    after = sr.render(new_root, source, presentation=automatic)
    assert after.surface.primitives == before.surface.primitives
    assert after.scene.diagnostics == before.scene.diagnostics
    assert after.artifact.content == before.artifact.content


def test_automatic_missing_actual_anchor_reports_real_project_pointer(tmp_path):
    parts, source = parts_and_source()
    parts["view"]["body"]["annotationBindings"][0]["facet"] = "actual"
    with pytest.raises(RenderFailed) as error:
        sr.render(tmp_path, source, presentation=parts)
    assert error.value.code == "E_PRESENTATION_ANCHOR_MISSING"
    assert error.value.source_ref == "/annotations/new-gate/anchor"
    assert report_failure(error.value).diagnostics[0]["sourceRef"] == "/annotations/new-gate/anchor"


def test_automatic_missing_policy_preserves_typed_cli_report(tmp_path):
    parts, source = parts_and_source()
    parts["layout"]["viewDefaults"]["annotationPlacement"] = {}
    with pytest.raises(RenderFailed) as error:
        sr.render(tmp_path, source, presentation=parts)
    report = report_failure(error.value)
    assert report.status == "rejected" and report.exit_code == 1
    assert report.diagnostics[0]["code"] == "E_PRESENTATION_ANNOTATION_POLICY_MISSING"
    assert report.diagnostics[0]["sourceRef"] == "/body/annotationPlacement/note"
    assert "purpose=" in report.diagnostics[0]["message"]
