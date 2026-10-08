"""The slot heading placement rules (#1064) on plain slots and a stub Theme; nothing reads `examples/`."""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.model import LayoutDecision, Measurement, Rect, SlotHeading
from chrona.presentation.layout.slot_heading import (
    SlotHeadings, complete_slot_headings, content_slot, full_slot, headed_slot_ids, reserve_slot_heading_blocks,
)
from chrona.presentation.layout.sources import MeasuredSources
from chrona.presentation.layout.surface_axis import AxisLabelTierGeometry
from chrona.presentation.layout.surface_quality import SlotPlacement
from chrona.presentation.model.surface_content import AxisTier
from chrona.presentation.model.theme_tokens import TextTreatment

SIZE, LINE = 10, Decimal("1.5")  # a 15 unit line box; the gap under it is 5


class _Font:
    content_identity = "sha256:test"
    ascent, descent, units_per_em = 1000, -200, 1000

    def width(self, content, size, letter_spacing=0, numeric_spacing="proportional"):
        return len(content) * size / 2 + max(0, len(content) - 1) * letter_spacing

    def ensure_numeric_spacing(self, _spacing):
        return None


class _Theme:
    def slot_heading_role(self):
        return "slot-heading"

    def text_treatment(self, _role):
        return TextTreatment("Test", 400, Decimal(SIZE), LINE, Decimal(0), "none", "proportional")


def _request(**content):
    surface = SimpleNamespace(annotations=("a",), notes=("n",), legend_entries=(("k", "v"),),
                              summary=SimpleNamespace(runs=("r",)), slot_heading_text=(),
                              group_details=(), milestones=(), observation_rows=(),
                              axis_tiers=(AxisTier("day", 1, "labels"),))
    for key, value in content.items():
        setattr(surface, key, value)
    return SimpleNamespace(theme_tokens=_Theme(), font_metrics=_Font(), surface_content=surface)


def _slot(source, block, size, inline=600, inline_size=200):
    return SlotPlacement(source, source, Rect(Decimal(inline), Decimal(block), Decimal(inline_size), Decimal(size)))


def _decision(source, heading, node_id=None):
    return LayoutDecision(node_id or source, "slot", Rect(Decimal(0), Decimal(0), Decimal(1), Decimal(1)), source,
                          heading=heading)


def _run(slots, heading, *, source="annotations", request=None):
    by_source = {slot.source_ref: slot for slot in slots}
    return complete_slot_headings(request=request or _request(), slots=by_source,
                                  decisions={source: _decision(source, heading)})


AXIS = _slot("timeline-axis", 100, 50, inline=100, inline_size=400)  # a band from 100 to 150


def test_no_declaration_completes_nothing():
    assert complete_slot_headings(request=_request(), slots={}, decisions={}) == SlotHeadings()


def test_prepared_axis_caption_is_reused_in_global_node_order_without_remeasurement(monkeypatch):
    slots = {"timeline-axis": AXIS, "annotations": _slot("annotations", 100, 400)}
    decisions = {"timeline-axis": _decision("timeline-axis", SlotHeading("Calendar", block="axis-tier")),
                 "annotations": _decision("annotations", SlotHeading("Notes"))}
    own = complete_slot_headings(request=_request(), slots=slots,
                                 decisions={"timeline-axis": decisions["timeline-axis"]})
    assert own.diagnostics == ("I_LAYOUT_SLOT_HEADING_NO_AXIS_TIER:timeline-axis",)
    from chrona.presentation.layout import slot_heading
    original = slot_heading.place_text
    calls = []

    def observed(**kwargs):
        calls.append(kwargs["placement_id"])
        return original(**kwargs)

    monkeypatch.setattr(slot_heading, "place_text", observed)
    result = complete_slot_headings(request=_request(), slots=slots, decisions=decisions,
                                    prepared={"timeline-axis": own})
    assert calls == ["slot-heading:annotations"]
    assert [text.placement_id for text in result.text] == [
        "slot-heading:annotations", "slot-heading:timeline-axis"]
    assert result.text[-1] is own.text[0]
    assert result.reserved("timeline-axis") == own.reserved("timeline-axis")
    assert result.diagnostics == own.diagnostics


