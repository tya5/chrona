from datetime import date
import pytest
from chrona.presentation.review_svg import append_review_summary, build_review_projection, render_table_timeline_svg

def test_review_projection_keeps_actual_independent_and_marks_variance():
    project={"objects":{"fw":{"title":"FW"},"gate":{"title":"Gate"}}}
    placements={"fw":{"start":date(2026,4,1),"end":date(2026,4,10)},"gate":{"at":date(2026,4,12)}}
    view={"body":{"selection":{"include":{"types":["span","point"]}},"ordering":{"by":"plannedStart"},"window":{"marginDays":2},"comparison":{"actual":"required"}}}
    actual={"body":{"observations":[{"id":"fw-1","sequence":1,"projectObjectId":"fw","actual":{"finish":"2026-04-13"}},{"id":"unknown","sequence":1,"externalIdentity":{"key":"x"},"actual":{"finish":"2026-04-13"}}]}}
    style={"body":{"rules":[{"when":{"facet":"planned","sourceType":"span"},"addRoles":["planned"]},{"when":{"facet":"actual","sourceType":"span"},"addRoles":["actual"]},{"when":{"facet":"finishDelta","comparisonCategory":"behind"},"addRoles":["variance-behind"]}]}}
    result=build_review_projection(project,placements,view,actual,style,{"body":{"roles":{"planned":{}}}})
    assert result.items[0].finish_delta == 3 and "variance-behind" in result.items[0].roles
    assert result.unmatched_actual_ids == ("unknown",) and result.window == (date(2026,3,30),date(2026,4,14))

def test_table_timeline_is_resource_driven():
    project={"objects":{"a":{"title":"A","fields":{"owner":"fw"}}},"entities":{"fw":{"title":"Firmware"}}}
    placements={"a":{"start":date(2026,4,1),"end":date(2026,4,3)}}
    view={"body":{"selection":{"include":{"types":["span"]}},"grouping":{"by":"field","field":"owner","missing":"none"},"ordering":{"by":"plannedStart"},"window":{"marginDays":0},"comparison":{"actual":"optional"},"tableColumns":[{"id":"Owner","source":{"field":"owner"},"missing":"em-dash"},{"id":"Task","source":"title","missing":"em-dash"}]}}
    style={"body":{"rules":[]}}; theme={"body":{"roles":{"planned":{},"actual":{}},"values":{}}}
    projection=build_review_projection(project,placements,view,None,style,theme)
    profile={"groups":{"mode":"header-and-separator","gapRows":1},"axis":{}}
    svg=render_table_timeline_svg("X",projection,project,view,theme,{"sourceMetadata","accessibleText","semanticRoles","marker","tableSemantics","hierarchicalAxis"},profile)
    assert 'table-header' in svg and 'Firmware' in svg and 'data-purpose="axis-major"' in svg

def test_summary_uses_only_declared_metrics():
    projection=build_review_projection({"objects":{"a":{"title":"A"}}},{"a":{"at":date(2026,4,3)}},{"body":{"selection":{"include":{"types":["point"]}},"ordering":{"by":"plannedStart"},"window":{"marginDays":0},"comparison":{"actual":"optional"}}},None,{"body":{"rules":[]}},{"body":{"roles":{"planned":{}}}})
    svg=append_review_summary('<svg></svg>',projection,{"panels":[{"id":"next","metrics":["selectedCount","nextPlannedPoint"]}]},date(2026,4,1))
    assert 'summary-panel' in svg and 'Selected work: 1' in svg and '2026-04-03' in svg

def test_resolved_summary_cannot_append_private_geometry_after_scene_serialization():
    projection=build_review_projection({"objects":{"a":{"title":"A"}}},{"a":{"at":date(2026,4,3)}},{"body":{"selection":{"include":{"types":["point"]}},"ordering":{"by":"plannedStart"},"window":{"marginDays":0},"comparison":{"actual":"optional"}}},None,{"body":{"rules":[]}},{"body":{"roles":{"planned":{}}}})
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_MISSING"):
        append_review_summary('<svg></svg>',projection,{"panels":[{"id":"next","metrics":["selectedCount"]}]},date(2026,4,1),settings={})

def test_expressive_primitives_use_generic_relations():
    project={"objects":{"a":{"title":"A"},"b":{"title":"B"}},"relations":[{"id":"ab","from":{"object":"a"},"to":{"object":"b"}}]}
    placements={"a":{"at":date(2026,4,1)},"b":{"at":date(2026,4,3)}}
    view={"body":{"selection":{"include":{"types":["point"]}},"ordering":{"by":"plannedStart"},"window":{"marginDays":0},"comparison":{"actual":"optional"}}}; theme={"body":{"roles":{"planned":{}},"values":{}}}
    projection=build_review_projection(project,placements,view,None,{"body":{"rules":[]}},theme)
    svg=render_table_timeline_svg("X",projection,project,view,theme,{"sourceMetadata","accessibleText","semanticRoles","marker","tableSemantics","hierarchicalAxis"},{"constraints":{"connectors":"obstacle-aware"}})
    assert 'axis-quarter' in svg and 'routed-connector' in svg
