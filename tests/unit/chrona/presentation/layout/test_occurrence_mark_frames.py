from types import SimpleNamespace

from chrona.presentation.layout.mark_band_allocation import compose_mark_band
from chrona.presentation.layout.presentation import (
    MarkBandFrame, MarkGeometry, RowPlacement, minimum_track_block_extent,
    place_mark_tracks, required_row_block_extents,
)
from chrona.presentation.model.projection import ObservationState


def _roles():
    return {
        "planned": MarkGeometry(0.4, 0.3, 0, 0.0),
        "missing-actual": MarkGeometry(0.3, 0.35, 1, 0.0),
        "actual": MarkGeometry(0.2, 0.4, 2, 0.0),
        "snapshot": MarkGeometry(0.7, 0.15, 3, 0.0),
        "scenario": MarkGeometry(0.7, 0.15, 3, 0.0),
    }


def _stack(*, gap=8, padding=3):
    return SimpleNamespace(members=(("planned", "missing-actual"), ("actual",)),
                           gap=gap, frame_roles=("snapshot",), frame_padding=padding)


def _row(row_id, item_id):
    item = SimpleNamespace(item_id=item_id, object_id=item_id, track="stacked", source_kind="primary",
                           actual={}, observation_state=ObservationState.DUE_UNOBSERVED)
    return SimpleNamespace(row_id=row_id, group_id=None, items=(item,))


def test_selected_occurrence_stack_grows_row_and_its_marks_remain_contained():
    roles = _roles()
    selected_allocation = compose_mark_band(track_size=10, role_geometries=roles, stack=_stack())
    assert selected_allocation.outer_extent > selected_allocation.track_size
    frame = MarkBandFrame(None, 0.0, 10.0, roles, selected_allocation)
    row = _row("row", "item")
    occurrence_frames = {"row:item": frame}

    required = required_row_block_extents(
        review_rows=(row,), row_minimum=8, row_padding=0, mark_block_size=10,
        occurrence_frames=occurrence_frames,
    )
    assert required[0] >= selected_allocation.outer_extent
    assert minimum_track_block_extent(review_row=row, mark_block_size=10,
                                      occurrence_frames=occurrence_frames) == required[0]

    placement = RowPlacement("row", None, (0.0, 0.0, 100.0, required[0]))
    track = place_mark_tracks(review_rows=(row,), row_placements=(placement,), mark_block_size=10,
                              occurrence_frames=occurrence_frames)[0]
    assert track.instance_id == "row:item"
    for role in ("planned", "missing-actual"):
        local_block, extent = selected_allocation.span_bounds(role)
        assert track.block + local_block >= placement.bounds[1]
        assert track.block + local_block + extent <= placement.bounds[1] + placement.bounds[3]


def test_selected_pitch_is_scoped_to_each_row():
    roles = _roles()
    large = _row("large", "one")
    plain = _row("plain", "two")
    allocation = compose_mark_band(track_size=10, role_geometries=roles, stack=_stack())
    frames = {"large:one": MarkBandFrame(None, 0.0, 10.0, roles, allocation)}

    required = required_row_block_extents(review_rows=(large, plain), row_minimum=8, row_padding=0,
                                          mark_block_size=10, occurrence_frames=frames)

    assert required[0] == allocation.outer_extent
    assert required[1] == 10
    placements = tuple(RowPlacement(row.row_id, None, (0.0, index * size, 100.0, size))
                       for index, (row, size) in enumerate(zip((large, plain), required, strict=True)))
    tracks = place_mark_tracks(review_rows=(large, plain), row_placements=placements, mark_block_size=10,
                               occurrence_frames=frames)
    assert tuple(track.instance_id for track in tracks) == ("large:one", "plain:two")
    assert tracks[0].block != tracks[1].block


def test_no_occurrence_frames_preserve_existing_track_arithmetic():
    row = _row("row", "item")
    placement = RowPlacement("row", None, (0.0, 12.0, 100.0, 10.0))

    legacy = place_mark_tracks(review_rows=(row,), row_placements=(placement,), mark_block_size=10)
    empty = place_mark_tracks(review_rows=(row,), row_placements=(placement,), mark_block_size=10,
                              occurrence_frames={})

    assert legacy == empty
    assert legacy[0].block == legacy[0].actual_block == 12.0
    assert legacy[0].block_size == 10.0
    assert required_row_block_extents(review_rows=(row,), row_minimum=8, row_padding=0,
                                      mark_block_size=10) == (10.0,)
