"""Surface visual advance contract (#592 I3 review finding)."""
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.surface_visuals import CandidateVisualAdvances


def _visual(side: str) -> SimpleNamespace:
    return SimpleNamespace(side=side)


def test_candidate_advances_sum_each_side_from_the_visual_request() -> None:
    advances = CandidateVisualAdvances((
        (_visual("leading"), object(), 12.0, 3.0),
        (_visual("trailing"), object(), 8.0, 2.0),
    ))
    assert advances.leading == pytest.approx(15.0)
    assert advances.trailing == pytest.approx(10.0)


def test_candidate_advances_are_zero_without_visuals() -> None:
    assert CandidateVisualAdvances(()).leading == 0
    assert CandidateVisualAdvances(()).trailing == 0
