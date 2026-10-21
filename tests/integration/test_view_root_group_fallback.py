"""Public rendering of the private root-group fallback stays in View/Core scope."""
from copy import deepcopy
from datetime import date
from pathlib import Path

import pytest

from chrona.presentation.model.info_diagnostics import UnboundFieldRole
from chrona.resources import builtin_preset_source_root, safe_load
from tests.support import synthetic_review as sr


def test_unbound_responsible_renders_root_group_headers_without_group_bars(tmp_path):
    project = sr.project({
        "root": {"type": "group", "title": "Root team", "fields": {"label": "Platform"},
                 "schedule": {"mode": "rollup"}},
        "nested": {"type": "group", "title": "Nested team", "parent": "root",
                   "schedule": {"mode": "rollup"}},
        "work": {"type": "task", "title": "Work", "parent": "nested", "fields": {},
                 "schedule": {"mode": "fixed-span", "start": "2026-02-02", "end": "2026-02-06"}},
        "flat": {"type": "gate", "title": "Flat gate", "fields": {},
                 "schedule": {"mode": "fixed-point", "at": "2026-02-10"}},
    })
    parts = sr.bundle("executive-light")
    body = parts["view"]["body"]
    body["selection"]["exclude"]["objectTypes"] = []
    body["grouping"] = {"by": {"fieldRole": "responsible"}, "fallback": "hierarchy",
                        "missing": "Unassigned", "presentation": "header",
                        "header": {"text": "{title} · {secondary}",
                                   "secondary": {"entityField": "label"}}}

    rendered = sr.render(tmp_path, project, presentation=parts)

    labels = {item.text for item in rendered.surface.primitives if item.kind == "Text"}
    assert "Root team · Platform" in labels
    assert "Nested team" not in labels
    assert {"Work", "Flat gate"} <= labels
    assert not any(isinstance(item, UnboundFieldRole) for item in rendered.info_diagnostics)
    assert not any(item.source_ref in {"root", "nested"} and item.purpose == "planned"
                   for item in rendered.surface.primitives)


def test_missing_root_group_secondary_names_the_object_source(tmp_path):
    project = sr.project({
        "root": {"type": "group", "title": "Root", "schedule": {"mode": "rollup"}},
        "work": {"type": "task", "title": "Work", "parent": "root",
                 "schedule": {"mode": "fixed-span", "start": "2026-02-02", "end": "2026-02-06"}},
    })
    parts = sr.bundle("executive-light")
    parts["view"]["body"]["grouping"] = {
        "by": {"fieldRole": "responsible"}, "fallback": "hierarchy",
        "missing": "Unassigned", "presentation": "header",
        "header": {"text": "{title} {secondary}", "secondary": {"entityField": "label"}},
    }
    with pytest.raises(ValueError, match="E_REVIEW_GROUP_HEADER_SECONDARY") as failure:
        sr.render(tmp_path, project, presentation=parts)
    assert "/objects/'root'/fields/'label'=" in str(failure.value)
    assert "/entities/" not in str(failure.value)


def test_shared_design_default_view_uses_the_same_fallback_on_a_synthetic_project(tmp_path):
    project = sr.project({
        "root": {"type": "group", "title": "Root team", "schedule": {"mode": "rollup"}},
        "task": {"type": "task", "title": "Work", "parent": "root", "fields": {"owner": "eng"},
                 "schedule": {"mode": "fixed-span", "start": "2026-02-02", "end": "2026-02-06"}},
    }, responsible_field_role=False)
    preset_root = builtin_preset_source_root("designs/marquee")
    parts = {kind: safe_load(preset_root.joinpath(filename).read_bytes()) for kind, filename in {
        "theme": "theme.yaml", "scheme": "scheme.yaml", "layout": "layout.yaml",
    }.items()}
    generic_view = builtin_preset_source_root("presets/bundles/design-default").joinpath("view.yaml")
    parts["view"] = safe_load(generic_view.read_bytes())

    catalog = Path(__file__).resolve().parents[2] / "src/chrona/resources/icons/chrona-target-parts-v2026-10-09.yaml"
    rendered = sr.render(tmp_path, project, presentation=parts, icon_catalogs=(catalog,),
                         visual_profile="chrona-output/visual/v0.7-svg")

    labels = {item.text for item in rendered.surface.primitives if item.kind == "Text"}
    assert any("root team" in item.casefold() for item in labels)
    unbound_roles = {item.role for item in rendered.info_diagnostics if isinstance(item, UnboundFieldRole)}
    assert "responsible" not in unbound_roles
    assert unbound_roles == set()  # the optional Phase column disappears quietly (#1870)


def test_executive_light_bound_responsible_matches_its_former_direct_owner_grouping(tmp_path):
    project = sr.project({
        "alpha": {"type": "task", "title": "Alpha", "fields": {"owner": "eng"},
                  "schedule": {"mode": "fixed-span", "start": "2026-02-02", "end": "2026-02-06"}},
        "beta": {"type": "gate", "title": "Beta", "fields": {"owner": "ops"},
                  "schedule": {"mode": "fixed-point", "at": "2026-02-10"}},
    })
    project["fieldRoles"] = {"responsible": "owner"}
    parts = sr.bundle("executive-light")
    control = deepcopy(parts)
    control["view"]["body"]["grouping"] = {
        "by": "field", "field": "owner", "missing": "Other",
        "order": {"by": "earliestPlannedStart"}, "presentation": "header",
    }

    (tmp_path / "role").mkdir()
    (tmp_path / "direct").mkdir()
    rendered = sr.render(tmp_path / "role", project, presentation=parts)
    direct = sr.render(tmp_path / "direct", project, presentation=control)

    assert rendered.artifact.content == direct.artifact.content
    assert rendered.surface.primitives == direct.surface.primitives
    assert not any(isinstance(item, UnboundFieldRole) for item in rendered.info_diagnostics)
