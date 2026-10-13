"""Omission preserves authored source indexes; wording never rewrites identity."""
from datetime import date
import json

from chrona.presentation.contracts.resources import SummaryMetric, SummaryPanelInput, SummaryProfileInput
from chrona.presentation.model.info_diagnostics import UnboundSummarySource
from chrona.presentation.model.projection import ReviewProjection
from chrona.presentation.review.v05_content import normalize_summary_content


def _projection():
    return ReviewProjection((), (date(2026, 1, 1), date(2026, 2, 1)), (), ())


def test_unbound_inline_metrics_do_not_renumber_surviving_sources():
    summary = SummaryProfileInput((
        SummaryPanelInput("empty", None, "figures", (
            SummaryMetric("missing", "Missing", {"slot": "missing"}, "count", None),), "inline"),
        SummaryPanelInput("kept", "Kept", "figures", (
            SummaryMetric("missing", "Missing", {"slot": "missing"}, "count", None),
            SummaryMetric("count", "COUNT", "count.selected", "count", None)), "inline")))
    content = normalize_summary_content(summary, _projection(), None,
                                       omitted_metrics=frozenset({(0, 0), (1, 0)}))
    assert len(content.panels) == 1
    assert [run.placement_id for run in content.panels[0].runs] == [
        "summary:/panels/1/title", "summary:/panels/1/metrics/1/value",
        "summary:/panels/1/metrics/1/label"]


def test_legacy_caption_wording_preserves_metric_identity_and_value():
    summary = SummaryProfileInput((SummaryPanelInput("panel.with.dot", None, "lines",
                                                    (("metric.with.dot", "literal"),)),))
    content = normalize_summary_content(summary, _projection(), None,
                                       summary_wording={"panel.with.dot.metric.with.dot": "Project caption"})
    assert content.panels[0].runs[-1].content == "Project caption: literal"
    assert content.panels[0].runs[-1].placement_id == "summary:panel.with.dot:metric.with.dot"


def test_info_preserves_delimiters_and_unicode_in_admitted_ids():
    fact = UnboundSummarySource("panel;=雪", "metric;=雪", "slot", "slot;=雪")
    code, payload = fact.scene_diagnostic().split(":", 1)
    assert code == "I_SUMMARY_SLOT_UNBOUND"
    assert json.loads(payload) == {"panel": "panel;=雪", "metric": "metric;=雪", "slot": "slot;=雪"}
