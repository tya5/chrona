"""Tests for the solved inline frame used by fixed-membership lane layout."""
from datetime import date
from decimal import Decimal

import pytest

from chrona.presentation.layout.lane_preflight import (
    LaneInlineFrame, lane_inline_frame_for_manifest,
)
from chrona.presentation.layout.model import LayoutDecision, LayoutError, LayoutManifest, Rect


def test_lane_inline_frame_reads_actual_solved_table_and_timeline_bounds():
    manifest = LayoutManifest(
        "profile", "sha256:test", "block", "inline",
        Rect(Decimal(0), Decimal(0), Decimal(200), Decimal(100)),
        (LayoutDecision("table", "slot", Rect(Decimal(0), Decimal(0), Decimal(30), Decimal(40)),
                        source="table"),
         LayoutDecision("timeline", "slot", Rect(Decimal(30), Decimal(0), Decimal(100), Decimal(40)),
                        source="timeline")),
    )

    frame = lane_inline_frame_for_manifest(
        manifest, window=(date(2026, 1, 1), date(2026, 1, 11)))

    assert frame == LaneInlineFrame(Decimal(0), Decimal(30), Decimal(30), Decimal(100), Decimal(10))


@pytest.mark.parametrize(
    ("decisions", "window"),
    [
        ((), (date(2026, 1, 1), date(2026, 1, 11))),
        ((LayoutDecision("table", "slot", Rect(Decimal(0), Decimal(0), Decimal(30), Decimal(40)),
                         source="table"),),
         (date(2026, 1, 1), date(2026, 1, 11))),
        ((LayoutDecision("table", "slot", Rect(Decimal(0), Decimal(0), Decimal(30), Decimal(40)),
                         source="table"),
          LayoutDecision("timeline", "slot", Rect(Decimal(30), Decimal(0), Decimal(100), Decimal(40)),
                         source="timeline")),
         (date(2026, 1, 11), date(2026, 1, 1))),
    ],
)
def test_lane_inline_frame_rejects_missing_slots_and_invalid_window(decisions, window):
    manifest = LayoutManifest(
        "profile", "sha256:test", "block", "inline",
        Rect(Decimal(0), Decimal(0), Decimal(200), Decimal(100)), decisions,
    )

    with pytest.raises(LayoutError, match="E_LAYOUT_LANE_SEED_INVALID"):
        lane_inline_frame_for_manifest(manifest, window=window)
