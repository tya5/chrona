"""The plot: where gridlines, closed days, the as-of line and a period band end (#880 item 2).

A slot is an allocation and the rows are the content. When a surface is given more block room than its rows need,
the ground (group and row bands) stops at the last row; every overlay that spans the plot must stop there too.
Each rule is proven on a synthetic Project rendered through a packaged preset bundle, so no corpus edit can change
what these tests prove.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_geometry import plot_rect
from tests.support import synthetic_review as sr

WINDOW = {"mode": "explicit", "start": "2026-01-01", "end": "2026-04-01"}
ACTUAL = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
          "body": {"asOf": "2026-02-20", "observations": [
              {"id": "a-observed", "sequence": 1, "projectObjectId": "a",
               "actual": {"start": "2026-01-05", "finish": "2026-02-10", "progress": 1.0}}]}}


def _source() -> dict:
    return sr.project({
        "a": sr.span("a", date(2026, 1, 5), 40),
        "b": sr.span("b", date(2026, 2, 10), 30, owner="b"),
        "g": sr.point("g", date(2026, 3, 20)),
    })


def _parts() -> dict:
    parts = sr.bundle("executive-light")
    body = parts["view"]["body"]
    body["window"] = dict(WINDOW)
    body["periods"] = [{"id": "freeze"}]
    parts["theme"]["body"]["roles"]["period-band"] = {
        "backgroundTreatment": "fill", "backgroundPaintOrder": 11, "opacity": "opacity.axis-band"}
    parts["theme"]["body"]["colorBindings"].pop("period-band.stroke", None)  # the packaged band is an outline
    parts["theme"]["body"]["colorBindings"]["period-band.fill"] = "accent"
    return parts


def _render(tmp_path: Path, viewport: tuple[int, int | None] = (1600, 900)):
    source = _source()
    source["periods"] = {"freeze": {"title": "Freeze", "start": "2026-02-01", "end": "2026-03-01"}}
    directory = tmp_path / "render"
    directory.mkdir()
    return sr.render(directory, source, presentation=_parts(), actual=ACTUAL, viewport=viewport)


def _box(bounds) -> tuple[float, float, float, float]:
    """Scene primitives carry a tuple, slots a Rect."""
    if isinstance(bounds, tuple):
        return tuple(float(value) for value in bounds)
    return (float(bounds.inline), float(bounds.block), float(bounds.inline_size), float(bounds.block_size))


def _bottom(item) -> float:
    _, block, _, size = _box(item.bounds)
    return block + size


def _slot(rendered, slot_id: str):
    return next(item for item in rendered.surface.slots if item.slot_id == slot_id)


def _ground_bottom(rendered) -> float:
    return max(_bottom(item) for item in rendered.surface.primitives if item.purpose == "group-decoration")


def _overlays(rendered) -> dict[str, list]:
    wanted = {"calendar-closed", "as-of", "period-band"}
    found: dict[str, list] = {key: [] for key in (*wanted, "axis-grid")}
    for item in rendered.surface.primitives:
        if item.purpose in wanted:
            found[item.purpose].append(item)
        elif item.purpose == "axis-grid" and _box(item.bounds)[3] > 8:
            found["axis-grid"].append(item)
    return found


def test_overlays_end_where_the_ground_ends_when_the_slot_is_taller_than_the_rows(tmp_path):
    rendered = _render(tmp_path)
    slot = _slot(rendered, "timeline")
    ground = _ground_bottom(rendered)
    assert _bottom(slot) - ground > 100, "fixture: the slot must be much taller than the rows"

    overlays = _overlays(rendered)
    for purpose, items in overlays.items():
        assert items, purpose
        for item in items:
            assert _bottom(item) == pytest.approx(ground), (purpose, item.scene_id)
            assert _box(item.bounds)[1] == pytest.approx(_box(slot.bounds)[1]), (purpose, item.scene_id)


def test_the_overlay_path_points_end_at_the_ground_too(tmp_path):
    rendered = _render(tmp_path)
    ground = _ground_bottom(rendered)

    for item in (*_overlays(rendered)["as-of"], *_overlays(rendered)["axis-grid"]):
        assert [point[1] for point in item.points][-1] == pytest.approx(ground), item.scene_id


def test_a_slot_that_fits_its_rows_keeps_overlays_at_the_ground(tmp_path):
    # An automatic block size sizes the slot to its rows (within a pixel): nothing is left to trim.
    rendered = _render(tmp_path, viewport=(1600, None))
    slot = _slot(rendered, "timeline")
    ground = _ground_bottom(rendered)

    assert 0 <= _bottom(slot) - ground < 1
    for purpose, items in _overlays(rendered).items():
        for item in items:
            assert _bottom(item) == pytest.approx(ground), (purpose, item.scene_id)


def test_a_period_label_at_the_bottom_sits_on_the_plot_not_the_empty_strip(tmp_path):
    source = _source()
    source["periods"] = {"freeze": {"title": "Freeze", "start": "2026-02-01", "end": "2026-03-01"}}
    parts = _parts()
    parts["view"]["body"]["periods"] = [{"id": "freeze", "label": {"placement": "bottom"}}]
    body = parts["theme"]["body"]
    body["roles"]["period-label"] = {
        **{key: value for key, value in body["roles"]["annotation-note-text"].items() if key != "contrastTreatment"},
        "contrastTreatment": "required"}
    body["colorBindings"]["period-label.fill"] = "text"
    directory = tmp_path / "label"
    directory.mkdir()
    rendered = sr.render(directory, source, presentation=parts, actual=ACTUAL)
    ground = _ground_bottom(rendered)

    labels = [item for item in rendered.surface.primitives if item.purpose == "period-label"]
    assert labels and all(_bottom(item) <= ground + 0.01 for item in labels)


# --- the rule itself, on bare rectangles --------------------------------------------------------------------

def _rect(block: float, size: float) -> Rect:
    return Rect(Decimal(10), Decimal(str(block)), Decimal(100), Decimal(str(size)))


SLOT = _rect(50, 400)  # block 50 to 450


def test_the_plot_ends_at_the_last_row_bottom():
    plot = plot_rect(SLOT, (_rect(50, 40), _rect(90, 60)))

    assert (plot.block, plot.block + plot.block_size) == (Decimal(50), Decimal(150))
    assert (plot.inline, plot.inline_size) == (Decimal(10), Decimal(100))


def test_the_plot_never_runs_past_the_slot():
    plot = plot_rect(SLOT, (_rect(50, 40), _rect(400, 200)))

    assert plot.block + plot.block_size == Decimal(450)


def test_the_plot_is_the_slot_when_there_are_no_rows():
    assert plot_rect(SLOT, ()) == SLOT


def test_the_plot_is_the_slot_when_the_rows_fill_it():
    assert plot_rect(SLOT, (_rect(50, 200), _rect(250, 200))) == SLOT
