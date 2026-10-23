from chrona.presentation.layout.labels import LabelCandidateGeometry, LabelRect, place_label


def test_authored_painted_anchor_moves_side_candidate_but_not_inside_host():
    semantic = LabelRect(10, 10, 10, 10)
    painted = LabelRect(8, 8, 16, 14)
    bounds = LabelRect(0, 0, 100, 100)

    side = place_label(
        semantic, (4, 4), ("end",), bounds=bounds, gap=2,
        candidate_geometries={"end": LabelCandidateGeometry((4, 4), gap=2,
                                                                side_anchor=painted)},
    )
    inside = place_label(
        semantic, (4, 4), ("inside",), bounds=bounds, gap=2,
        candidate_geometries={"inside": LabelCandidateGeometry((4, 4), gap=2,
                                                                   side_anchor=painted)},
    )

    assert side is not None and side.bounds == LabelRect(26, 13, 4, 4)
    # The painted envelope is asymmetric around its semantic host; inside still
    # centers in the original host and cannot borrow its larger ink envelope.
    assert inside is not None and inside.bounds == LabelRect(13, 13, 4, 4)
