"""#1298: counter bounds cover a whole generated Project, not just the iterator."""
from collections import Counter
from datetime import date

import pytest

from chrona.presentation.layout import route_search as search
from tests.support import synthetic_review as sr


@pytest.mark.parametrize("relation_count", (0, 10, 50, 200))
def test_generated_project_obeys_the_surface_candidate_bound(tmp_path, monkeypatch, relation_count):
    counts = Counter()
    original_candidates = search.orthogonal_route_candidates
    original_intersects = search._history_segments_intersect
    original_pop = search.heappop

    def candidates(*args, **kwargs):
        counts["generators"] += 1
        yield from original_candidates(*args, **kwargs)

    def intersects(*args):
        counts["history_predicates"] += 1
        return original_intersects(*args)

    def pop(queue):
        entry = original_pop(queue)
        state = entry[-1]
        counts["frontier_pops" if isinstance(state, tuple) and len(state) == 6
               else "graph_pops"] += 1
        return entry

    monkeypatch.setattr(search, "orthogonal_route_candidates", candidates)
    monkeypatch.setattr(search, "_history_segments_intersect", intersects)
    monkeypatch.setattr(search, "heappop", pop)
    source = sr.project({
        "source": sr.span("source", date(2026, 1, 5), 10, owner="a"),
        "target": sr.span("target", date(2026, 2, 2), 10, owner="b"),
    }, [{"id": f"r{index}", "type": "dependency", "lag": "0d",
         "from": {"object": "source", "endpoint": "end"},
         "to": {"object": "target", "endpoint": "start"}}
        for index in range(relation_count)])
    parts = sr.bundle()
    parts["view"] = sr.lane_view(parts["view"])
    rendered = sr.render(tmp_path, source, presentation=parts)
    # One source/target instance per declared relation, including all lane
    # reservation rehearsals and final route/name trials. No timing gate.
    assert counts["generators"] <= 100 * relation_count
    assert counts["frontier_pops"] <= 81920 * relation_count
    assert counts["history_predicates"] <= 20 * relation_count * 4096**2
    if relation_count:
        assert counts["generators"] >= relation_count
    relation_ids = {f"relation:r{index}" for index in range(relation_count)}
    emitted = {primitive.scene_id.split(":", 2)[0] + ":" + primitive.scene_id.split(":", 2)[1]
               for primitive in rendered.surface.primitives
               if primitive.scene_id.startswith("relation:")}
    assert emitted == relation_ids
    assert not [diagnostic for diagnostic in rendered.scene.diagnostics
                if diagnostic.startswith("W_LAYOUT_RELATION_SUPPRESSED:")]
    print(f"Project R={relation_count}: {dict(counts)}")
