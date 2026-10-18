import pytest

from chrona.presentation.layout.labels import (
    LabelCandidateGeometry,
    LabelRect,
    MemberNameAssociation,
    place_label,
    place_member_name,
)


def test_place_label_uses_each_declared_sides_completed_geometry_in_order():
    anchor = LabelRect(40, 40, 10, 10)
    result = place_label(
        anchor, (1, 1), ("above", "end"), bounds=LabelRect(0, 0, 100, 100),
        required=False, overflow="suppress",
        candidate_geometries={
            "above": LabelCandidateGeometry((120, 8), gap=7),
            "end": LabelCandidateGeometry((6, 4), gap=3),
        },
    )

    assert result is not None
    assert result.side == "end"
    assert result.bounds == LabelRect(53, 43, 6, 4)


def test_place_label_inside_candidate_uses_its_own_measured_size():
    anchor = LabelRect(20, 20, 12, 10)
    result = place_label(
        anchor, (1, 1), ("inside", "below"), bounds=LabelRect(0, 0, 100, 100),
        candidate_geometries={
            "inside": LabelCandidateGeometry((8, 4), gap=100),
            "below": LabelCandidateGeometry((50, 20), gap=3),
        },
    )

    assert result is not None
    assert result.side == "inside"
    assert result.bounds == LabelRect(22, 23, 8, 4)


def test_place_label_uses_each_candidates_completed_bounds():
    anchor = LabelRect(10, 40, 10, 10)
    result = place_label(
        anchor, (5, 5), ("above", "end"), bounds=LabelRect(0, 0, 100, 100),
        required=False, overflow="suppress",
        candidate_geometries={
            "above": LabelCandidateGeometry((5, 5), bounds=LabelRect(0, 0, 100, 30)),
            "end": LabelCandidateGeometry((5, 5), bounds=LabelRect(20, 0, 10, 100)),
        },
    )

    assert result is not None
    assert result.side == "end"
    assert result.bounds == LabelRect(20, 42.5, 5, 5)


def test_member_name_uses_candidate_specific_size_gap_and_declared_order():
    anchor = LabelRect(10, 20, 10, 10)
    result = place_member_name(
        anchor, (2, 2), ("end", "start"), bounds=LabelRect(0, 0, 40, 60),
        obstacles=(), gap=0, maximum_end_gap=100,
        candidate_geometries={
            "end": LabelCandidateGeometry((50, 8), gap=4, maximum_end_gap=100),
            "start": LabelCandidateGeometry((5, 6), gap=2, maximum_end_gap=100),
        },
    )

    assert result is not None
    assert result.side == "start"
    assert result.bounds == LabelRect(3, 22, 5, 6)


def test_member_name_uses_candidate_specific_bounds():
    anchor = LabelRect(10, 20, 10, 10)
    result = place_member_name(
        anchor, (2, 2), ("end", "start"), bounds=LabelRect(0, 0, 40, 60),
        obstacles=(), gap=0, maximum_end_gap=100,
        candidate_geometries={
            "end": LabelCandidateGeometry((6, 4), bounds=LabelRect(0, 0, 15, 60)),
            "start": LabelCandidateGeometry((5, 6), bounds=LabelRect(0, 0, 10, 60)),
        },
    )

    assert result is not None
    assert result.side == "start"
    assert result.bounds == LabelRect(5, 22, 5, 6)


def test_member_name_final_own_mark_rung_uses_end_geometry_and_final_association():
    anchor = LabelRect(0, 0, 10, 10)
    host_association = MemberNameAssociation(anchor, 0, 0, 6, 4, 0)
    final_mark = LabelRect(30, 0, 5, 10)
    end_final_association = MemberNameAssociation(final_mark, 0, 0, 6, 4, 1)
    ignored_baseline_association = MemberNameAssociation(LabelRect(80, 80, 5, 5), 0, 0, 1, 1, 0)

    result = place_member_name(
        anchor, (1, 1), ("end",), own_mark_right=30,
        final_association=ignored_baseline_association,
        bounds=LabelRect(0, 0, 100, 100), obstacles=(), gap=9, maximum_end_gap=100,
        association=ignored_baseline_association,
        candidate_geometries={
            "end": LabelCandidateGeometry((6, 4), gap=1, maximum_end_gap=100,
                                           association=host_association,
                                           final_association=end_final_association),
        },
    )

    assert result is not None
    assert result.final_rung
    assert result.side == "end"
    assert result.bounds == LabelRect(31, 3, 6, 4)


def test_visible_end_fallback_uses_end_geometry_and_final_association():
    anchor = LabelRect(0, 0, 10, 10)
    host_association = MemberNameAssociation(anchor, 0, 0, 8, 4, 0)
    final_association = MemberNameAssociation(LabelRect(39, 0, 5, 10), 0, 0, 8, 4, 0)

    result = place_member_name(
        anchor, (1, 1), ("end",), own_mark_right=30, overflow="visible-overflow",
        visible_fallback_side="end", bounds=LabelRect(0, 0, 36, 20), obstacles=(),
        gap=9, maximum_end_gap=100,
        candidate_geometries={
            "end": LabelCandidateGeometry((8, 4), gap=1, maximum_end_gap=100,
                                           association=host_association,
                                           final_association=final_association),
        },
    )

    assert result is not None
    assert result.final_rung and result.visible_overflow
    assert result.bounds == LabelRect(31, 3, 8, 4)


def test_candidate_geometries_reject_missing_or_invalid_geometry():
    with pytest.raises(ValueError, match="E_PRESENTATION_LABEL_INPUT"):
        place_label(LabelRect(10, 10, 5, 5), (2, 2), ("above", "end"),
                    bounds=LabelRect(0, 0, 100, 100),
                    candidate_geometries={"above": LabelCandidateGeometry((2, 2))})
    with pytest.raises(ValueError, match="E_PRESENTATION_LABEL_INPUT"):
        place_member_name(LabelRect(10, 10, 5, 5), (2, 2), ("end",),
                          bounds=LabelRect(0, 0, 100, 100), gap=1, maximum_end_gap=10,
                          candidate_geometries={"end": LabelCandidateGeometry((0, 2))})


def test_none_candidate_geometry_matches_existing_solver_behavior():
    anchor = LabelRect(20, 20, 10, 10)
    bounds = LabelRect(0, 0, 100, 100)
    assert place_label(anchor, (5, 4), ("end", "above"), bounds=bounds, gap=2) == place_label(
        anchor, (5, 4), ("end", "above"), bounds=bounds, gap=2, candidate_geometries=None)
    assert place_member_name(anchor, (5, 4), ("end", "start"), bounds=bounds,
                             gap=2, maximum_end_gap=20) == place_member_name(
        anchor, (5, 4), ("end", "start"), bounds=bounds,
        gap=2, maximum_end_gap=20, candidate_geometries=None)
