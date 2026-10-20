"""Folded point headers participate in outside:omit without losing source edges."""
from datetime import date

import pytest

from chrona.presentation.layout import surface_routes
from tests.integration.test_window_row_admission_render import _parts
from tests.support import synthetic_review as sr


def _folded_case(*, include_visible: bool):
    objects = {
        "gate-a": sr.point("gate-a", date(2026, 2, 12), owner="team"),
        "gate-b": sr.point("gate-b", date(2026, 2, 16), owner="team"),
    }
    if include_visible:
        objects["gate-in"] = sr.point("gate-in", date(2026, 1, 15), owner="team")
    source = sr.project(objects, [
        {"id": "outside-folded", "type": "dependency", "lag": "0d",
         "from": {"object": "gate-a", "endpoint": "at"},
         "to": {"object": "gate-b", "endpoint": "at"}},
    ])
    parts = _parts(lanes=False)
    view = parts["view"]["body"]
    view["rows"]["points"] = "group-header"
    view["grouping"] = {
        "by": {"fieldRole": "responsible"}, "fallback": "hierarchy",
        "missing": "Other", "presentation": "header",
    }
    view["visibility"]["labels"] = {
        "placement": "plot", "content": ["title"], "side": "end", "overflow": "suppress",
    }
    view["window"] = {
        "mode": "explicit", "start": "2026-01-01", "end": "2026-02-01",
        "outside": "omit",
    }
    return source, parts


@pytest.mark.parametrize("include_visible", [False, True], ids=["all-outside", "mixed-group"])
def test_folded_window_omission_keeps_relation_source_identity(tmp_path, monkeypatch, include_visible):
    source, parts = _folded_case(include_visible=include_visible)
    batches = []
    compose = surface_routes.compose_surface_routes

    def capture(context):
        result = compose(context)
        batches.append(result)
        return result

    monkeypatch.setattr("chrona.presentation.layout.surface_route_label_plan.compose_surface_routes", capture)
    rendered = sr.render(tmp_path, source, presentation=parts)

    assert len(batches) == 1
    relation = next(item for item in batches[0].relations if item.source_ref == "relation:id:outside-folded")
    assert relation.suppressed and relation.points == ()
    assert relation.window_suppression_reason in {"row-omission", "outside-window"}
    proofs = (*relation.window_endpoint_absences, *relation.window_row_absences)
    assert {proof.occurrence.object_id for proof in proofs} == {"gate-a", "gate-b"}
    assert all(proof.occurrence.kind.value == "folded" for proof in proofs)
    assert "W_LAYOUT_RELATION_SUPPRESSED" in " ".join(rendered.surface.diagnostics)

    if include_visible:
        assert [group.group_id for group in rendered.surface.groups] == ["team"]
        assert any(item.scene_id == "planned:group-header:team:gate-in"
                   for item in rendered.surface.primitives)
    else:
        assert rendered.surface.groups == ()
        assert not any(item.purpose == "group-header" for item in rendered.surface.primitives)
        assert not any(item.scene_id.startswith("planned:group-header:")
                       for item in rendered.surface.primitives)
