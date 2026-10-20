"""A known inline legend width completes its row block for fixed and auto canvases."""
from datetime import date
from decimal import Decimal
from xml.etree import ElementTree

from chrona.presentation.layout import surface_render_plan as planner
from chrona.presentation.layout.sources import SourceInput, SourceTextRun, measure_sources
from chrona.usecases import render_review as usecase
from tests.support import synthetic_review as sr
from tests.unit.chrona.presentation.layout.test_sources import theme as measuring_theme


ROLES = ("planned", "actual", "gate")
LABELS = {"planned": "Planned", "actual": "Actual", "gate": "Gate"}


def _render(tmp_path, monkeypatch, *, width, host_block, mark_size=None):
    parts = sr.bundle("executive-light")
    legend = sr.find_node(parts["layout"], "legend")
    legend.update(direction="inline", overflow="ellipsize-with-source", inlineSize="fill",
                  blockSize="content",
                  itemMinInlineSize={"token": "legend-item-min"})
    added_tokens = {"legend-item-min"}
    if host_block is not None:
        added_tokens.add("legend-side-block")
    parts["layout"]["requiredThemeTokens"] = sorted({*parts["layout"]["requiredThemeTokens"], *added_tokens})
    parts["theme"]["body"]["values"]["legend-item-min"] = {"type": "number", "value": 40}
    legend_size = parts["theme"]["body"]["roles"]["legend"]["fontSize"]
    parts["theme"]["body"]["values"][legend_size]["value"] = 10

    footer_parent = next(item for item in parts["layout"]["root"]["children"]
                         if any(child.get("id") == "legend" for child in item.get("children", ())))
    footer_parent["children"] = [child for child in footer_parent["children"] if child.get("id") != "legend"]
    sidebar = {"id": "side", "kind": "column", "inlineSize": {"fixed": {"token": "legend-side"}},
               "blockSize": ("content" if host_block is None else {"fixed": {"token": "legend-side-block"}}),
               "gap": {"token": "spacing.m"}, "padding": {"token": "spacing.none"},
               "alignItems": "start", "justifyContent": "start",
               "place": {"inline": "start", "block": "start", "safety": "safe"}, "children": [legend]}
    parts["layout"]["root"]["children"].insert(1, sidebar)
    parts["layout"]["requiredThemeTokens"] = sorted({*parts["layout"]["requiredThemeTokens"], "legend-side"})
    parts["theme"]["body"]["values"].update({
        "legend-side": {"type": "number", "value": width},
        "legend-side-block": {"type": "number", "value": host_block or 16},
    })
    if mark_size is not None:
        token = parts["theme"]["body"]["metrics"]["timeline.mark.blockSize"]
        parts["theme"]["body"]["values"][token]["value"] = mark_size

    project = sr.with_calendar(sr.project({
        "task": sr.span("task", date(2026, 2, 2), 30),
        "gate": sr.point("gate", date(2026, 3, 9)),
    }))
    detail = {"version": "chrona/review-detail-profile/v0.1", "id": "known-width-legend",
              "body": {"legend": [{"role": role, "label": LABELS[role]} for role in ROLES]}}
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "legend-actual",
              "body": {"asOf": "2026-03-15", "observations": [
                  {"id": "task-observed", "sequence": 1, "projectObjectId": "task",
                   "actual": {"start": "2026-02-02", "finish": "2026-02-28"}},
              ]}}
    captured = []
    original = planner.prepare_surface_render_plan

    def observe(value):
        result = original(value)
        captured.append(result)
        return result

    monkeypatch.setattr(usecase, "prepare_surface_render_plan", observe)
    rendered = sr.render(tmp_path, project, presentation=parts, detail=detail, actual=actual,
                         viewport=(1200, None) if host_block is None else (1200, 800))
    assert len(captured) == 1
    return rendered, captured[0]


def _legend_warning(rendered):
    return [warning for warning in rendered.surface.fit_warnings
            if warning.code == "W_LAYOUT_VISIBLE_OVERFLOW"]


def _svg_text(rendered):
    root = ElementTree.fromstring(rendered.artifact.content)
    return tuple("".join(node.itertext()) for node in root.iter() if node.tag.endswith("text"))


def test_source_minimum_includes_a_taller_declared_inline_row_block():
    class Metrics:
        content_identity = "sha256:known-width-test"

        def width(self, value, size):
            return len(value) * size / 2

        def baseline(self, top, size, line_height):
            return top + size

    source = SourceInput(runs=(SourceTextRun("Legend entry", "legend"),), run_flow="line",
                         row_block=Decimal(30))
    measured = measure_sources({"legend": source}, measuring_theme(), font_metrics=Metrics())

    assert measured.measurements["legend"].min_block == 30


def test_fixed_canvas_completes_known_one_row_height_without_false_host_overflow(tmp_path, monkeypatch):
    rendered, plan = _render(tmp_path, monkeypatch, width=1100, host_block=16)
    legend = plan.measured.measurements["legend"]
    assert legend.preferred_block == legend.min_block == 16
    assert not _legend_warning(rendered)
    assert plan.viewport[1] == 800
    drawn = _svg_text(rendered)
    assert all(label in drawn for label in LABELS.values())


def test_fixed_canvas_completes_wrapped_rows_and_retains_real_shortage(tmp_path, monkeypatch):
    rendered, plan = _render(tmp_path, monkeypatch, width=100, host_block=16)

    assert plan.measured.measurements["legend"].preferred_block > 16
    assert len(_legend_warning(rendered)) == 1, rendered.surface.fit_warnings
    assert _legend_warning(rendered)[0].required_block > _legend_warning(rendered)[0].available_block
    assert plan.viewport[1] == 800


def test_known_swatch_height_can_increase_completed_row_block(tmp_path, monkeypatch):
    rendered, plan = _render(tmp_path, monkeypatch, width=1100, host_block=16, mark_size=30)

    assert plan.measured.measurements["legend"].min_block >= 30
    assert plan.measured.measurements["legend"].preferred_block >= 30
    assert _legend_warning(rendered), rendered.surface.fit_warnings


def test_draft_auto_uses_the_same_completed_rows_for_canvas_height(tmp_path, monkeypatch):
    rendered, plan = _render(tmp_path, monkeypatch, width=1100, host_block=None)

    assert plan.measured.measurements["legend"].preferred_block == 16
    assert not _legend_warning(rendered)
    assert plan.viewport[1] < 900
