import pytest

from chrona.presentation.model import color_separability
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
    assert not any((item.first, item.second) == ("bus", "payload") and item.vision == "normal"
                   for item in collisions)
    duplicate = next(item for item in collisions
                     if (item.first, item.second) == ("bus", "launch") and item.vision == "normal")
    assert duplicate.delta_e == 0.0 and duplicate.vision == "normal"
    assert duplicate.scene_diagnostic() == "W_PRESENTATION_SCALE_NOT_SEPARABLE:owner:bus:launch:normal"


def test_every_supported_colour_vision_is_checked_independent_of_claims() -> None:
    # This pair clears normal vision and two simulations, but not deuteranopia.
    violet, blue = "#8957E5", "#2F81F7"
    assert delta_e_2000(violet, blue) >= MINIMUM_CATEGORY_DELTA_E
    assert delta_e_2000(violet, blue, vision="protanopia") >= MINIMUM_CATEGORY_DELTA_E
    assert delta_e_2000(violet, blue, vision="deuteranopia") < MINIMUM_CATEGORY_DELTA_E
    assert delta_e_2000(violet, blue, vision="tritanopia") >= MINIMUM_CATEGORY_DELTA_E
    collisions = scale_collisions("s", (("violet", violet), ("blue", blue)))
    assert [(item.first, item.second, item.vision) for item in collisions] == [
        ("violet", "blue", "deuteranopia")]


def test_exact_duplicate_is_reported_in_all_four_vision_modes() -> None:
    collisions = scale_collisions("s", (("a", "#8957E5"), ("b", "#8957E5")))
    assert [item.vision for item in collisions] == [
        "normal", "protanopia", "deuteranopia", "tritanopia"]
    assert all(item.delta_e == 0.0 for item in collisions)


def test_scale_collision_retains_raw_measurement_before_display_rounding(monkeypatch) -> None:
    monkeypatch.setattr(
        color_separability, "delta_e_2000",
        lambda _first, _second, *, vision: 4.9996 if vision == "normal" else 5.0,
    )

    collisions = scale_collisions("s", (("a", "#000000"), ("b", "#FFFFFF")))

    assert [(item.vision, item.delta_e) for item in collisions] == [("normal", 4.9996)]
    assert collisions[0].delta_e < MINIMUM_CATEGORY_DELTA_E


def test_resolved_scale_carries_collisions_without_refusing() -> None:
    scale = resolve_color_scale(
        {"scale": "owner", "target": "planned", "source": {"field": "owner"}, "domain": ["bus", "launch"]},
        {"owner": {"slots": {"bus": "bus", "launch": "launch"}}},
        {"bus": "#142642", "launch": "#142642"},
    )
    assert scale is not None and scale.color_for("x", {"owner": "launch"}) == "#142642"
    assert [(item.first, item.second, item.vision) for item in scale.collisions] == [
        ("bus", "launch", vision)
        for vision in ("normal", "protanopia", "deuteranopia", "tritanopia")]
