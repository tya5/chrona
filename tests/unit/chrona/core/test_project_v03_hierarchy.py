from datetime import date

import pytest

from chrona.core.hierarchy import HierarchyEntry, children_by_parent, normalize_hierarchy
from chrona.core.validation import validate_project
from chrona.scheduling.scheduler import schedule


def _project(objects, relations=()):
    return {
        "version": "timeline/v0.6",
        "project": {"id": "hierarchy"},
        "objects": objects,
        "relations": list(relations),
    }


def _fixed(start="2026-01-01", end="2026-01-02"):
    return {"type": "task", "schedule": {"mode": "fixed-span", "start": start, "end": end}}


@pytest.mark.parametrize(("objects", "diagnostic"), [
    ({"child": _fixed() | {"parent": "missing"}}, "E_PARENT_NOT_FOUND"),
    ({"self": _fixed() | {"parent": "self"}}, "E_SELF_PARENT"),
    ({"a": _fixed() | {"parent": "b"}, "b": _fixed() | {"parent": "a"}}, "E_PARENT_CYCLE"),
    ({"a": _fixed() | {"wbsCode": "1"}, "b": _fixed() | {"wbsCode": "1"}}, "E_DUPLICATE_WBS_CODE"),
    ({"rollup": {"type": "group", "schedule": {"mode": "rollup"}}}, "E_ROLLUP_EMPTY"),
    ({"rollup": {"type": "group", "schedule": {"mode": "rollup", "anchor": {"start": "2026-01-01"}}}}, "E_ROLLUP_SCHEDULE"),
])
def test_project_v03_hierarchy_invariants_have_stable_diagnostics(objects, diagnostic):
    assert diagnostic in {item.id for item in validate_project(_project(objects))}


def test_hierarchy_normalization_uses_authored_order_and_explicit_code_only_as_label():
    project = _project({
        "programme": {"type": "group", "wbsCode": "P", "schedule": {"mode": "rollup"}},
        "design": _fixed() | {"parent": "programme"},
        "build": _fixed() | {"parent": "programme", "wbsCode": "build-work"},
        "release": _fixed(),
    })
    assert validate_project(project) == []
    assert normalize_hierarchy(project) == (
        HierarchyEntry("programme", None, 0, ("programme",), "P"),
        HierarchyEntry("design", "programme", 1, ("programme", "design"), "1.1"),
        HierarchyEntry("build", "programme", 1, ("programme", "build"), "build-work"),
        HierarchyEntry("release", None, 0, ("release",), "2"),
    )
    assert children_by_parent(normalize_hierarchy(project)) == {
        "programme": ("design", "build"), "design": (), "build": (), "release": (),
    }


def test_rollup_envelope_is_derived_after_children_and_can_be_a_dependency_endpoint():
    project = _project(
        {
            "programme": {"type": "group", "schedule": {"mode": "rollup"}},
            "early": _fixed("2026-01-02", "2026-01-04") | {"parent": "programme"},
            "late": _fixed("2026-01-05", "2026-01-09") | {"parent": "programme"},
            "next": {"type": "task", "schedule": {"mode": "scheduled", "amount": "2d"}},
        },
        [{"type": "dependency", "from": {"object": "programme", "endpoint": "end"},
          "to": {"object": "next", "endpoint": "start"}, "lag": "1d"}],
    )
    result = schedule(project)
    assert result.ok
    assert result.placements["programme"] == {"start": date(2026, 1, 2), "end": date(2026, 1, 9)}
    assert result.placements["next"] == {"start": date(2026, 1, 10), "end": date(2026, 1, 12)}
