"""Source-local object references reach actual table SVG and encoding legends (#344)."""
from copy import deepcopy
from datetime import date
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
import yaml

from chrona.presentation.model.field_roles import FieldDescriptor, FieldRoleBindings
from chrona.presentation.model.projection import ReviewItem
from chrona.presentation.model.surface_content import table_value
from chrona.presentation.model.style_rules import (
    OccurrenceStyleIndex, StyleFieldFact, StyleOccurrence, StyleOccurrenceKey, evaluate_style_rules,
)
from chrona.presentation.model.style_fills import complete_style_fills
from chrona.presentation.review.v05_content import _style_legend_entries
from chrona.presentation.style import (
    EncodingSource, StyleEncodingOutcome, StyleFieldSource, StyleRule, StyleSelector, bind_style_rules,
)
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from tests.support import synthetic_review as sr


def _source(title="Payload team", *, many=False, second_title=None):
    def task(key, profile, **fields):
        result = sr.span(key, date(2026, 3, 2), 5)
        result.update(type=profile, fields=fields)
        return result

    objects = {
        "work-a": task("work-a", "acme.work", reference=["target-a", "target-b"] if many else "target-a"),
        "target-a": task("target-a", "acme.target"),
        "target-b": task("target-b", "acme.target"),
    }
    objects["target-a"]["title"] = title
    objects["target-b"]["title"] = second_title or "Bus team"
    source = sr.project(objects, responsible_field_role=False)
    source["extensions"] = [{"packageId": "acme", "path": "package.yaml",
                             "revision": "git:" + "1" * 40}]
    source["fieldRoles"] = {"responsible": "reference"}
    declaration = {"type": "objectReference", "targetProfiles": ["acme.target"]}
    if many:
        declaration["cardinality"] = "many"
    package = {"version": "chrona/profile/v0.3", "packageId": "acme",
               "requires": {"projectFormat": "timeline/v0.7"}, "profiles": {
                   "acme.work": {"extends": "task", "fields": {"reference": declaration}},
                   "acme.target": {"extends": "task"},
               }}
    return source, package


def _render(directory, *, title="Payload team", many=False, lane=False, locale="en-US",
            encoding=None, predicate=None, source_package=None):
    directory.mkdir(parents=True, exist_ok=True)
    source, package = source_package or _source(title, many=many, second_title=title if encoding else None)
    parts = sr.bundle()
    body = parts["view"]["body"]
    column = {"id": "Reference", "source": {"fieldRole": "responsible"},
              "width": "content", "missing": "blank", "align": "start", "headerOrientation": "horizontal"}
    body["rows"] = {"mode": "automatic"}
    body["grouping"] = {"by": "none", "missing": "ungrouped"}
    body["tableColumns"] = [column]
    body.pop("hierarchyColumn", None)
    body["visibility"]["labels"] = {"placement": "none", "content": ["title"], "side": "end"}
    if lane:
        body.pop("tableColumns")
        body.pop("hierarchyColumn", None)
        lane_column = {key: value for key, value in column.items() if key not in {"width", "headerOrientation"}}
        body["rows"] = {"mode": "lanes", "packing": ["explicit"], "laneTable": {
            "label": "lane", "columns": [{"id": "Lane", "source": "label"}, lane_column]}}
        body["visibility"]["labels"]["placement"] = "plot"
    rules = []
    if encoding:
        source["objects"]["work-b"] = deepcopy(source["objects"]["work-a"])
        source["objects"]["work-b"].update(title="Work B", fields={"reference": "target-b"})
        parts["theme"]["body"]["colorScales"] = {"refs": {"slots": {
            "target-a": "ref-a", "target-b": "ref-b"}}}
        parts["scheme"]["body"]["categories"].update({"ref-a": "#2255aa", "ref-b": "#aa5522"})
        encode = {"source": {"field": "reference"}, "scale": "refs", "domain": ["target-a", "target-b"]}
        if encoding == "view":
            body["colorEncoding"] = {**encode, "target": "planned"}
        else:
            rules.append({"id": "reference-fill", "when": {"semantic": "planned"},
                          "then": {"encode": {**encode, "channel": "fill"}}})
    if predicate is not None:
        rules.append({"id": "reference-title", "when": {"semantic": "planned", "fields": [
            {"source": {"fieldRole": "responsible"}, "equals": predicate}]},
            "then": {"role": "planned"}})
    paths = {kind: sr._write(directory / f"{kind}.yaml", value) for kind, value in parts.items()}
    sr._write(directory / "package.yaml", package)
    project_path = sr._write(directory / "project.yaml", source)
    style = None
    if rules:
        style = sr._write(directory / "style.yaml", {"version": "chrona/style/v0.2", "kind": "style",
            "id": "references", "body": {"rules": rules}})
    rendered = render_draft(DraftRenderRequest(
        project=project_path, target_kind="svg", view=paths["view"], theme=paths["theme"],
        scheme=paths["scheme"], layout=paths["layout"], style=style, locale=locale,
    )).rendered
    return rendered


def _svg_texts(rendered):
    root = ET.fromstring(rendered.artifact.content)
    return ["".join(node.itertext()) for node in root.iter("{http://www.w3.org/2000/svg}text")]


