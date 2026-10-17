from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace

from chrona.presentation.layout.lane_label_intent import measure_lane_member_labels
from chrona.presentation.layout.style_occurrences import StyleSourceOccurrences
from chrona.presentation.layout.surface_mark_visibility import MarkOccurrence, MarkOccurrenceKind
from chrona.presentation.model.style_rules import (
    OccurrenceStyleIndex, OccurrenceStyleIntent, StyleOccurrenceKey,
)
from chrona.presentation.model.semantic_registry import inside_member_label_semantic
from chrona.presentation.model.theme_tokens import ThemeTokenView


@dataclass(frozen=True)
class _Item:
    object_id: str
    item_id: str
    title: str
    finish_delta: int | None = None
    source_kind: str = "primary"
    attached_to: str | None = None
    presentation: dict | None = None


class _Metrics:
    def select(self, _family, _weight):
        return self

    def width(self, content, size, **kwargs):
        return len(content) * size + len(content) * kwargs.get("letter_spacing", 0)


class _Theme:
    def text_treatment(self, _role):
        return SimpleNamespace(family="Test", weight=400, font_size=Decimal(10),
                               line_height=Decimal("1.2"), letter_spacing=Decimal(0),
                               transform="none", numeric_spacing="proportional",
                               horizontal_scale=Decimal(1))

    def icon_ratios(self, _role):
        return Decimal("0.5"), Decimal("0.2")

    def label_chip(self, _role):
        return (Decimal("0.1"), Decimal(0))

    def label_chip_min_block(self, _role):
        return None

    def label_chip_shape(self, _role):
        from chrona.presentation.model.theme_tokens import RectangleChipShape
        return RectangleChipShape()


def _inputs(items):
    projection = SimpleNamespace(
        rows=(SimpleNamespace(row_id="source-row", items=tuple(items)),),
        lane_rows=(SimpleNamespace(lane_id="lane-a", items=tuple(items),
                                   member_item_ids=tuple(item.item_id for item in items)),),
    )
    content = SimpleNamespace(show_member_labels=True, label_content=("title",),
                              label_side="auto", label_fallback=("inside", "end"),
                              label_text_role=None, attached_labels=())
    return projection, content


class _RoleTheme(_Theme):
    def __init__(self):
        self._paint = ThemeTokenView({
            "version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
            "body": {"values": {"ink": {"type": "color", "value": "#000000"}},
                     "roles": {"style-wide-label": {"fill": "ink"}}},
        })

    def __getattr__(self, name):
        return getattr(self._paint, name)

    def text_treatment(self, role):
        size = Decimal(20 if role == "style-wide-label" else 10)
        return SimpleNamespace(family="Test", weight=400, font_size=size,
                               line_height=Decimal("1.2"), letter_spacing=Decimal(0),
                               transform="none", numeric_spacing="proportional",
                               horizontal_scale=Decimal(1))

    def color(self, role, property_name):
        return "#000000"


def _style_index(key):
    return OccurrenceStyleIndex((OccurrenceStyleIntent(
        key, "style-wide-label", None, ("wide-label",), ("wide-label",), ()),))


def test_lane_label_preflight_measures_each_candidate_from_source_identity(monkeypatch):
    item = _Item("gate", "gate-instance", "Gate label")
    projection, content = _inputs((item,))
    source_key = StyleOccurrenceKey("gate", "primary", inside_member_label_semantic("primary"), "source-row", "gate-instance",
                                    occurrence_kind="lane-source")
    source = MarkOccurrence(MarkOccurrenceKind.LANE_SOURCE, "source-row", "gate-instance",
                            "gate", "primary")
    sources = StyleSourceOccurrences(True, True, {
        ("lane-a", "gate-instance", "gate", "primary"): source,
    })
    monkeypatch.setattr(StyleSourceOccurrences, "from_projection",
                        classmethod(lambda cls, projection, *, as_of=None: sources))
    content.style_intents = _style_index(source_key)

    (measured,) = measure_lane_member_labels(
        projection, content, timeline_inline_size=100, theme_tokens=_RoleTheme(),
        font_metrics=_Metrics(), visual_requests=(), icon_assets={},
    )

    assert tuple(side for side, _ in measured.candidate_measurements) == ("inside", "end")
    start, end = dict(measured.candidate_measurements)["inside"], dict(measured.candidate_measurements)["end"]
    assert start.font_size == 20
    assert end.font_size == 10
    assert start.width > end.width
    assert measured.width == start.width
    assert measured.height == start.height
    assert all(not leaf.candidate_measurements for _, leaf in measured.candidate_measurements)
    assert source_key == source.style_key(inside_member_label_semantic("primary"))


def test_unstyled_lane_label_keeps_original_single_measurement_shape():
    item = _Item("gate", "gate-instance", "Gate label")
    projection, content = _inputs((item,))

    (measured,) = measure_lane_member_labels(
        projection, content, timeline_inline_size=100, theme_tokens=_Theme(),
        font_metrics=_Metrics(), visual_requests=(), icon_assets={},
    )

    assert measured.candidate_measurements == ()
    assert measured.width == 102  # 10px character width plus the existing chip padding
    assert measured.font_size == 10
