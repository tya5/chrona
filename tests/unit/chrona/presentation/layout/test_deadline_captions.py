"""Two-anchor optional-caption geometry, independently of domain fixtures."""
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import pytest

from chrona.presentation.layout import deadline_captions as dc
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.surface_quality import TextPlacement
from chrona.presentation.model.diagnostic_sources import DiagnosticSubject


@pytest.fixture
def measured(monkeypatch):
    calls = []
    def measure(**values):
        calls.append(values)
        return TextPlacement(values["placement_id"], values["source_ref"], values["content"],
                             Rect(Decimal(0), Decimal(-8), Decimal(20), Decimal(10)), values["typography_role"],
                             baseline=(0, 0), font_size=12, font_family="Face", font_asset_identity="sha256:face",
                             slot_id="timeline", semantic_id="deadlineCaption")
    monkeypatch.setattr(dc, "place_text", measure)
    return calls


def _anchor(**changes):
    return replace(dc.DeadlineCaptionAnchor("deadline-caption:x", "x", "planned:x", "3 days late",
                    55, 70, 50, 2, (DiagnosticSubject.project_object("x"),)), **changes)


def _place(anchors, obstacles=None, shapes=()):
    return dc.place_deadline_captions(anchors=anchors, shapes=shapes,
        plot=Rect(Decimal(0), Decimal(0), Decimal(100), Decimal(100)),
        obstacles=obstacles or SurfaceObstacleIndex(),
        theme_tokens=SimpleNamespace(has_role=lambda _role: False), font_metrics=object())


def test_right_candidate_measures_once_and_completes_baseline_and_provenance(measured):
    result = _place((_anchor(),))
    placed, = result.text
    assert placed.bounds == Rect(Decimal(75), Decimal(45), Decimal(20), Decimal(10))
    assert placed.baseline == (75, 53)
    assert placed.subjects == (DiagnosticSubject.project_object("x"),)
    assert placed.host_placement_id is None
    assert placed.font_asset_identity == "sha256:face" and len(measured) == 1


def test_overflow_switches_anchor_to_other_side_of_tick(measured):
    result = _place((_anchor(run_end=98),))
    assert result.text[0].bounds.inline == 30  # 55 - (2 margin + 3 gap) - 20 width
    assert result.info == ()


def test_collision_also_switches_anchor_without_mutating_existing_inventory(measured):
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("existing-label", "text", "timeline", ObstacleRect(74, 44, 99, 56)))
    before = obstacles.all()
    result = _place((_anchor(),), obstacles)
    assert result.text[0].bounds.inline == 30
    assert obstacles.all() == before


def test_both_candidates_blocked_count_host_occurrences_and_keep_subjects(measured):
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("host-and-ink", "mark", "timeline", ObstacleRect(0, 0, 100, 100)))
    result = _place((_anchor(), _anchor(placement_id="deadline-caption:second")), obstacles)
    assert not result.text and result.info[0].count == 2
    assert result.info[0].code == "I_LAYOUT_DEADLINE_CAPTION_DROPPED"
    assert result.provenance[0].subjects == (DiagnosticSubject.project_object("x"),)


def test_prior_caption_is_an_obstacle_for_next_host_occurrence(measured):
    result = _place((_anchor(), _anchor(placement_id="deadline-caption:second"),
                     _anchor(placement_id="deadline-caption:third")))
    assert [item.bounds.inline for item in result.text] == [75, 30]
    assert result.info[0].count == 1


def test_full_text_block_must_fit_plot_and_wobble_margin_is_not_discarded(measured):
    assert not _place((_anchor(run_y=2),)).text
    result = _place((_anchor(stroke_margin=6),))
    assert result.text[0].bounds.inline == 79


def test_absent_caption_does_not_read_theme_or_measure(measured):
    assert dc.place_deadline_captions(anchors=(), shapes=(), plot=None, obstacles=None,
                                      theme_tokens=None, font_metrics=None) == dc.DeadlineCaptionBatch()
    assert measured == []
