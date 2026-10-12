"""Disposable real-Context materializer evidence for #1346; never edit authored examples."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

import yaml

from chrona.resources import safe_load
from chrona.usecases.materialize import materialize

DESIGNS = {"titlecard": "23-titlecard", "marquee": "24-marquee", "sunday": "25-sunday"}
ITEMS, GROUPS, NOTES = "heading-items", "heading-groups", "heading-notes"


def _load(path):
    return safe_load(path.read_bytes())


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _pin(reference, path):
    reference["contentIdentity"] = "sha256:" + sha256(path.read_bytes()).hexdigest()
    reference["revision"] = {"token": "issue-1346-evidence"}


def _template_view(view, design):
    body = view["body"]
    body.setdefault("figures", []).extend([
        {"id": ITEMS, "kind": "count", "source": "selected"},
        {"id": GROUPS, "kind": "count", "source": "groups"},
        {"id": NOTES, "kind": "count", "source": "placedNotes"},
    ])
    subtitle = body["heading"]["subtitle"]
    if design == "titlecard":
        body["heading"]["subtitle"] = subtitle.replace("26 WORK PACKAGES", f"{{figure:{ITEMS}}} WORK PACKAGES").replace(
            "6 SECTIONS", f"{{figure:{GROUPS}}} SECTIONS")
        body["figureFormats"] = {NOTES: {"form": "digits", "minimumDigits": 2}}
    elif design == "marquee":
        body["heading"]["subtitle"] = subtitle.replace("Twenty-six", f"{{figure:{ITEMS}}}").replace(
            "six acts", f"{{figure:{GROUPS}}} acts")
        body["figureFormats"] = {ITEMS: {"form": "english-words", "capitalize": True}, GROUPS: {"form": "english-words"}}
    else:
        body["heading"]["subtitle"] = subtitle.replace("six panels", f"{{figure:{GROUPS}}} panels")
        body["figureFormats"] = {GROUPS: {"form": "english-words"}}


def _caption(node):
    if node.get("kind") == "slot" and node.get("source") == "annotations":
        heading = node.get("heading")
        if heading and heading.get("text") == "STATUS REPORTS : 03":
            heading.pop("text")
            heading["template"] = f"STATUS REPORTS : {{figure:{NOTES}}}"
    for child in node.get("children", ()):
        _caption(child)


def _connect_annotations(design_entries, project_entries):
    """Connect project subjects/copy while retaining the design's unique purpose policy."""
    policies = {}
    for annotation in design_entries:
        policy = {key: annotation[key] for key in ("candidates", "placement") if key in annotation}
        purpose = annotation["purpose"]
        if purpose in policies and policies[purpose] != policy:
            raise ValueError(f"ambiguous design policy for purpose {purpose}")
        policies[purpose] = policy
    result = []
    for annotation in project_entries:
        connected = {key: deepcopy(value) for key, value in annotation.items() if key not in {"candidates", "placement"}}
        connected.update(deepcopy(policies[annotation["purpose"]]))
        result.append(connected)
    return result


def prepare(root: Path, repo: Path):
    inputs = root / "inputs"
    for name in ("halcyon-1", "chrona-roadmap"):
        shutil.copytree(repo / "examples" / name, inputs / name, ignore=shutil.ignore_patterns("generated"))
    halcyon, roadmap = inputs / "halcyon-1", inputs / "chrona-roadmap"
    hal_manifest = _load(halcyon / "manifest.yaml")
    road_manifest = _load(roadmap / "manifest.yaml")
    road_context = _load(roadmap / "contexts/roadmap.yaml")
    road_view = _load(roadmap / "views/roadmap.yaml")
    road_manifest["stores"] = [{"identity": "halcyon-1-example", "root": "../halcyon-1"}]
    road_manifest["slides"] = []
    cases = []
    for design, name in DESIGNS.items():
        view_path = halcyon / "views" / f"{name}.yaml"
        view = _load(view_path)
        _template_view(view, design)
        _write(view_path, view)
        context_path = halcyon / "contexts" / f"{name}.yaml"
        context = _load(context_path)
        _pin(context["body"]["view"], view_path)
        if design == "titlecard":
            layout_path = halcyon / context["body"]["layout"]["address"]
            layout = _load(layout_path)
            _caption(layout["root"])
            _write(layout_path, layout)
            _pin(context["body"]["layout"], layout_path)
        _write(context_path, context)
        cases.append((halcyon / "manifest.yaml", design, "halcyon", root))
        # View is the project connector; design Theme/Layout/Scheme stay shared.
        connected = deepcopy(view)
        connected["id"] = f"roadmap-reuse-{design}"
        body, bindings = connected["body"], road_view["body"]
        for member in ("selection", "window", "annotationBindings", "periods"):
            if member in bindings:
                body[member] = deepcopy(bindings[member])
            else:
                body.pop(member, None)
        body["annotations"] = _connect_annotations(view["body"].get("annotations", ()), bindings.get("annotations", ()))
        if body.get("grouping", {}).get("by") == "field":
            body["grouping"]["order"] = deepcopy(bindings["grouping"]["order"])
        for figure in body["figures"]:
            if figure["kind"] == "daysUntil":
                figure["to"] = {"object": "rc-gate", "endpoint": "at"}
        road_view_path = roadmap / "views" / f"reuse-{design}.yaml"
        _write(road_view_path, connected)
        shared = deepcopy(context)
        shared["id"] = f"roadmap-reuse-{design}"
        shared["body"]["project"] = deepcopy(road_context["body"]["project"])
        for member in ("actual", "snapshot"):
            shared["body"]["inputs"][member] = deepcopy(road_context["body"]["inputs"][member])
        reference = shared["body"]["view"]
        reference.update(id=connected["id"], address=f"views/reuse-{design}.yaml", store=deepcopy(road_context["body"]["view"]["store"]))
        _pin(reference, road_view_path)
        road_context_path = roadmap / "contexts" / f"reuse-{design}.yaml"
        _write(road_context_path, shared)
        road_manifest["slides"].append({"id": design, "evidence": "Disposable #1346 same-template design reuse",
            "context": f"contexts/reuse-{design}.yaml", "expectedSvg": f"generated/reuse-{design}.svg",
            "expectedScene": f"generated/reuse-{design}.scene.json"})
        cases.append((roadmap / "manifest.yaml", design, "roadmap", root))
        control = deepcopy(connected)
        control["id"] = f"roadmap-control-{design}"
        control["body"]["selection"] = {"include": {"ids": ["titlecard", "route-bound", "japanese"]}}
        control_view = roadmap / "views" / f"control-{design}.yaml"
        _write(control_view, control)
        control_context = deepcopy(shared)
        control_context["id"] = control["id"]
        control_reference = control_context["body"]["view"]
        control_reference.update(id=control["id"], address=f"views/control-{design}.yaml")
        _pin(control_reference, control_view)
        _write(roadmap / "contexts" / f"control-{design}.yaml", control_context)
        road_manifest["slides"].append({"id": f"control-{design}", "evidence": "Same immutable roadmap, independent3/2 View membership control",
            "context": f"contexts/control-{design}.yaml", "expectedSvg": f"generated/control-{design}.svg",
            "expectedScene": f"generated/control-{design}.scene.json"})
        cases.append((roadmap / "manifest.yaml", f"control-{design}", "roadmap-control", root))
    _write(roadmap / "manifest.yaml", road_manifest)
    return cases


