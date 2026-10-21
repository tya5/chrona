"""A count figure can be restricted by object type or temporal kind, and a group count can leave out the
unassigned group (#1880 row 1). Synthetic Project: no `examples/` input."""
from __future__ import annotations

from copy import deepcopy
from datetime import date

import pytest

from chrona.usecases.render_review import RenderRejected
from tests.integration.test_derived_figures import _metric, _parts, _summary, _texts
from tests.support import synthetic_review as sr


def _source() -> dict:
    objects = {
        "t1": sr.span("t1", date(2026, 1, 5), 10, owner="a"),
        "t2": sr.span("t2", date(2026, 1, 8), 10, owner="b"),
        "t3": sr.span("t3", date(2026, 1, 12), 10, owner="b"),
        "orphan": sr.span("orphan", date(2026, 1, 14), 10),
        "g1": sr.point("g1", date(2026, 2, 2), owner="a"),
    }
    del objects["orphan"]["fields"]["owner"]
    source = sr.project(objects)
    source["fieldRoles"] = {"responsible": "owner"}
    return source


FIGURES = (
    {"id": "all", "kind": "count", "source": "selected"},
    {"id": "tasks", "kind": "count", "source": "selected", "objectTypes": ["task"]},
    {"id": "gates", "kind": "count", "source": "selected", "objectTypes": ["gate"]},
    {"id": "spans", "kind": "count", "source": "selected", "temporalKind": "span"},
    {"id": "points", "kind": "count", "source": "selected", "temporalKind": "point"},
    {"id": "both", "kind": "count", "source": "selected", "objectTypes": ["task"], "temporalKind": "point"},
    {"id": "sections", "kind": "count", "source": "groups"},
    {"id": "assigned", "kind": "count", "source": "groups", "excludeUnassigned": True},
)


def _values(tmp_path, grouping, figures=FIGURES) -> dict[str, str]:
    parts = _parts(*figures)
    parts["view"]["body"]["grouping"] = grouping
    summary = _summary(*(_metric(item["id"], metric_id=item["id"]) for item in figures))
    texts = _texts(sr.render(tmp_path, _source(), presentation=parts, summary=summary))
    return {key.split(":")[2]: value for key, value in texts.items() if key.endswith(":value")}


@pytest.mark.parametrize("grouping", [
    {"by": "field", "field": "owner", "missing": "Unassigned"},
    {"by": {"fieldRole": "responsible"}, "fallback": "objectType", "missing": "Unassigned"},
], ids=["field", "role"])
def test_a_count_figure_can_be_restricted(tmp_path, grouping):
    values = _values(tmp_path, grouping)
    assert values["all"] == "5"
    assert (values["tasks"], values["gates"]) == ("4", "1")
    assert (values["spans"], values["points"], values["both"]) == ("4", "1", "0")
    # Groups a and b, plus the group of the object that has no owner.
    assert values["sections"] == "3"
    assert values["assigned"] == "2"


def test_an_unrestricted_figure_is_unchanged(tmp_path):
    values = _values(tmp_path, {"by": "field", "field": "owner", "missing": "Unassigned"}, FIGURES[:1] + FIGURES[6:7])
    assert values == {"all": "5", "sections": "3"}


@pytest.mark.parametrize(("figure", "pointer"), [
    ({"id": "n", "kind": "count", "source": "placedNotes", "objectTypes": ["task"]}, "/body/figures/0/source"),
    ({"id": "n", "kind": "count", "source": "selected", "excludeUnassigned": True}, "/body/figures/0/excludeUnassigned"),
])
def test_an_inapplicable_restriction_is_refused(tmp_path, figure, pointer):
    parts = _parts(figure, slot=False)
    with pytest.raises(Exception) as caught:
        sr.render(tmp_path, _source(), presentation=deepcopy(parts))
    assert "E_VIEW_FIGURE_INVALID" in str(getattr(caught.value, "code", "")) + str(caught.value)
    assert pointer in str(caught.value) or getattr(caught.value, "source_ref", pointer) == pointer


def test_a_restricted_group_scope_count_counts_the_group_members(tmp_path):
    figures = ({"id": "g", "kind": "count", "source": "selected", "objectTypes": ["task"], "scope": "group"},)
    parts = _parts(*figures, slot=False)
    parts["view"]["body"]["grouping"] = {"by": "field", "field": "owner", "missing": "Unassigned"}
    parts["view"]["body"]["grouping"].update(presentation="header", header={"text": "{title} {figure:g}"})
    rendered = sr.render(tmp_path, _source(), presentation=parts)
    headers = {item.text for item in rendered.surface.primitives if item.scene_id.startswith("group-header")}
    assert any(text.endswith(" 2") for text in headers) and any(text.endswith(" 1") for text in headers)