def test_top_puts_the_line_at_the_slot_start_and_reserves_the_line_and_its_gap():
    result = _run([_slot("annotations", 100, 400)], SlotHeading("Notes"))

    (text,) = result.text
    assert text.placement_id == "slot-heading:annotations" and text.slot_id == "annotations"
    assert text.bounds.block == 100 and text.bounds.block_size == 15
    assert result.reserved("annotations") == 20  # 15 line + 5 gap
    assert result.reserved("legend") == 0


def test_header_row_centres_the_line_in_the_band_and_content_starts_below_the_band():
    result = _run([_slot("annotations", 100, 400), AXIS], SlotHeading("Notes", block="header-row"))

    (text,) = result.text
    assert text.bounds.block == Decimal("117.5")  # (150 + 100) / 2 - 7.5
    assert result.reserved("annotations") == 50  # the band's bottom, not the line plus gap


def test_header_row_without_a_band_beside_the_slot_is_top_with_a_record():
    below = _slot("timeline-axis", 0, 50, inline=100, inline_size=400)  # ends before the slot starts
    result = _run([_slot("annotations", 100, 400), below], SlotHeading("Notes", block="header-row"))

    assert result.text[0].bounds.block == 100 and result.reserved("annotations") == 20
    assert result.diagnostics == ("I_LAYOUT_SLOT_HEADING_NO_HEADER_ROW:annotations",)


def test_the_caption_stays_inside_a_slot_shorter_than_the_band_centre_allows():
    short = _slot("annotations", 140, 60)  # the band centre would put the line at 117.5, above the slot
    result = _run([short, AXIS], SlotHeading("Notes", block="header-row"))

    assert result.text[0].bounds.block == 140  # clamped to the slot's start


@pytest.mark.parametrize("align", ["start", "center", "end"])
def test_align_sets_the_inline_origin(align):
    (text,) = _run([_slot("annotations", 100, 400)], SlotHeading("Notes", align=align)).text

    width = 5 * SIZE / 2  # five characters of half an em
    assert text.baseline[0] == {"start": 600, "center": 600 + (200 - width) / 2, "end": 600 + 200 - width}[align]


def test_a_slot_too_short_or_without_area_draws_nothing_and_reserves_nothing():
    for slot in (_slot("annotations", 100, 20), _slot("annotations", 100, 400, inline_size=0)):
        result = _run([slot], SlotHeading("Notes"))
        assert result.text == () and result.reserved("annotations") == 0
        assert result.diagnostics == ("I_LAYOUT_SLOT_HEADING_OMITTED:annotations:too-small",)


@pytest.mark.parametrize(("source", "content"), [
    ("annotations", {"annotations": ()}), ("notes", {"notes": ()}), ("legend", {"legend_entries": ()}),
    ("summary", {"summary": SimpleNamespace(runs=())})])
def test_a_source_without_content_draws_no_caption(source, content):
    request = _request(**content)
    slot = _slot(source, 100, 400)
    result = _run([slot], SlotHeading("Caption"), source=source, request=request)

    assert result.text == () and result.reserved(source) == 0
    assert result.diagnostics == (f"I_LAYOUT_SLOT_HEADING_OMITTED:{source}:no-content",)

    baseline = Measurement(Decimal(10), Decimal(20), Decimal(40), Decimal(10), Decimal(20), Decimal(30),
                           Decimal(7), Decimal(9))
    measured = MeasuredSources({source: baseline}, {}, {})
    resolved = SimpleNamespace(profile={"root": {"kind": "slot", "source": source,
                                                    "blockSize": "content", "heading": {"text": "Caption"}}})
    unchanged = reserve_slot_heading_blocks(measured, resolved, _Theme(), content=request.surface_content)
    assert unchanged.measurements[source] == baseline
    assert unchanged.measurements[source].first_baseline == baseline.first_baseline
    assert unchanged.measurements[source].last_baseline == baseline.last_baseline


