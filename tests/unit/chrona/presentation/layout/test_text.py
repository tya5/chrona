from chrona.presentation.layout.text import place_text


class _Theme:
    def typography(self, role):
        assert role == "text"
        return ("Test Sans", 400, 12, 1.5)


class _Font:
    content_identity = "sha256:test"
    def width(self, content, size):
        return len(content) * size / 2


def test_place_text_returns_a_completed_measured_layout_record():
    placed = place_text(placement_id="label:a", source_ref="a", content="AB",
                        inline=10, baseline_block=30, typography_role="text",
                        theme_tokens=_Theme(), font_metrics=_Font())
    assert (float(placed.bounds.inline), float(placed.bounds.block), float(placed.bounds.inline_size), float(placed.bounds.block_size)) == (10, 18, 12, 18)
    assert placed.baseline == (10, 30)
    assert placed.font_asset_identity == "sha256:test"
