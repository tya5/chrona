from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.relation_halo import complete_relation_halo
from chrona.presentation.layout.surface_quality import RelationPlacement


def _relation():
    return RelationPlacement("r", "source:end", "target:start", ((10., 20.), (30., 20.)))


def _tokens():
    return SimpleNamespace(dependency_halo_width=lambda role: Decimal(6))


def test_layout_closes_halo_bounds_and_shared_text_order_without_mutating_source():
    source = _relation()
    completed = complete_relation_halo(source, _tokens(), (SimpleNamespace(paint_order=200),))
    assert source.halo is None and source.paint_order == 250
    assert completed.paint_order == 199
    assert completed.halo.paint_order == 198
    assert completed.halo.bounds == (7., 17., 26., 6.)
    assert completed.halo.points == source.points


def test_normalized_empty_text_uses_existing_line_layer():
    completed = complete_relation_halo(_relation(), _tokens(), ())
    assert completed.paint_order == 250 and completed.halo.paint_order == 249


@pytest.mark.parametrize("field,value", (("suppressed", True), ("paint_order", 260),
                                        ("points", ((10., 20.), (40., 20.)))))
def test_completed_halo_cannot_drift_from_its_line(field, value):
    completed = complete_relation_halo(_relation(), _tokens(), ())
    with pytest.raises(ValueError, match="inconsistent completed relation halo"):
        replace(completed, **{field: value})


def test_no_legal_layer_does_not_silently_cover_text():
    with pytest.raises(ValueError, match="no paint layer below text"):
        complete_relation_halo(_relation(), _tokens(), (SimpleNamespace(paint_order=1),))
