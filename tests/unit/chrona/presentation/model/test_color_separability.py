import pytest

from chrona.presentation.model.color_scale import resolve_color_scale
from chrona.presentation.model.color_separability import (
    MINIMUM_CATEGORY_DELTA_E, delta_e_2000, scale_collisions,
)


def test_ciede2000_matches_the_reference_pair_and_is_zero_for_duplicates() -> None:
    assert delta_e_2000("#142642", "#142642") == 0.0
    assert delta_e_2000("#000000", "#FFFFFF") == pytest.approx(100.0, abs=0.01)
    assert delta_e_2000("#FF0000", "#00FF00") == delta_e_2000("#00FF00", "#FF0000")


def test_duplicate_and_near_colours_are_named_collisions() -> None:
    colours = (("bus", "#142642"), ("payload", "#12302B"), ("launch", "#142642"), ("near", "#152743"))
    collisions = scale_collisions("owner", colours)
    pairs = {(item.first, item.second) for item in collisions}
    assert ("bus", "launch") in pairs and ("bus", "near") in pairs and ("launch", "near") in pairs
    assert ("bus", "payload") not in pairs
    duplicate = next(item for item in collisions if (item.first, item.second) == ("bus", "launch"))
    assert duplicate.delta_e == 0.0 and duplicate.vision == "normal"
    assert duplicate.scene_diagnostic() == "W_PRESENTATION_SCALE_NOT_SEPARABLE:owner:bus:launch:normal"


def test_claimed_colour_vision_is_checked_and_unclaimed_is_not() -> None:
    gold, olive = "#B8860B", "#6B8E23"  # 24.4 for normal vision, 1.5 under protanopia
    assert delta_e_2000(gold, olive) >= MINIMUM_CATEGORY_DELTA_E
    assert delta_e_2000(gold, olive, vision="protanopia") < MINIMUM_CATEGORY_DELTA_E
    colours = (("a", gold), ("b", olive))
    assert scale_collisions("s", colours) == ()
    assert scale_collisions("s", colours, ("none-claimed",)) == ()
    claimed = scale_collisions("s", colours, ("protanopia", "deuteranopia"))
    assert [item.vision for item in claimed] == ["protanopia"]


def test_resolved_scale_carries_collisions_without_refusing() -> None:
    scale = resolve_color_scale(
        {"scale": "owner", "target": "planned", "source": {"field": "owner"}, "domain": ["bus", "launch"]},
        {"owner": {"slots": {"bus": "bus", "launch": "launch"}}},
        {"bus": "#142642", "launch": "#142642"},
    )
    assert scale is not None and scale.color_for("x", {"owner": "launch"}) == "#142642"
    assert [(item.first, item.second) for item in scale.collisions] == [("bus", "launch")]
