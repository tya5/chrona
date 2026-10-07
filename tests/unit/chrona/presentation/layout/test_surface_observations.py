from decimal import Decimal
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_observations import compose_observations, observations_table_content
from chrona.presentation.layout.surface_quality import SlotPlacement, SurfaceLayoutRequest
from chrona.presentation.model.theme_tokens import ThemeTokenView
from tests.unit.chrona.presentation.scene.test_v05_builder import _Font, _theme


def _request(rows, columns=(('signal', 'Signal'), ('note/a', 'Note'))):
    content = SimpleNamespace(observation_columns=columns, observation_rows=rows)
    theme = _theme()
    measured = SimpleNamespace(metric_values={"table.column.gutter.inlineSize": Decimal(6)})
    return SurfaceLayoutRequest(surface_content=content, measured_sources=measured,
                                theme_tokens=ThemeTokenView(theme), font_metrics=_Font())


def _slot(*, width=240, height=80, overflow="visible-overflow"):
    return SlotPlacement("detail-observations", "observations",
                         Rect(Decimal(20), Decimal(40), Decimal(width), Decimal(height)),
                         overflow=overflow)


def test_rows_keep_order_provenance_and_emphasis_as_paint_semantics():
    rows = (
        ("row:a/b", "Runbook · owner: Ada", "normal", (("signal", "nominal"), ("note/a", "stable"))),
        ("row:second", "Source: team Ω", "attention", (("signal", "watch"), ("note/a", "capacity"))),
        ("row:third", "System: flight", "critical", (("signal", "blocked"), ("note/a", "review"))),
    )
    batch = compose_observations(slot=_slot(), request=_request(rows))
    assert [item.placement_id for item in batch.text[:2]] == [
        "observations:header:signal", "observations:header:note%2Fa"]
    source_items = [item for item in batch.text if item.placement_id.endswith(":source")]
    assert [item.source_ref for item in source_items] == ["row:a/b", "row:second", "row:third"]
    assert [item.source_content for item in source_items] == [row[1] for row in rows]
    cells = [item for item in batch.text if ":cell:" in item.placement_id]
    assert [item.semantic_id for item in cells] == [
        "tableCell", "tableCell", "tableVarianceAhead", "tableVarianceAhead",
        "tableVarianceBehind", "tableVarianceBehind"]
    assert [item.source_ref for item in cells] == [
        "row:a/b", "row:a/b", "row:second", "row:second", "row:third", "row:third"]
    assert all(item.typography_role == "text" for item in cells)


def test_adversarial_row_and_column_ids_have_injective_stable_paths():
    rows = (
        ("a/b", "source 1", "normal", (("c:d", "one"),)),
        ("a%2Fb", "source 2", "normal", (("c%3Ad", "two"),)),
    )
    columns = (("c:d", "First"), ("c%3Ad", "Second"))
    batch = compose_observations(slot=_slot(), request=_request(rows, columns))
    ids = [item.placement_id for item in batch.text]
    assert len(ids) == len(set(ids))
    assert "observations:row:a%2Fb:cell:c%3Ad" in ids
    assert "observations:row:a%252Fb:cell:c%253Ad" in ids


def test_wrapped_source_and_cells_grow_completed_slot_and_preserve_source_text():
    rows = (("long", "Source provenance words " * 8, "critical",
             (("signal", "x " * 30), ("note/a", "d " * 30))),)
    batch = compose_observations(slot=_slot(width=80, height=15, overflow="ellipsize-with-source"),
                                 request=_request(rows))
    source, *cells = [item for item in batch.text if item.source_ref == "long"]
    assert len(source.lines) > 1
    assert any(len(item.lines) > 1 for item in cells)
    assert source.source_content == rows[0][1]
    assert all(item.source_content for item in cells)
    assert batch.slot.bounds.block_size > Decimal(15)
    assert any(warning.code == "W_LAYOUT_VISIBLE_OVERFLOW" for warning in batch.warnings)
    assert all(item.bounds.inline_size <= Decimal(80) for item in [source, *cells])


def test_empty_observations_return_original_slot_without_headers():
    slot = _slot()
    batch = compose_observations(slot=slot, request=_request(()))
    assert batch.slot is slot
    assert batch.text == ()
    assert batch.columns == ()
    assert batch.warnings == ()


def test_premeasurement_table_facts_reuse_existing_typed_table_model():
    content = _request((("row", "source", "attention", (("signal", "watch"), ("note/a", "details"))),)).surface_content
    table = observations_table_content(content)
    assert tuple(column.column_id for column in table.columns) == ("signal", "note/a")
    assert tuple(cell.object_id for cell in table.cells) == ("row", "row")
    assert tuple(cell.semantic_id for cell in table.cells) == ("tableVarianceAhead",) * 2
    assert table.cell_objects == () and table.hierarchy_column is None and table.row_levels == ()
    assert all(column.width.minimum == "ellipsis" and column.width.maximum == "fr"
               for column in table.columns)


def test_zero_width_clip_optional_suppresses_unrepresentable_provenance_without_losing_source():
    row = ("row", "provenance-without-breakpoints", "normal", (("signal", "visible"), ("note/a", "cell")))
    batch = compose_observations(slot=_slot(width=0, height=20, overflow="clip-optional"),
                                 request=_request((row,)))
    source = next(item for item in batch.text if item.placement_id.endswith(":source"))
    assert source.overflow == "suppressed" and source.required is False
    assert source.source_ref == row[0] and source.source_content == row[1]
    warning = next(item for item in batch.warnings if item.placement_id == source.placement_id)
    assert warning.code == "W_LAYOUT_DETAIL_PANEL_CLIPPED"
    assert warning.behaviour == "clip-optional"


def test_ellipsis_that_cannot_fit_keeps_natural_source_visible():
    row = ("row", "verylongunbreakableprovenance", "normal", (("signal", "x"), ("note/a", "y")))
    batch = compose_observations(slot=_slot(width=1, height=20, overflow="ellipsize-with-source"),
                                 request=_request((row,)))
    source = next(item for item in batch.text if item.placement_id.endswith(":source"))
    assert source.overflow == "visible-overflow"
    assert source.source_content == row[1]
    assert source.lines == (row[1],)
    assert any(item.code == "W_LAYOUT_VISIBLE_OVERFLOW" and item.placement_id == source.placement_id
               for item in batch.warnings)


@pytest.mark.parametrize("emphasis, semantic", [("normal", "tableCell"),
                                                 ("attention", "tableVarianceAhead"),
                                                 ("critical", "tableVarianceBehind")])
def test_emphasis_contract_mapping(emphasis, semantic):
    from chrona.presentation.layout.surface_observations import _emphasis_semantic
    assert _emphasis_semantic(emphasis) == semantic
