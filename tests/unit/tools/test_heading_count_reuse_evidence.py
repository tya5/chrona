"""Evidence conversions are template-only and preserve literal style/semantic bindings."""
from copy import deepcopy

import pytest

from tools.heading_count_reuse_evidence import GROUPS, ITEMS, NOTES, _caption, _connect_annotations, _template_view


@pytest.mark.parametrize("design,text,expected", [
    ("titlecard", "26 WORK PACKAGES · 6 SECTIONS", f"{{figure:{ITEMS}}} WORK PACKAGES · {{figure:{GROUPS}}} SECTIONS"),
    ("marquee", "Twenty-six work packages in six acts", f"{{figure:{ITEMS}}} work packages in {{figure:{GROUPS}}} acts"),
    ("sunday", "in six panels", f"in {{figure:{GROUPS}}} panels"),
])
def test_conversion_preserves_all_other_view_members_and_existing_figures(design, text, expected):
    view = {"body": {"heading": {"title": "{project}", "subtitle": text},
                     "figures": [{"id": "existing", "kind": "daysUntil", "to": "asOf"}],
                     "selection": {"include": {"types": ["span"]}}, "annotations": [{"id": "n"}]}}
    before = deepcopy(view)
    _template_view(view, design)
    assert view["body"]["heading"]["subtitle"] == expected
    assert view["body"]["heading"]["title"] == before["body"]["heading"]["title"]
    assert view["body"]["figures"][0] == before["body"]["figures"][0]
    assert view["body"]["selection"] == before["body"]["selection"]
    assert view["body"]["annotations"] == before["body"]["annotations"]
    assert {item["id"] for item in view["body"]["figures"][-3:]} == {ITEMS, GROUPS, NOTES}


def test_caption_changes_only_explicit_known_copy_and_keeps_allocation_intent():
    node = {"kind": "row", "children": [{"kind": "slot", "source": "annotations", "id": "reports",
        "inlineSize": "fill", "heading": {"text": "STATUS REPORTS : 03", "align": "start", "block": "header-row"}},
        {"kind": "slot", "source": "legend", "heading": {"text": "Key"}}]}
    _caption(node)
    first, second = node["children"]
    assert first["heading"] == {"template": f"STATUS REPORTS : {{figure:{NOTES}}}", "align": "start", "block": "header-row"}
    assert first["inlineSize"] == "fill" and second["heading"] == {"text": "Key"}


def test_worker_records_detector_code_message_and_pointer_instead_of_pickling_exception(monkeypatch):
    from pathlib import Path
    from chrona.usecases.render_review import RenderFailed
    from tools import heading_count_reuse_evidence as evidence
    def fail(case):
        raise RenderFailed("E_EXAMPLE", "owned cause", "view", "/body/heading/title")
    monkeypatch.setattr(evidence, "characterize", fail)
    result = evidence.run_case((Path("manifest.yaml"), "titlecard", "roadmap", Path("out")))
    assert result == {"project": "roadmap", "design": "titlecard", "error": {
        "type": "RenderFailed", "code": "E_EXAMPLE", "message": "owned cause", "pointer": "/body/heading/title"}}


def test_project_anchor_and_reference_keep_the_designs_placement_policy_without_mutation():
    design = [{"purpose": "note", "candidates": [{"region": {"kind": "plot"}, "search": {"maxInlineEm": 12}}]}]
    project = [{"id": "n", "purpose": "note", "anchor": {"id": "roadmap-task"}, "projectAnnotation": "source",
                "candidates": [{"region": {"kind": "slot", "source": "annotations"}}]}]
    before = deepcopy((design, project))
    result = _connect_annotations(design, project)
    assert result[0]["anchor"] == project[0]["anchor"]
    assert result[0]["projectAnnotation"] == "source"
    assert result[0]["candidates"] == design[0]["candidates"]
    result[0]["candidates"][0]["search"]["maxInlineEm"] = 8
    assert (design, project) == before


def test_ambiguous_design_purpose_policy_is_not_guessed():
    with pytest.raises(ValueError, match="ambiguous"):
        _connect_annotations([{"purpose": "note", "placement": {"side": "start"}},
                              {"purpose": "note", "placement": {"side": "end"}}], [])
