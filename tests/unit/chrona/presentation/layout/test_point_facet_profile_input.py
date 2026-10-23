"""Point-scale measurement receives the selected neutral paint admission."""
from datetime import date
from types import SimpleNamespace

from chrona.presentation.layout import surface_base
from chrona.presentation.layout.obstacles import ObstacleRect
from chrona.presentation.model.paint_capabilities import PaintWitnessCapabilities
from chrona.presentation.model.projection import ReviewItem


def test_provisional_point_facets_use_selected_profile_admission(monkeypatch):
    item = ReviewItem(
        "gate", "Gate", "point", {"at": date(2026, 1, 2)}, None, None,
        ("planned",), item_id="gate", source_kind="primary")
    row = SimpleNamespace(row_id="row", items=(item,))
    projection = SimpleNamespace(lane_membership=None, rows=(row,), folded_points=())
    mark = SimpleNamespace(mark_shape="point", semantic_id="planned")
    selected = PaintWitnessCapabilities(line_finish_supported=False,
                                         optional_line_finish_omission=True)
    received = []

    monkeypatch.setattr(surface_base.MarkBandFrame, "zero_origin", lambda *_args: None)
    monkeypatch.setattr(surface_base, "compose_item_marks",
                        lambda **_kwargs: SimpleNamespace(marks=(mark,)))

    def facets(_item, _instance, _mark, _theme, *, paint_capabilities):
        received.append(paint_capabilities)
        return (SimpleNamespace(visible_footprint=ObstacleRect(1, 2, 3, 4)),)

    monkeypatch.setattr(surface_base, "_mark_facets", facets)
    result = surface_base._provisional_point_facets(
        projection=projection, rows=(row,), scale=None, as_of=None,
        theme_tokens=None, slot_id="timeline", mark_block_size=10,
        role_geometries={}, paint_capabilities=selected)

    assert received == [selected]
    assert received[0] is selected
    assert [(value.anchor_date, value.left, value.right) for value in result] == [
        (date(2026, 1, 2), 1, 3)]
