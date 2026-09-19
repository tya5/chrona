from datetime import date
from chrona.review_svg import build_review_projection

def test_review_projection_keeps_actual_independent_and_marks_variance():
    project={"objects":{"fw":{"title":"FW"},"gate":{"title":"Gate"}}}
    placements={"fw":{"start":date(2026,4,1),"end":date(2026,4,10)},"gate":{"at":date(2026,4,12)}}
    view={"body":{"selection":{"include":{"types":["span","point"]}},"ordering":{"by":"plannedStart"},"window":{"marginDays":2},"comparison":{"actual":"required"}}}
    actual={"body":{"observations":[{"id":"fw-1","sequence":1,"projectObjectId":"fw","actual":{"finish":"2026-04-13"}},{"id":"unknown","sequence":1,"externalIdentity":{"key":"x"},"actual":{"finish":"2026-04-13"}}]}}
    style={"body":{"rules":[{"when":{"facet":"planned","sourceType":"span"},"addRoles":["planned"]},{"when":{"facet":"actual","sourceType":"span"},"addRoles":["actual"]},{"when":{"facet":"finishDelta","comparisonCategory":"behind"},"addRoles":["variance-behind"]}]}}
    result=build_review_projection(project,placements,view,actual,style,{"body":{"roles":{"planned":{}}}})
    assert result.items[0].finish_delta == 3 and "variance-behind" in result.items[0].roles
    assert result.unmatched_actual_ids == ("unknown",) and result.window == (date(2026,3,30),date(2026,4,14))
