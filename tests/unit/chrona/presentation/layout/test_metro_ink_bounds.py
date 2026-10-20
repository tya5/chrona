"""Route paint bounds contain exact Q extrema, not only four sampled chords."""
import pytest

from chrona.presentation.layout.network_ink import relation_paint_bounds
from chrona.presentation.layout.path_geometry import flatten_path
from chrona.presentation.layout.surface_quality import PathCommand, RelationPlacement
from tests.unit.chrona.presentation.layout.test_network_routes import _theme


def test_network_paint_bounds_include_a_quadratic_extremum_between_legacy_samples():
    commands = (PathCommand("move", ((0, 0),)),
                PathCommand("quadratic", ((10, 10), (20, 3))))
    relation = RelationPlacement("edge", "a:output", "b:input", ((0, 0), (20, 3)),
        semantic_id="networkEdge", path_commands=commands)
    left, top, width, height = relation_paint_bounds(relation, _theme())
    maximum = 100 / 17  # y(t)=20t-17t², derivative root t=10/17.
    assert max(point[1] for point in flatten_path(commands)) < maximum
    assert top + height == pytest.approx(maximum + 0.5)
    assert (left, top, width) == pytest.approx((-0.5, -0.5, 21.0))
