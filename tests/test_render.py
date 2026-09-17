from datetime import date

from chrona.render import render_svg
from chrona.scheduler import ScheduleResult


def test_render_svg_projects_placements_without_owning_them():
    project = {
        "project": {"title": "Demo"},
        "objects": {
            "task": {"title": "Build & Test"},
            "gate": {"title": "Release"},
        },
        "relations": [
            {
                "from": {"object": "task", "endpoint": "end"},
                "to": {"object": "gate", "endpoint": "at"},
            }
        ],
    }
    result = ScheduleResult(
        {
            "task": {"start": date(2026, 10, 1), "end": date(2026, 10, 8)},
            "gate": {"at": date(2026, 10, 9)},
        },
        [],
    )

    svg = render_svg(project, result)

    assert '<svg ' in svg
    assert 'Build &amp; Test' in svg
    assert 'marker-end="url(#arrow)"' in svg
    assert '<rect ' in svg
    assert '<circle ' in svg