@pytest.mark.parametrize("locale,title", [("en-US", "Payload team"), ("ja-JP", "開発チーム")])
@pytest.mark.parametrize("lane", [False, True])
def test_reference_column_uses_target_title_in_final_svg(tmp_path, locale, title, lane):
    rendered = _render(tmp_path, title=title, locale=locale, lane=lane)
    cells = [node for node in rendered.surface.primitives if node.table_column_id == "Reference"]
    assert any(node.text == title for node in cells)
    assert title in _svg_texts(rendered)
    assert "target-a" not in _svg_texts(rendered)


def test_many_reference_column_keeps_declared_order_in_final_svg(tmp_path):
    rendered = _render(tmp_path, many=True)
    assert "Payload team, Bus team" in _svg_texts(rendered)


@pytest.mark.parametrize("encoding", ["view", "style"])
def test_same_title_targets_keep_distinct_raw_id_colours_and_legend_keys(tmp_path, encoding):
    rendered = _render(tmp_path, encoding=encoding)
    marks = {node.source_ref: node for node in rendered.surface.primitives
             if node.scene_id.startswith("planned:") and node.encoding is not None}
    assert marks["work-a"].encoding.value == "target-a"
    assert marks["work-b"].encoding.value == "target-b"
    assert marks["work-a"].paint.fill == "#2255aa"
    assert marks["work-b"].paint.fill == "#aa5522"
    assert _svg_texts(rendered).count("Payload team") >= 4  # two cells and two distinct keys
    assert "target-a" not in _svg_texts(rendered)
    assert "target-b" not in _svg_texts(rendered)


@pytest.mark.parametrize("predicate,matches", [("Payload team", True), ("target-a", False)])
def test_style_reference_predicate_reads_title_not_raw_id(tmp_path, predicate, matches):
    rendered = _render(tmp_path, predicate=predicate)
    mark = next(node for node in rendered.surface.primitives
                if node.source_ref == "work-a" and node.scene_id.startswith("planned:"))
    assert (mark.style_match is not None) is matches


def test_source_local_snapshot_and_scenario_titles_do_not_lookup_primary_entities():
    descriptor = FieldDescriptor("reference", "objectReference", target_profiles=("acme.target",))
    items = []
    for kind, title in (("primary", "Current"), ("snapshot", "Archived"), ("scenario", "Variant")):
        source, _ = _source(title)
        bindings = FieldRoleBindings.from_project(source, object_descriptors={"work-a": (descriptor,)})
        item = ReviewItem("work-a", "Work", "span", {}, None, None, (),
                          source_kind=kind, fields={"reference": "target-a"}, field_bindings=bindings)
        items.append(item)
    unrelated = {"entities": {"target-a": {"title": "Wrong primary"}, "Current": {"title": "Double lookup"}}}
    assert [table_value(item, unrelated, {"fieldRole": "responsible"}) for item in items] == [
        "Current", "Archived", "Variant"]


@pytest.mark.parametrize("titles", [("Archived", "Current"), ("Current", "Archived")])
def test_reference_legend_title_uses_first_matched_occurrence_not_title_sorting(titles):
    occurrences = tuple(StyleOccurrence(
        StyleOccurrenceKey(f"work-{index}", source, "planned"), "planned", "mark",
        fields=(StyleFieldFact("reference", "objectReference", True, "target-a",
                               reference_title=title,
                               reference_identity=("plan", "objects", "target-a")),),
    ) for index, (source, title) in enumerate(zip(("snapshot", "primary"), titles, strict=True)))
    rules = bind_style_rules("references", (StyleRule(
        "reference-fill", StyleSelector(purpose="planned"),
        StyleEncodingOutcome("fill", StyleFieldSource(field_name="reference"), "refs", "firstAppearance"),
        "/body/rules/0",
    ),))
    intents = OccurrenceStyleIndex(evaluate_style_rules(rules, occurrences))
    fills = complete_style_fills(intents, occurrences, theme={"body": {
        "colorScales": {"refs": {"palette": ["first"]}}, "categorySlots": {"first": "#2255aa"},
    }}, encoding_sources={rules[0].rule_id: EncodingSource("style", "references", "/body/rules/0/then/encode", "reference-fill")})
    entries, _ = _style_legend_entries(rules, intents, occurrences, fills)
    assert len(entries) == 1
    assert entries[0].label == titles[0]
    assert entries[0].style_value == "target-a"
    assert entries[0].style_occurrences == tuple(occurrence.key for occurrence in occurrences)


def test_delivery_assignee_keeps_entity_domain_when_actor_object_has_the_same_id(tmp_path):
    package = yaml.safe_load((Path(__file__).resolve().parents[2] /
                             "conformance/implementation-delivery-profile-v0.2.yaml").read_bytes())
    work = sr.span("work", date(2026, 3, 2), 5)
    work.update(type="implementation-delivery.work-item", fields={
        "assignees": ["same"], "workflowState": "planned", "reuseClassification": "core",
    })
    actor = sr.span("same", date(2026, 3, 2), 5, title="Actor object")
    actor.update(type="implementation-delivery.person", fields={})
    source = sr.project({"work": work, "same": actor}, responsible_field_role=False)
    source["entities"] = {"same": {"type": "implementation-delivery.person", "title": "Actor entity"}}
    source["fieldRoles"] = {"responsible": "assignees"}
    source["extensions"] = [{"packageId": "implementation-delivery", "path": "package.yaml",
                             "revision": "git:" + "1" * 40}]
    rendered = _render(tmp_path, source_package=(source, package))
    cells = [node.text for node in rendered.surface.primitives if node.table_column_id == "Reference"]
    assert "Actor entity" in cells
    assert "Actor object" not in cells
    assert "Actor entity" in _svg_texts(rendered)
