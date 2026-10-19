"""Declared scale -> final legend -> paired warning and actual SVG (#1756)."""
from datetime import date
from xml.etree import ElementTree

from tests.integration.test_realized_legends import (
    ACTUAL, _detail, _parts, _render, _render_with_style, _source, _svg_fills,
)
from tests.support import synthetic_review as sr


def _encoded_parts(slots=None):
    slots = slots or {"a": "#269D78"}
    parts = _parts()
    parts["view"]["body"]["colorEncoding"] = {
        "scale": "risk", "target": "planned", "source": {"field": "owner"}, "domain": list(slots)}
    parts["theme"]["body"]["colorScales"] = {"risk": {"slots": {key: f"risk-{key}" for key in slots}}}
    parts["scheme"]["body"]["categories"].update({f"risk-{key}": value for key, value in slots.items()})
    return parts


def test_realized_explicit_slot_warns_against_semantic_key_with_both_names_and_svg_ink(tmp_path):
    parts = _encoded_parts()
    rendered = _render(tmp_path, _source(), actual=ACTUAL, parts=parts,
                       detail=_detail(("actual", "Observed")))
    records = [item for item in rendered.warning_records
               if item.payload["code"] == "W_LEGEND_COLOR_NOT_SEPARABLE"
               and any("Team a" in subject["title"]
                       for subject in item.payload.get("sourceSubjects", ()))
               and any(subject["sourceRef"].startswith("legend-key:actual:")
                       for subject in item.payload.get("sourceSubjects", ()))]
    assert records, "a real View slot must be compared with the realized Actual key"
    root = ElementTree.fromstring(rendered.artifact.content)
    svg = {node.attrib["data-scene-id"]: node for node in root.iter()
           if "data-scene-id" in node.attrib}
    primitives = {item.scene_id: item for item in rendered.surface.primitives}
    for record in records:
        payload = record.payload
        assert record.identity in rendered.surface.diagnostics
        assert len(payload["sourceSubjects"]) == 2
        assert "normal vision" in payload["message"] and "ΔE=" in payload["message"]
        assert "Team a" in payload["message"] and "On track" in payload["message"]
        fills = set()
        for subject in payload["sourceSubjects"]:
            assert subject["title"] in payload["message"]
            key = subject["sourceRef"].removeprefix("legend-key:")
            primitive = primitives[f"legend-swatch:{key}"]
            assert primitive.purpose == "legend-swatch"
            assert svg[primitive.scene_id].attrib["fill"] == primitive.paint.fill
            fills.add(primitive.paint.fill.upper())
        assert fills == {"#269D78", "#269D79"}


def test_unrealized_semantic_candidate_does_not_generate_a_colour_warning(tmp_path):
    parts = _encoded_parts()
    rendered = _render(tmp_path, _source(), parts=parts,
                       detail=_detail(("actual", "Observed")))
    assert not any(item.scene_id.startswith("legend:actual:")
                   for item in rendered.surface.primitives if item.purpose == "legend-label")
    assert not any(item.payload["code"] == "W_LEGEND_COLOR_NOT_SEPARABLE"
                   for item in rendered.warning_records)


def test_same_scale_explicit_slots_keep_the_domain_warning_without_a_duplicate_legend_warning(tmp_path):
    source = sr.project({"first": sr.span("first", date(2026, 2, 2), 5, owner="a"),
                         "second": sr.span("second", date(2026, 2, 9), 5, owner="b")})
    rendered = _render(tmp_path, source, parts=_encoded_parts({"a": "#0000FF", "b": "#0000FE"}))
    records = [item.payload for item in rendered.warning_records
               if item.payload["code"] == "W_PRESENTATION_SCALE_NOT_SEPARABLE"]
    assert len(records) == 1
    assert records[0]["scaleId"] == "risk" and records[0]["values"] == ["a", "b"]
    assert records[0]["vision"] == "normal" and records[0]["deltaE"] < 5
    assert "a and b" in records[0]["message"]
    assert not any(item.payload["code"] == "W_LEGEND_COLOR_NOT_SEPARABLE"
                   for item in rendered.warning_records)


def test_same_scale_same_value_distinct_style_scopes_warn_with_both_completed_keys(tmp_path):
    source = sr.project({
        "one": sr.span("one", date(2026, 2, 2), 5, owner="a"),
    })
    for item in source["objects"].values():
        item["fields"]["phase"] = "a"

    parts = _parts()
    parts["theme"]["body"]["colorScales"] = {"shared": {"slots": {"a": "shared-a"}}}
    parts["scheme"]["body"]["categories"]["shared-a"] = "#269D78"
    actual = {
        "version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "same-value-actual",
        "body": {"asOf": "2026-02-20", "observations": [
            {"id": "one", "sequence": 1, "projectObjectId": "one",
             "actual": {"start": "2026-02-02", "finish": "2026-02-07"}},
        ]},
    }
    rules = (
        {"id": "owner-scope", "when": {"semantic": "planned"},
         "then": {"encode": {"channel": "fill", "source": {"field": "owner"},
                              "scale": "shared", "domain": ["a"],
                              "legend": {"title": "Planned owner"}}}},
        {"id": "phase-scope", "when": {"semantic": "actual"},
         "then": {"encode": {"channel": "fill", "source": {"field": "phase"},
                              "scale": "shared", "domain": ["a"],
                              "legend": {"title": "Actual phase"}}}},
    )
    style = {"version": "chrona/style/v0.2", "kind": "style", "id": "two-scopes",
             "body": {"rules": list(rules)}}

    rendered = _render_with_style(tmp_path, source, parts=parts, style=style, actual=actual)

    records = [item for item in rendered.warning_records
               if item.payload["code"] == "W_LEGEND_COLOR_NOT_SEPARABLE"]
    def has_two_scopes(item):
        titles = [subject["title"] for subject in item.payload["sourceSubjects"]]
        return (len(titles) == 2 and any(title.startswith("Planned owner: a (") for title in titles)
                and any(title.startswith("Actual phase: a (") for title in titles))

    matching = [item for item in records if has_two_scopes(item)]
    assert len(matching) == 1, [
        [subject["title"] for subject in item.payload["sourceSubjects"]] for item in records
    ]
    payload = matching[0].payload
    subjects = payload["sourceSubjects"]
    assert len(subjects) == 2
    assert {subject["title"].split(" (", 1)[0] for subject in subjects} == {
        "Planned owner: a", "Actual phase: a",
    }
    assert len({subject["sourceRef"] for subject in subjects}) == 2
    assert all("legend-key:scale:style:" in subject["sourceRef"] for subject in subjects)
    assert not any(item.payload["code"] == "W_PRESENTATION_SCALE_NOT_SEPARABLE"
                   for item in rendered.warning_records)

    by_ref = {item.source_ref: item for item in rendered.surface.primitives
              if item.purpose == "legend-swatch"}
    svg_fills = _svg_fills(rendered)
    inks = set()
    for subject in subjects:
        swatch = by_ref[subject["sourceRef"].removeprefix("legend-key:")]
        inks.add(swatch.paint.fill.upper())
        assert svg_fills[swatch.scene_id] == swatch.paint.fill
    assert inks == {"#269D78"}