@pytest.mark.parametrize(("source", "field"), [("group-details", "group_details"),
    ("milestones", "milestones"), ("observations", "observation_rows")])
def test_detail_presence_is_shared_by_measurement_and_completion(source, field):
    slot = _slot(source, 100, 400)
    heading = SlotHeading("Detail")
    measured = MeasuredSources({source: Measurement(*(Decimal(10) for _ in range(6)))}, {}, {})
    resolved = SimpleNamespace(profile={"root": {"kind": "slot", "source": source,
                                                "blockSize": "content", "heading": {"text": "Detail"}}})
    empty = _request(**{field: ()})
    assert _run([slot], heading, source=source, request=empty).text == ()
    assert reserve_slot_heading_blocks(measured, resolved, _Theme(), content=empty.surface_content) is measured
    present = _request(**{field: ("entry",)})
    assert _run([slot], heading, source=source, request=present).reserved(source) == 20
    assert reserve_slot_heading_blocks(measured, resolved, _Theme(), content=present.surface_content
                                      ).measurements[source].preferred_block == 30


@pytest.mark.parametrize(("tiers", "draws"), [((), False), ((AxisTier("day", 1, "labels"),), True)])
def test_timeline_axis_presence_is_shared_by_measurement_and_completion(tiers, draws):
    slot = _slot("timeline-axis", 100, 400)
    heading = SlotHeading("Calendar")
    request = _request(axis_tiers=tiers)
    measured = MeasuredSources({"timeline-axis": Measurement(*(Decimal(10) for _ in range(6)))}, {}, {})
    resolved = SimpleNamespace(profile={"root": {"kind": "slot", "source": "timeline-axis",
                                                  "blockSize": "content", "heading": {"text": "Calendar"}}})

    result = _run([slot], heading, source="timeline-axis", request=request)
    updated = reserve_slot_heading_blocks(measured, resolved, _Theme(), content=request.surface_content)
    if draws:
        assert len(result.text) == 1 and result.reserved("timeline-axis") == 20
        assert updated.measurements["timeline-axis"].preferred_block == 30
    else:
        assert result.text == () and result.reserved("timeline-axis") == 0
        assert result.diagnostics == ("I_LAYOUT_SLOT_HEADING_OMITTED:timeline-axis:no-content",)
        assert updated is measured


def test_full_slot_restores_the_caption_around_a_translated_content_viewport():
    slot = _slot("milestones", 100, 80)
    completed = _slot("milestones", 300, 90)
    assert full_slot(slot, completed, Decimal(20)).bounds == Rect(
        Decimal(600), Decimal(280), Decimal(200), Decimal(110))


def test_a_caption_wider_than_the_slot_is_cut_and_recorded():
    result = _run([_slot("annotations", 100, 400, inline_size=40)], SlotHeading("A long caption"))

    (text,) = result.text
    assert text.content.endswith("…") and text.overflow == "ellipsized" and text.source_content == "A long caption"
    assert [item.code for item in result.warnings] == ["W_LAYOUT_TEXT_ELLIPSIZED"]


def test_selected_copy_is_measured_and_ellipsized_with_its_source_retained():
    result = _run([_slot("annotations", 100, 400, inline_size=40)], SlotHeading("Notes"),
                  request=_request(slot_heading_text=(("annotations", "A long selected caption"),)))
    (text,) = result.text
    assert text.content.endswith("…") and text.source_content == "A long selected caption"
    assert text.overflow == "ellipsized" and result.reserved("annotations") == 20


def test_heading_targets_include_optional_profile_slots_without_a_manifest_decision():
    node = {"id": "optional-caption", "kind": "slot", "priority": "optional",
            "source": "annotations", "heading": {"text": "Notes"}}
    root = {"kind": "column", "id": "root", "children": [node,
            {"kind": "slot", "id": "headless", "source": "notes"}]}
    resolved = SimpleNamespace(profile={"root": root}, content_hash="unchanged")
    assert headed_slot_ids(resolved) == frozenset({"optional-caption"})
    assert resolved.content_hash == "unchanged" and node["heading"] == {"text": "Notes"}


