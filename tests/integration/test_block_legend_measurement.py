"""Block legend source height encloses actual swatches in fixed/auto SVG (#1830)."""
from datetime import date
from xml.etree import ElementTree

import pytest

from chrona.presentation.layout import surface_render_plan as planner
from chrona.usecases import render_review as usecase
from tests.support import synthetic_review as sr


def _render(directory, monkeypatch, *, auto=False, cramped=False):
    directory.mkdir(parents=True, exist_ok=True)
    parts = sr.bundle()
    legend = sr.find_node(parts["layout"], "legend")
    legend.update(direction="block", inlineSize="fill", blockSize="content",
                  overflow="visible-overflow", gap={"token": "key-gap"})
    legend.pop("itemMinInlineSize", None)
    body = parts["theme"]["body"]
    body["values"].update({"key-gap": {"type": "number", "value": 6},
                           "key-height": {"type": "number", "value": 30}})
    body["roles"]["legend-swatch"] = {"swatchShape": "circle", "swatchBlockSize": "key-height"}
    parts["layout"]["requiredThemeTokens"] = sorted({*parts["layout"]["requiredThemeTokens"], "key-gap"})
    if cramped:
        body["values"]["key-short"] = {"type": "number", "value": 40}
        legend["blockSize"] = {"fixed": {"token": "key-short"}}
        parts["layout"]["requiredThemeTokens"] = sorted({*parts["layout"]["requiredThemeTokens"], "key-short"})
    source = sr.project({"work": sr.span("work", date(2026, 3, 2), 5)})
    detail = {"version": "chrona/review-detail-profile/v0.1", "id": "block-keys", "body": {
        "legend": [{"role": "planned", "label": "Planned work"}, {"role": "actual", "label": "Observed work"}],
    }}
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed", "body": {
        "asOf": "2026-03-10", "observations": [{"id": "work-observed", "sequence": 1,
            "projectObjectId": "work", "actual": {"start": "2026-03-02", "finish": "2026-03-06"}}],
    }}
    plans = []
    prepare = planner.prepare_surface_render_plan

    def capture(request):
        result = prepare(request)
        plans.append(result)
        return result

    monkeypatch.setattr(usecase, "prepare_surface_render_plan", capture)
    rendered = sr.render(directory, source, presentation=parts, detail=detail, actual=actual,
                         viewport=(1200, None if auto else 900))
    return rendered, plans[-1]


@pytest.mark.parametrize("auto", [False, True])
def test_fixed_and_auto_block_legends_reserve_full_rows_in_actual_svg(tmp_path, monkeypatch, auto):
    rendered, plan = _render(tmp_path, monkeypatch, auto=auto)
    measure = plan.measured.measurements["legend"]
    slot = next(slot for slot in rendered.surface.slots if slot.source == "legend")
    swatches = [node for node in rendered.surface.primitives if node.purpose == "legend-swatch"]
    assert len(swatches) == 2
    assert all(node.bounds[3] == pytest.approx(30) for node in swatches)
    assert measure.min_block == measure.preferred_block == 66
    assert slot.bounds[3] == pytest.approx(66)
    assert max(node.bounds[1] + node.bounds[3] for node in swatches) == pytest.approx(slot.bounds[1] + slot.bounds[3])
    assert not [warning for warning in rendered.surface.fit_warnings
                if warning.code == "W_LAYOUT_VISIBLE_OVERFLOW" and warning.source == "legend"]
    root = ElementTree.fromstring(rendered.artifact.content)
    texts = ["".join(node.itertext()) for node in root.iter("{http://www.w3.org/2000/svg}text")]
    assert "Planned work" in texts and "Observed work" in texts
    if not auto:
        assert rendered.surface.canvas_bounds[3] == 900


def test_a_genuinely_short_fixed_block_legend_still_reports_overflow(tmp_path, monkeypatch):
    rendered, plan = _render(tmp_path, monkeypatch, cramped=True)
    assert plan.measured.measurements["legend"].preferred_block == 66
    warnings = [warning for warning in rendered.surface.fit_warnings if warning.code == "W_LAYOUT_VISIBLE_OVERFLOW"]
    assert any(warning.required_block > warning.available_block for warning in warnings)
    # The fixed allocation stays fixed; visible-overflow ink may enlarge the
    # completed Scene canvas envelope, independently of the declared viewport.
    assert plan.viewport[1] == 900
