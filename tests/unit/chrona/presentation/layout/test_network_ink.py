from decimal import Decimal
from types import SimpleNamespace

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.network_ink import network_ink_bounds
from chrona.presentation.layout.surface_quality import PathCommand
from chrona.presentation.layout.relation_terminals import marker_geometry


def _rect(x, y, width, height):
    return Rect(*(Decimal(str(value)) for value in (x, y, width, height)))


class _Theme:
    def __init__(self, *, stroke_width=2, alignment="outside"):
        self.stroke_width = stroke_width
        self.alignment = alignment

    def optional_color(self, role, name):
        return "#000000" if name == "stroke" else None

    def optional_number(self, role, name):
        return self.stroke_width if name == "strokeWidth" else None

    def optional_choice(self, role, name, choices):
        return self.alignment if name == "strokeAlign" else None

    def number(self, role, name):
        return self.stroke_width


def test_network_ink_includes_node_stroke_alignment_text_and_completed_shape_geometry():
    node = SimpleNamespace(is_container=False, bounds=_rect(10, 20, 30, 12))
    container = SimpleNamespace(is_container=True, bounds=_rect(-100, -100, 300, 300))
    text = SimpleNamespace(bounds=_rect(12, 5, 28, 8))
    shape = SimpleNamespace(
        semantic_id="groupHeaderBand", visual_role=None, bounds=_rect(45, 10, 20, 10),
        path_commands=(PathCommand("move", ((48, 8),)), PathCommand("line", ((70, 15),))),
        points=(), symbol_parts=(), paint_channels=None,
    )

    ink = network_ink_bounds((node, container), (text,), (shape,), (), _Theme())

    assert ink == (_rect(8, 18, 34, 16), _rect(12, 5, 28, 8), _rect(37, 0, 41, 28))


def test_network_ink_accounts_for_stroked_route_and_completed_terminal_outlines():
    marker = marker_geometry({"shape": "open-triangle", "headLength": 8,
                              "headWidth": 8, "attachmentOffset": 0}, stroke_width=2)
    relation = SimpleNamespace(
        semantic_id="networkEdge", suppressed=False,
        points=((10.0, 20.0), (50.0, 20.0)),
        path_commands=(PathCommand("move", ((10.0, 20.0),)),
                       PathCommand("line", ((50.0, 20.0),))),
        marker_start=marker, marker_end=None,
    )

    ink = network_ink_bounds((), (), (), (relation,), _Theme(stroke_width=2))

    assert ink[0] == _rect(9, 19, 42, 2)
    assert len(ink) == 2
    assert float(ink[1].inline) < 10
    assert float(ink[1].inline + ink[1].inline_size) > 10
    assert float(ink[1].block) < 20
    assert float(ink[1].block + ink[1].block_size) > 20


def test_network_ink_theme_free_geometry_has_no_stroke_expansion():
    node = SimpleNamespace(is_container=False, bounds=_rect(1, 2, 3, 4))
    shape = SimpleNamespace(semantic_id="groupHeaderBand", visual_role=None,
                            bounds=_rect(5, 6, 7, 8), path_commands=(), points=(),
                            symbol_parts=(), paint_channels=None)

    assert network_ink_bounds((node,), (), (shape,), (), None) == (
        _rect(1, 2, 3, 4), _rect(5, 6, 7, 8))
