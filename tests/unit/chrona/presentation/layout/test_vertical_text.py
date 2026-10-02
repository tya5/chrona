"""#585 I585-2: the character classes, segmentation and measured advances of a vertical label."""
from decimal import Decimal

import pytest

from chrona.presentation.layout.surface_quality import CollisionDomain
from chrona.presentation.layout.vertical_text import is_upright, place_vertical_label, segment_vertical
from chrona.presentation.model.theme_tokens import TextTreatment


@pytest.mark.parametrize("character", [
    "ぁ", "あ", "ア", "・", "・", "ヿ", "漢", "㐀", "䶿", "一", "鿿", "豈", "가", "힯",
    "、", "。", "　", "！", "Ａ", "｠",
])
def test_upright_characters(character):
    assert is_upright(character)


@pytest.mark.parametrize("character", [
    "A", "z", "0", "9", " ", "-", ".", "ー", "ー", "〜", "～", "―", "—", "…", "‥", "「", "」", "『", "』", "（", "）", "【", "】",
    "〈", "》", "〔", "(", "[", "{", "ｱ", "é", "Ж", "぀", "鿿" + "\u0000",
][:-1])
def test_sideways_characters(character):
    assert not is_upright(character)


def test_segmentation_keeps_a_sideways_run_whole_and_stands_each_upright_character_alone():
    assert segment_vertical("機体ABC12・x") == (
        ("upright", "機"), ("upright", "体"), ("sideways", "ABC12"), ("upright", "・"), ("sideways", "x"))
    assert segment_vertical("「機」") == (("sideways", "「"), ("upright", "機"), ("sideways", "」"))
    assert segment_vertical("a b") == (("sideways", "a b"),)
    assert segment_vertical("") == ()


class _Font:
    content_identity = "sha256:test"
    ascent, descent, units_per_em = 1000, -200, 1000

    def width(self, content, size, letter_spacing=0, numeric_spacing="proportional"):
        return sum(size if ord(character) > 0x2FFF else size / 2 for character in content) + max(0, len(content) - 1) * letter_spacing

    def ensure_numeric_spacing(self, _spacing):
        return None


def _theme(spacing="0", transform="none"):
    class Theme:
        def text_treatment(self, _role):
            return TextTreatment("Test", 400, Decimal(20), Decimal("1.5"), Decimal(spacing), transform, "proportional")
    return Theme()


def _place(label, *, block=100.0, available=300.0, spacing="0", transform="none"):
    return place_vertical_label(
        label=label, placement_prefix="tag:g", source_ref="g", column_inline=10.0, column_size=30.0,
        block_start=block, available_block=available, typography_role="groupHeader", theme_tokens=_theme(spacing, transform),
        font_metrics=_Font(), collision_region="group:g", collision_domain=CollisionDomain("group-header", "g"),
        semantic_id="groupHeader")


def _box(placement):
    bounds = placement.bounds
    return tuple(float(value) for value in (bounds.inline, bounds.block, bounds.inline_size, bounds.block_size))


def test_upright_characters_advance_one_em_and_sideways_runs_their_measured_width():
    placed = _place("漢字ab漢")
    assert [item.content for item in placed] == ["漢", "字", "ab", "漢"]
    assert [item.orientation for item in placed] == ["horizontal", "horizontal", "rotate-cw", "horizontal"]
    assert [item.rotation_degrees for item in placed] == [0, 0, 90, 0]
    blocks = [_box(item)[1:4:2] for item in placed]
    inset = 10.0  # half an em at each end
    assert blocks == [(100 + inset, 20.0), (120 + inset, 20.0), (140 + inset, 20.0), (160 + inset, 20.0)]
    assert [item.placement_id for item in placed] == ["tag:g:0", "tag:g:1", "tag:g:2", "tag:g:3"]


def test_the_segments_tile_the_column_without_overlap_and_are_centred_in_it():
    placed = _place("漢字abc漢", spacing="0.1")
    cursor = None
    for item in placed:
        x, y, w, h = _box(item)
        assert x + w / 2 == pytest.approx(25.0)  # the centre of the column [10, 40]
        if cursor is not None:
            assert y == pytest.approx(cursor)  # each segment starts where the last ended, plus one letter spacing
        cursor = y + h + 2
    assert [float(item.letter_spacing) for item in placed] == [2.0] * len(placed)


def test_a_sideways_run_is_a_quarter_turn_with_its_baseline_at_the_top_of_its_cell():
    run = _place("ab")[0]
    assert run.baseline[1] == pytest.approx(110.0)  # the run starts at the cell top (after the inset)
    assert run.baseline[0] == pytest.approx(25.0 - (1000 - 200) / 2 / 1000 * 20)  # em box centred on the column
    assert _box(run)[0] == pytest.approx(25.0 - 15.0) and _box(run)[2] == 30.0  # the line box: fontSize x lineHeight


def test_an_upright_character_is_centred_by_its_measured_width():
    placed = _place("漢")[0]
    assert _box(placed)[0] == pytest.approx(25.0 - 10.0)
    assert placed.baseline[1] == pytest.approx(110.0 + 10.0 + (1000 - 200) / 2 / 1000 * 20)


def test_a_label_longer_than_its_span_is_cut_at_a_segment_with_a_sideways_ellipsis():
    placed = _place("漢字漢字漢字", available=100.0)
    assert placed[-1].content == "…" and placed[-1].orientation == "rotate-cw"
    assert all(item.overflow == "ellipsized" and item.source_content == "漢字漢字漢字" for item in placed)
    assert _box(placed[-1])[1] + _box(placed[-1])[3] <= 100.0 + 100.0 - 10.0 + 1e-6  # inside the span less the end inset
    assert [item.content for item in placed[:-1]] == list("漢字漢字漢字")[: len(placed) - 1]


def test_a_label_that_fits_is_not_cut_and_one_whose_marker_does_not_fit_is_shown_whole():
    assert {item.overflow for item in _place("漢字", available=100.0)} == {"fit"}
    whole = _place("漢字", available=25.0)
    assert [item.content for item in whole] == ["漢", "字"] and {item.overflow for item in whole} == {"visible-overflow"}


def test_text_transform_applies_before_segmentation():
    assert [item.content for item in _place("ab漢", transform="uppercase")] == ["AB", "漢"]