def characterize(case):
    manifest, design, project, root = case
    from chrona.presentation import surface_pipeline as pipeline
    completed = []
    original = pipeline.complete_surface_render_plan
    def observe(*args, **kwargs):
        result = original(*args, **kwargs)
        completed.append(result)
        return result
    pipeline.complete_surface_render_plan = observe
    try:
        result = materialize(manifest, design, root / "rendered" / project / design, write=True)
    finally:
        pipeline.complete_surface_render_plan = original
    final = completed[-1]
    items = {item.object_id for item in final.projection.items if item.source_kind in {"primary", "combined"}}
    groups = {item.group_id for item in final.projection.items if item.source_kind in {"primary", "combined"} and item.group_id}
    notes = len(final.composition.placement.narrative_receipts)
    assert dict(final.projection.figures)[ITEMS] == len(items)
    assert dict(final.projection.figures)[GROUPS] == len(groups)
    assert dict(final.projection.figures)[NOTES] == notes
    if project == "roadmap-control":
        assert (len(items), len(groups)) == (3, 2)
    texts = {p.scene_id: p.text for p in result.rendered.surface.primitives
             if p.scene_id == "subtitle" or p.scene_id.startswith("slot-heading:")}
    xml = ET.fromstring(result.output.read_bytes())
    svg_text = {e.get("data-scene-id"): "".join(e.itertext()) for e in xml.iter() if e.tag.endswith("}text")}
    for identifier, text in texts.items():
        assert svg_text.get(identifier) == text, (identifier, text, svg_text.get(identifier))
    if project == "halcyon":
        repo = Path(__file__).resolve().parents[1]
        original_manifest = _load(repo / "examples/halcyon-1/manifest.yaml")
        slide = next(item for item in original_manifest["slides"] if item["id"] == design)
        original_scene = json.loads((repo / "examples/halcyon-1" / slide["expectedScene"]).read_bytes())
        before = {p["id"]: p.get("text") for surface in original_scene["surfaces"] for p in surface["primitives"]
                  if p["id"] in texts}
        assert before == texts, (design, before, texts)
    return {"project": project, "design": design, "selected": len(items), "groups": len(groups), "placedNotes": notes,
            "texts": texts, "trials": len(final.trials), "svgSha256": sha256(result.output.read_bytes()).hexdigest()}


def run_case(case):
    """Keep every failed case readable across process boundaries, including unpicklable exceptions."""
    try:
        return characterize(case)
    except Exception as error:
        return {"project": case[2], "design": case[1], "error": {
            "type": type(error).__name__, "code": getattr(error, "code", getattr(error, "diagnostic_id", None)),
            "message": getattr(error, "message", getattr(error, "detail", str(error))),
            "pointer": getattr(error, "source_ref", getattr(error, "path", None))}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=3)
    parser.add_argument("--control-only", action="store_true", help="Render only independent3/2 controls (reuse checks remain in the full run).")
    args = parser.parse_args()
    root = args.output_dir.resolve()
    if args.jobs < 1 or (root.exists() and any(root.iterdir())):
        parser.error("positive jobs and an empty output directory required")
    root.mkdir(parents=True, exist_ok=True)
    cases = prepare(root, Path(__file__).resolve().parents[1])
    if args.control_only:
        cases = [case for case in cases if case[2] == "roadmap-control"]
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(run_case, cases))
    (root / "heading-reuse-evidence.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for result in results:
        print(json.dumps(result, ensure_ascii=False), flush=True)
    return int(any("error" in result for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
