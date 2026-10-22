"""#497: a content-sized legend is as wide as its widest entry, up to its container, and any ellipsis is reported.

Rendered end to end through the packaged `control-room-dark` bundle with a Project built in
`tests/support/synthetic_review.py` and a sidebar added to the bundle's Layout Profile. No `examples/`
input: a corpus edit cannot change what these tests prove.
"""
from __future__ import annotations

from datetime import date

import pytest

from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr

OWNERS = ("assembly-integration-and-test", "ground", "launch-and-range")
LONGEST = "legend:scale:series:assembly-integration-and-test"


def _parts(side: int, overflow: str = "ellipsize-with-source") -> dict:
    parts = sr.bundle("control-room-dark")
    legend = {"id": "legend", "kind": "slot", "source": "legend", "inlineSize": "content", "blockSize": "content",
              "place": {"inline": "start", "block": "start", "safety": "safe"}, "priority": "preferred",
              "overflow": overflow}
    sidebar = {"id": "side", "kind": "column", "inlineSize": {"fixed": {"token": "side-width"}},
               "blockSize": "content", "gap": {"token": "spacing.m"}, "padding": {"token": "spacing.none"},
               "alignItems": "start", "justifyContent": "start",
               "place": {"inline": "start", "block": "start", "safety": "safe"}, "children": [legend]}
    parts["layout"]["root"]["children"].insert(1, sidebar)
    parts["layout"]["requiredThemeTokens"] = sorted({*parts["layout"]["requiredThemeTokens"], "side-width"})
    parts["theme"]["body"]["values"]["side-width"] = {"type": "number", "value": side}
    return parts


def _render(tmp_path, side: int, overflow: str = "ellipsize-with-source"):
    objects = {f"t{index}": sr.span(f"t{index}", date(2026, 1, 5 + index), 20, owner=owner)
               for index, owner in enumerate(OWNERS)}
    return sr.render(tmp_path, sr.project(objects), presentation=_parts(side, overflow))


def _legend(rendered):
    slot = next(item for item in rendered.surface.slots if item.source == "legend")
    labels = {node.scene_id: node for node in rendered.surface.primitives if node.scene_id.startswith("legend:")}
    return slot, labels


def _ellipsis_warnings(rendered):
    return [item for item in rendered.surface.fit_warnings if item.code == "W_LAYOUT_TEXT_ELLIPSIZED"]


def test_a_roomy_sidebar_gives_the_legend_exactly_its_widest_entry_and_nothing_is_ellipsized(tmp_path):
    rendered = _render(tmp_path, 600)
    slot, labels = _legend(rendered)

    assert len(labels) == 3
    assert not any(node.text.endswith("…") for node in labels.values())
    longest = labels[LONGEST]
    # The slot is the swatch, the gap and the widest drawn label: the label ends where the slot ends.
    assert slot.bounds[0] + slot.bounds[2] == pytest.approx(longest.bounds[0] + longest.bounds[2])
    assert not _ellipsis_warnings(rendered)
    assert not any(item.startswith("W_LAYOUT_TEXT_ELLIPSIZED") for item in rendered.scene.diagnostics)


def test_a_narrow_sidebar_wraps_legend_labels_without_losing_source_text(tmp_path):
    (tmp_path / "narrow").mkdir()
    narrow = _render(tmp_path / "narrow", 120)
    slot, labels = _legend(narrow)

    # The outer sidebar remains fixed at 120; the legend box encloses its
    # indivisible hyphenated names and reports the resulting track shortage.
    assert slot.bounds[2] > 120.0
    expected = {
        "legend:scale:series:assembly-integration-and-test": "assembly-integration-and-test",
        "legend:scale:series:ground": "ground",
        "legend:scale:series:launch-and-range": "launch-and-range",
    }
    assert set(labels) == set(expected)
    for key, source in expected.items():
        assert source in labels[key].text.replace("\n", " ")
    assert not any(node.text.endswith("…") for node in labels.values())
    assert not _ellipsis_warnings(narrow)
    # The two long hyphenated names are indivisible under the shared line breaker;
    # Layout retains their complete text and names the actual inline shortage.
    overflow = {item.placement_id: item for item in narrow.surface.fit_warnings
                if item.code == "W_LAYOUT_VISIBLE_OVERFLOW" and item.failure_kind == "legend-text"}
    assert set(overflow) == {LONGEST, "legend:scale:series:launch-and-range"}
    for key, warning in overflow.items():
        assert warning.source_ref == key.removeprefix("legend:")
        assert warning.required_inline > warning.available_inline
    track_warning = next(item for item in narrow.surface.fit_warnings
                         if item.code == "W_LAYOUT_VISIBLE_OVERFLOW" and item.failure_kind == "layout-track")
    assert track_warning.required_inline > 120
    assert not any(item.startswith("W_SCENE_TEXT_SLOT_ESCAPE") for item in narrow.scene.diagnostics)


def test_a_legend_that_does_not_shrink_grows_past_its_container_and_is_not_ellipsized(tmp_path):
    rendered = _render(tmp_path, 120, "visible-overflow")
    slot, labels = _legend(rendered)

    assert slot.bounds[2] > 120.0
    assert not any(node.text.endswith("…") for node in labels.values())
    assert not _ellipsis_warnings(rendered)


def _failure(tmp_path, *, break_metric: bool, break_layout: bool) -> str:
    parts = sr.bundle("control-room-dark")
    if break_metric:
        del parts["theme"]["body"]["metrics"]["timeline.dayWidth"]
    if break_layout:
        del parts["theme"]["body"]["values"]["spacing.l"]
    with pytest.raises(RenderFailed) as error:
        sr.render(tmp_path, sr.project({"t": sr.span("t", date(2026, 1, 5), 20)}), presentation=parts)
    return error.value.code


def test_the_layout_profile_is_still_resolved_after_measurement_for_error_precedence(tmp_path):
    # Measuring the legend needs the resolved Layout Profile, so it is resolved first; an error in it is
    # raised only after measurement, so a document with both kinds of error reports what it always did.
    for name in ("metric", "layout", "both"):
        (tmp_path / name).mkdir()

    assert _failure(tmp_path / "metric", break_metric=True, break_layout=False) == "E_LAYOUT_METRIC_REQUIRED"
    assert _failure(tmp_path / "layout", break_metric=False, break_layout=True) == "E_LAYOUT_TOKEN_REQUIREMENT_UNAVAILABLE"
    assert _failure(tmp_path / "both", break_metric=True, break_layout=True) == "E_LAYOUT_METRIC_REQUIRED"
