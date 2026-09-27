from pathlib import Path


def test_scene_builder_consumes_layout_paths_without_reconstructing_geometry():
    source = Path("src/chrona/presentation/scene/v05_builder.py").read_text()
    forbidden = ("variant_symbol(", "glyph_parts(", "symbol_geometry(",
                 "_complete_icon_paths(", "icon_stroke_scale", "icon_vector")
    assert not [term for term in forbidden if term in source]
    assert "planned_mark.symbol_parts" in source
    assert "placed.completed_paths" in source
    assert "_glyph_part_paint(" not in source
