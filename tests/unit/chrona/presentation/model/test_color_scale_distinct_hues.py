"""A categorical scale never repeats a hue across legend entries (#1628)."""
from __future__ import annotations

from chrona.presentation.model.color_scale import OTHER_LABEL, resolve_color_scale
from chrona.presentation.model.color_separability import MINIMUM_CATEGORY_DELTA_E, delta_e_2000

CATEGORIES = {"s1": "#2F81F7", "s2": "#2A9D43", "s3": "#D2691E", "s4": "#8957E5"}
SCALES = {"series": {"palette": ["s1", "s2", "s3", "s4"]}}
OTHER = "#6B747E"


def _resolve(observed, reserved=()):
    encoding = {"scale": "series", "target": "planned", "source": {"field": "owner"}, "domain": "firstAppearance"}
    return resolve_color_scale(encoding, SCALES, CATEGORIES, observed=tuple(observed), reserved=tuple(reserved),
                               other_color=OTHER)


def test_n_plus_one_values_give_n_distinct_hues_and_one_neutral_other():
    scale = _resolve(["a", "b", "c", "d", "e"])
    colors = dict(scale.colors)
    assert [colors[name] for name in "abcd"] == ["#2F81F7", "#2A9D43", "#D2691E", "#8957E5"]
    assert colors["e"] == OTHER and scale.folded == ("e",) and scale.palette_size == 4
    items = scale.legend_items(set("abcde"))
    assert [label for _, label, _ in items] == ["a", "b", "c", "d", OTHER_LABEL]
    assert len({color for _, _, color in items}) == 5


def test_the_remainder_folds_in_source_order_into_a_single_entry():
    scale = _resolve(["a", "b", "c", "d", "e", "f", "g"])
    assert scale.folded == ("e", "f", "g")
    assert {dict(scale.colors)[name] for name in "efg"} == {OTHER}
    assert [label for _, label, _ in scale.legend_items(set("abcdefg"))].count(OTHER_LABEL) == 1


def test_a_domain_that_fits_is_not_folded():
    scale = _resolve(["a", "b", "c", "d"])
    assert scale.folded == () and len({color for _, color in scale.colors}) == 4


def test_a_palette_colour_reserved_by_planned_or_milestone_is_never_assigned():
    scale = _resolve(["a", "b", "c", "d"], reserved=["#2F81F7"])
    assert "#2F81F7" not in {color for _, color in scale.colors}
    assert scale.palette_size == 3 and scale.folded == ("d",)
    assert all(delta_e_2000(color, "#2F81F7") >= MINIMUM_CATEGORY_DELTA_E for _, color in scale.colors)


def test_a_palette_slot_repeating_an_earlier_hue_is_skipped():
    categories = {**CATEGORIES, "s5": "#2F81F7"}
    scales = {"series": {"palette": ["s1", "s2", "s5", "s3"]}}
    encoding = {"scale": "series", "target": "planned", "source": {"field": "owner"}, "domain": "firstAppearance"}
    scale = resolve_color_scale(encoding, scales, categories, observed=("a", "b", "c", "d"), other_color=OTHER)
    assert scale.palette_size == 3 and scale.folded == ("d",)
