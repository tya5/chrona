import pytest

from chrona.presentation.model.color_separability import (
    MINIMUM_CATEGORY_DELTA_E, SIMULATED_VISIONS, _simulate, delta_e_2000, scale_collisions,
)


def test_grayscale_uses_the_existing_ciede2000_metric_for_black_and_white():
    assert delta_e_2000("#000000", "#FFFFFF", vision="grayscale") == pytest.approx(100.0, abs=0.01)
    assert delta_e_2000("#808080", "#808080", vision="grayscale") == 0.0


def test_equal_luminance_colours_are_nearly_identical_under_grayscale():
    # Equal-luminance continuous red and green inputs map to the same grey.
    red = _simulate((0.5, 0.0, 0.0), "grayscale")
    green = _simulate((0.0, 0.5 * 0.2126 / 0.7152, 0.0), "grayscale")
    assert red == pytest.approx(green, abs=1e-16)
    # The closest 8-bit green to pure red differs in luminance by less than 0.001.
    assert delta_e_2000("#FF0000", "#009400", vision="grayscale") < 0.1
    assert delta_e_2000("#FF0000", "#009400", vision="normal") > MINIMUM_CATEGORY_DELTA_E


def test_grayscale_keeps_sub_palette_luminance_differences_without_quantizing():
    difference = delta_e_2000("#000000", "#010000", vision="grayscale")
    assert difference > 0.0
    # The full-precision grey for this red increment rounds to black at 8-bit sRGB.
    linear_red = (1 / 255) / 12.92
    encoded_grey = 12.92 * (0.2126 * linear_red)
    assert encoded_grey < 0.5 / 255


def test_print_simulation_does_not_expand_colour_vision_scale_domains():
    assert SIMULATED_VISIONS == ("protanopia", "deuteranopia", "tritanopia")
    colours = (("gold", "#B8860B"), ("olive", "#6B8E23"))
    assert all(item.vision in {"normal", *SIMULATED_VISIONS}
               for item in scale_collisions("s", colours))
    assert delta_e_2000("#B8860B", "#6B8E23", vision="protanopia") < MINIMUM_CATEGORY_DELTA_E
    with pytest.raises(ValueError, match="E_COLOR_VISION_UNKNOWN:achromatopsia"):
        delta_e_2000("#000000", "#FFFFFF", vision="achromatopsia")
