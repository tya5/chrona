from dataclasses import dataclass
from types import SimpleNamespace

from chrona.presentation.layout import key_row_lanes


class _Treatment:
    font_size = 10
    letter_spacing = 0
    transform = "none"
    line_height = 1


class _Theme:
    def text_treatment(self, _role):
        return _Treatment()


@dataclass(frozen=True)
class _Item:
    item_id: str
    object_id: str
    title: str
    forecast: object
    finish_delta: int | None
    source_kind: str = "primary"
    key_lane: int | None = None
    key_pitch: float | None = None


@dataclass(frozen=True)
class _Row:
    key_row: bool
    row_id: str
    items: tuple[_Item, ...]


def _request(*, omit_zero_delta, content=("finishDelta",), labels_enabled=True):
    return SimpleNamespace(
        theme_tokens=_Theme(),
        projection=SimpleNamespace(),
        surface_content=SimpleNamespace(
            label_text_role="text", omit_zero_delta=omit_zero_delta,
            style_intents=None, member_name=lambda item, _row: item.title,
        ),
        presentation_contract=SimpleNamespace(labels=SimpleNamespace(
            side="end", content=content, enabled=labels_enabled,
        )),
        measured_sources=None,
        mark_visibility_index=None,
        font_metrics=None,
    )


def _run(monkeypatch, request, items):
    measurements = []

    class Frame:
        @staticmethod
        def zero_origin(*_args):
            return object()

    def measure(source_id, text, _role, semantic, _request, **_kwargs):
        measurements.append((source_id, text, semantic))
        heights = {"M": 5, "+0d": 17, "+1d*": 23, "+2d*": 31}
        return SimpleNamespace(size=(10, heights.get(text, 5)))

    monkeypatch.setattr(key_row_lanes, "MarkBandFrame", Frame)
    monkeypatch.setattr(key_row_lanes, "member_label_gap", lambda *_args: 0)
    monkeypatch.setattr(key_row_lanes, "chip_padding", lambda *_args: (0, 0))
    monkeypatch.setattr(key_row_lanes, "metric_for_role", lambda *_args: None)
    monkeypatch.setattr(key_row_lanes, "measure_text_width", lambda *_args, **_kwargs: 10)
    monkeypatch.setattr(key_row_lanes, "measure_label_footprint", measure)
    monkeypatch.setattr(key_row_lanes, "compose_item_marks", lambda **_kwargs: SimpleNamespace(marks=()))
    row = _Row(key_row=True, row_id="row", items=tuple(items))
    result = key_row_lanes.assign_key_row_lanes(
        (row,), request=request, scale=None, as_of=None, slot_id="slot", mark_block_size=1,
        role_geometries=None, mark_band_allocation=SimpleNamespace(outer_extent=1),
    )
    return result[0], measurements


def _forecast_item(item_id, delta):
    forecast = SimpleNamespace(
        schedule=SimpleNamespace(completed=False), finish_delta=delta,
    )
    return _Item(
        item_id=item_id, object_id=item_id, title=item_id, forecast=forecast,
        finish_delta=delta, source_kind="primary",
    )


def test_default_keeps_generic_delta_probe_even_without_forecast(monkeypatch):
    row, measurements = _run(monkeypatch, _request(omit_zero_delta=False), ())
    assert row.items == ()
    assert ("key-row-probe", "+0d", "finishDelta") in measurements


def test_zero_omission_measures_all_remaining_deltas_and_uses_max_block(monkeypatch):
    items = (_forecast_item("one", 1), _forecast_item("two", 2))
    row, measurements = _run(monkeypatch, _request(omit_zero_delta=True), items)
    assert {text for _, text, _ in measurements if text != "M"} == {"+1d*", "+2d*"}
    assert all(item.key_pitch == 31 for item in row.items)


def test_zero_omission_does_not_measure_zero_delta_block(monkeypatch):
    row, measurements = _run(
        monkeypatch, _request(omit_zero_delta=True), (_forecast_item("zero", 0),))
    assert all(text == "M" for _, text, _ in measurements)
    assert all(item.key_pitch == 5 for item in row.items)


def test_zero_omission_does_not_measure_hidden_delta_labels(monkeypatch):
    row, measurements = _run(
        monkeypatch, _request(omit_zero_delta=True, labels_enabled=False),
        (_forecast_item("one", 1),))
    assert row.items[0].key_pitch == 5
    assert all(semantic != "finishDelta" for _, _, semantic in measurements)
