"""Public rendering of the private root-group fallback stays in View/Core scope."""
from datetime import date

from chrona.presentation.model.info_diagnostics import UnboundFieldRole
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
