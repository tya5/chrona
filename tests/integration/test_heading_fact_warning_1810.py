from datetime import date

from tests.support import synthetic_review as sr
from tests.integration.test_title_ink import _network_parts


def test_missing_heading_facts_keep_empty_copy_and_reach_the_render_warning_ledger(tmp_path):
    parts = sr.bundle("executive-light")
    parts["view"]["body"]["heading"] = {
        "title": "As of {asOf}",
        "subtitle": "Calendar: {calendar}",
    }
    parts["theme"]["body"]["roles"]["subtitle"] = dict(parts["theme"]["body"]["roles"]["heading"])
    project = sr.project({"task": sr.span("task", date(2026, 1, 5), 12)})

    rendered = sr.render(tmp_path, project, presentation=parts)

    warnings = [item for item in rendered.warning_records
                if item.payload.get("code") == "W_PRESENTATION_HEADING_FACT_MISSING"]
    assert [item.payload["diagnostic"] for item in warnings] == [
        'W_PRESENTATION_HEADING_FACT_MISSING:{"fact":"asOf","sourceRef":"/body/heading/title"}',
        'W_PRESENTATION_HEADING_FACT_MISSING:{"fact":"calendar","sourceRef":"/body/heading/subtitle"}',
    ]
    assert [item.payload["severity"] for item in warnings] == ["warning", "warning"]


def test_network_heading_warning_follows_profile_heading_ownership(tmp_path):
    source = sr.project({"task": sr.span("task", date(2026, 1, 5), 12)})

    legacy = _network_parts()
    legacy["view"]["body"]["heading"] = {"title": "As of {asOf}"}
    (tmp_path / "legacy").mkdir()
    legacy_rendered = sr.render(tmp_path / "legacy", source, presentation=legacy)
    assert not any(item.payload.get("code") == "W_PRESENTATION_HEADING_FACT_MISSING"
                   for item in legacy_rendered.warning_records)

    independent = _network_parts()
    independent["view"]["body"]["heading"] = {"title": "As of {asOf}"}
    sr.find_node(independent["layout"], "title")["source"] = "heading.title"
    (tmp_path / "independent").mkdir()
    independent_rendered = sr.render(tmp_path / "independent", source, presentation=independent)
    warnings = [item for item in independent_rendered.warning_records
                if item.payload.get("code") == "W_PRESENTATION_HEADING_FACT_MISSING"]
    assert [item.payload["diagnostic"] for item in warnings] == [
        'W_PRESENTATION_HEADING_FACT_MISSING:{"fact":"asOf","sourceRef":"/body/heading/title"}',
    ]
