from chrona.presentation.icons.normalizer import IconPathCommand, NormalizedIconPath, NormalizedVectorIcon
from chrona.presentation.layout.icon_geometry import complete_icon_paths


def test_vector_icon_paths_are_transformed_and_stroke_scaled_in_layout():
    icon = NormalizedVectorIcon((10, 10), (NormalizedIconPath(
        (IconPathCommand("move", ((0.0, 0.0),)), IconPathCommand("line", ((10.0, 10.0),))),
        "stroke", 1.5, "round", "bevel"),))
    paths = complete_icon_paths(icon, (5.0, 7.0, 20.0, 30.0), 2.0)
    assert paths[0].commands == (("move", ((5.0, 7.0),)), ("line", ((25.0, 37.0),)))
    assert (paths[0].stroke_width, paths[0].line_cap, paths[0].line_join) == (3.0, "round", "bevel")
