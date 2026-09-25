from chrona.presentation.layout.text import measure_text_width, place_text
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