def _tier(index, top, baseline):
    return AxisLabelTierGeometry(index, Rect(Decimal(100), Decimal(top), Decimal(400), Decimal(20)), baseline)


def test_axis_tier_caption_uses_completed_upper_baseline_and_reserves_the_whole_band():
    slot = _slot("annotations", 100, 400)
    result = complete_slot_headings(request=_request(), slots={"annotations": slot, "timeline-axis": AXIS},
        decisions={"annotations": _decision("annotations", SlotHeading("Notes", block="axis-tier"))},
        axis_label_tiers=(_tier(5, 125, 140.0), _tier(2, 100, 113.75)))
    assert result.text[0].baseline[1] == 113.75
    assert result.reserved("annotations") == 50 and result.diagnostics == ()


@pytest.mark.parametrize(("axis", "tiers"), [(AXIS, ()), (None, (_tier(0, 100, 110.0),)),
    (AXIS, (_tier(0, 100, 105.0),)), (_slot("timeline-axis", 600, 50), (_tier(0, 600, 610.0),))])
def test_incompatible_axis_tier_falls_back_to_top_with_a_record(axis, tiers):
    slots = {"annotations": _slot("annotations", 100, 400)}
    if axis is not None:
        slots["timeline-axis"] = axis
    result = complete_slot_headings(request=_request(), slots=slots,
        decisions={"annotations": _decision("annotations", SlotHeading("Notes", block="axis-tier"))},
        axis_label_tiers=tiers)
    assert result.text[0].baseline[1] == 110.0
    assert result.reserved("annotations") == 20
    assert result.diagnostics == ("I_LAYOUT_SLOT_HEADING_NO_AXIS_TIER:annotations",)


def test_an_absent_slot_has_no_caption():
    result = _run([], SlotHeading("Notes"))
    assert result.text == () and result.reserved("annotations") == 0 and result.diagnostics == ()


def test_the_content_viewport_starts_below_the_caption_and_the_full_slot_is_restored():
    slot = _slot("annotations", 100, 400)
    viewport = content_slot(slot, Decimal(20))

    assert viewport.bounds == Rect(Decimal(600), Decimal(120), Decimal(200), Decimal(380))
    assert content_slot(slot, Decimal(0)) is slot
    grown = content_slot(slot, Decimal(20))  # content completed taller than the slot allowed
    grown = SlotPlacement(grown.slot_id, grown.source_ref, Rect(grown.bounds.inline, grown.bounds.block,
                                                                 grown.bounds.inline_size, Decimal(500)))
    assert full_slot(slot, grown, Decimal(20)).bounds == Rect(Decimal(600), Decimal(100), Decimal(200), Decimal(520))
    assert full_slot(slot, content_slot(slot, Decimal(20)), Decimal(20)).bounds == slot.bounds


def test_a_content_sized_slot_measures_the_caption_in_and_others_do_not():
    def measure(block):
        return Measurement(Decimal(10), Decimal(20), Decimal(40), Decimal(block), Decimal(block) * 2, Decimal(block) * 3,
                           Decimal(7), Decimal(9))

    measured = MeasuredSources({"legend": measure(10), "notes": measure(10)}, {}, {})
    resolved = SimpleNamespace(profile={"root": {"kind": "column", "children": [
        {"kind": "slot", "source": "legend", "blockSize": "content", "heading": {"text": "Key"}},
        {"kind": "slot", "source": "notes", "blockSize": "fill", "heading": {"text": "Notes"}}]}})

    result = reserve_slot_heading_blocks(measured, resolved, _Theme(), content=_request().surface_content)

    legend = result.measurements["legend"]
    assert (legend.min_block, legend.preferred_block, legend.max_block) == (30, 40, 50)  # each plus 20
    assert (legend.first_baseline, legend.last_baseline) == (27, 29)
    assert result.measurements["notes"] == measured.measurements["notes"]  # a filling slot gives from its allocation
    assert reserve_slot_heading_blocks(measured, SimpleNamespace(profile={"root": {"kind": "column", "children": []}}),
                                       _Theme(), content=_request().surface_content) is measured
