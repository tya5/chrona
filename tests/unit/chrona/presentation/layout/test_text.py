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
