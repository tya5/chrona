from decimal import Decimal

import pytest

from chrona.presentation.layout.text import measured_text_bounds, measure_text_width, place_text
from chrona.presentation.layout.surface_quality import CollisionDomain
from chrona.presentation.model.theme_tokens import TextTreatment


class _Theme:
    def typography(self, role):
        assert role == "text"
        return ("Test Sans", 400, 12, 1.5)

    def text_treatment(self, role):
        family, weight, size, line_height = self.typography(role)
        return TextTreatment(family, weight, size, line_height, 0, "none", "proportional")


class _Font:
    content_identity = "sha256:test"
    def width(self, content, size):
        return len(content) * size / 2


class _SpacedFont(_Font):
    def width(self, content, size, letter_spacing=0):
        return len(content) * size / 2 + max(0, len(content) - 1) * letter_spacing


@pytest.mark.parametrize("orientation,rotation", [("horizontal", 0), ("rotate-cw", 90), ("rotate-ccw", -90)])
def test_measured_bounds_are_the_same_native_rect_used_by_multiline_placement(orientation, rotation):
    placed = place_text(placement_id="label:bounds", source_ref="a", content="ABC\nDE",
                        lines=("ABC", "DE"), inline=0.1, baseline_block=0.3,
                        typography_role="text", theme_tokens=_Theme(), font_metrics=_Font(),
                        orientation=orientation)
    bounds = measured_text_bounds(inline=0.1, baseline_block=0.3, width=18.0,
                                  height=36.0, font_size=12.0, rotation=rotation)
    assert bounds == placed.bounds
    if rotation == 90:
        assert bounds.block + bounds.block_size == Decimal("0.3") + Decimal("18.0")
    elif rotation == -90:
        assert bounds.block == Decimal(str(0.3 - 18.0))
    else:
        assert bounds.block == Decimal(str(0.3 - 12.0))


def test_place_text_returns_a_completed_measured_layout_record():
    placed = place_text(placement_id="label:a", source_ref="a", content="AB",
                        inline=10, baseline_block=30, typography_role="text",
                        theme_tokens=_Theme(), font_metrics=_Font())
    assert (float(placed.bounds.inline), float(placed.bounds.block), float(placed.bounds.inline_size), float(placed.bounds.block_size)) == (10, 18, 12, 18)
    assert placed.baseline == (10, 30)
    assert placed.font_asset_identity == "sha256:test"
    assert placed.collision_domain == CollisionDomain("surface", "content")


def test_measure_text_width_keeps_font_metrics_at_the_layout_boundary():
    assert measure_text_width("AB", font_size=12, font_metrics=_Font()) == 12


def test_place_text_measures_the_transformed_spaced_painted_form():
    class Theme(_Theme):
        def text_treatment(self, role):
            family, weight, size, line_height = self.typography(role)
            return TextTreatment(family, weight, size, line_height, 0.25, "uppercase", "tabular")

    placed = place_text(placement_id="label:a", source_ref="a", content="ab",
                        inline=10, baseline_block=30, typography_role="text",
                        theme_tokens=Theme(), font_metrics=_SpacedFont())
    assert placed.content == "AB" and placed.lines == ("AB",)
    assert float(placed.bounds.inline_size) == 15
    assert placed.letter_spacing == 3 and placed.numeric_spacing == "tabular"


class _AsymmetricFont:
    """Give case changes observably different advances; scaling must be applied once."""

    content_identity = "sha256:asymmetric-glyph-widths"
    _advance = {"m": 1.0, "M": 8.0, "w": 2.0, "W": 9.0}

    def width(self, content, size, letter_spacing=0, numeric_spacing="proportional"):
        return size * sum(self._advance.get(character, 3.0) for character in content) + max(
            0, len(content) - 1
        ) * letter_spacing


class _AsymmetricTheme:
    def __init__(self, *, transform, horizontal_scale):
        self.transform = transform
        self.horizontal_scale = Decimal(str(horizontal_scale))

    def text_treatment(self, role):
        assert role == "text"
        return TextTreatment(
            "Asymmetric Sans", 400, Decimal(10), Decimal("1.4"), Decimal(0),
            self.transform, "proportional", self.horizontal_scale,
        )


@pytest.mark.parametrize("transform", ["none", "uppercase"])
@pytest.mark.parametrize("horizontal_scale", [1.0, 0.5])
@pytest.mark.parametrize("orientation,rotation", [
    ("horizontal", 0), ("rotate-cw", 90), ("rotate-ccw", -90),
])
@pytest.mark.parametrize("source_lines", [("m",), ("m", "wm")], ids=("one-line", "multi-line"))
def test_place_text_bounds_match_transformed_asymmetric_runs_scaled_once(
    transform, horizontal_scale, orientation, rotation, source_lines,
):
    source = "\n".join(source_lines)
    font = _AsymmetricFont()
    treatment = _AsymmetricTheme(transform=transform, horizontal_scale=horizontal_scale)
    painted_lines = tuple(line.upper() if transform == "uppercase" else line for line in source_lines)
    painted_content = source.upper() if transform == "uppercase" else source
    expected_width = max(
        font.width(line, 10) * horizontal_scale for line in painted_lines
    )
    expected_height = 10 * 1.4 * len(painted_lines)

    placed = place_text(
        placement_id="label:asymmetric", source_ref="subject", content=source,
        lines=source_lines, inline=17, baseline_block=43, typography_role="text",
        theme_tokens=treatment, font_metrics=font, orientation=orientation,
    )

    assert placed.content == painted_content
    assert placed.lines == painted_lines
    assert placed.source_content == source
    assert placed.font_asset_identity == font.content_identity
    assert placed.horizontal_scale == horizontal_scale
    assert placed.bounds == measured_text_bounds(
        inline=17, baseline_block=43, width=expected_width, height=expected_height,
        font_size=10, rotation=rotation,
    )


def test_place_text_rotates_the_completed_block_about_its_baseline_pivot():
    clockwise = place_text(placement_id="label:cw", source_ref="a", content="AB",
                           inline=10, baseline_block=30, typography_role="text",
                           theme_tokens=_Theme(), font_metrics=_Font(), orientation="rotate-cw")
    counterclockwise = place_text(placement_id="label:ccw", source_ref="a", content="AB",
                                  inline=10, baseline_block=30, typography_role="text",
                                  theme_tokens=_Theme(), font_metrics=_Font(), orientation="rotate-ccw")
    assert (clockwise.orientation, clockwise.rotation_degrees) == ("rotate-cw", 90)
    assert tuple(map(float, (clockwise.bounds.inline, clockwise.bounds.block,
                             clockwise.bounds.inline_size, clockwise.bounds.block_size))) == (4, 30, 18, 12)
    assert (counterclockwise.orientation, counterclockwise.rotation_degrees) == ("rotate-ccw", -90)
    assert tuple(map(float, (counterclockwise.bounds.inline, counterclockwise.bounds.block,
                             counterclockwise.bounds.inline_size, counterclockwise.bounds.block_size))) == (-2, 18, 18, 12)
