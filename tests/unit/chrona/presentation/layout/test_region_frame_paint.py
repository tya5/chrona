"""Named region-frame roles keep Layout identity and geometry role-specific (#1165)."""
from decimal import Decimal

from chrona.presentation.layout.model import LayoutDecision, Rect, RegionFrame
from chrona.presentation.layout.region_frame import complete_region_frames

D = Decimal


class Tokens:
    def __init__(self, roles):
        self.roles = roles

    def has_role(self, role):
        return role in self.roles

    def optional_color(self, role, prop):
        return self.roles[role].get(prop)

    def optional_number(self, role, prop):
        value = self.roles[role].get(prop)
        return None if value is None else D(str(value))

    def optional_pattern(self, role):
        return self.roles[role].get("pattern")


def decision(node_id, paint=None, *, inset=0):
    return LayoutDecision(
        node_id, "row", Rect(D(0), D(0), D(100), D(60)),
        frame=RegionFrame(D(inset), True, paint),
    )


def test_sibling_frames_keep_distinct_roles_and_profile_order():
    frames = complete_region_frames(
        Tokens({
            "region-frame-plaque": {"fill": "#111111", "stroke": "#222222", "strokeWidth": 2},
            "region-frame-board": {"fill": "#eeeeee", "frameCornerRadius": 8},
        }),
        (decision("outer", "plaque"), decision("inner", "board", inset=2)),
    )

    assert [shape.placement_id for shape in frames.shapes] == ["region-frame:outer", "region-frame:inner"]
    assert [shape.visual_role for shape in frames.shapes] == ["region-frame-plaque", "region-frame-board"]
    assert [shape.corner_radius for shape in frames.shapes] == [0, 8]
    assert [shape.bounds for shape in frames.shapes] == [
        Rect(D(1), D(1), D(98), D(58)), Rect(D(2), D(2), D(96), D(56)),
    ]


def test_missing_named_role_omits_only_that_frame_even_without_the_base_role():
    frames = complete_region_frames(
        Tokens({"region-frame-rule": {"fill": "#aa8800"}}),
        (decision("missing", "plaque"), decision("present", "rule"), decision("unnamed")),
    )

    assert [shape.placement_id for shape in frames.shapes] == ["region-frame:present"]
    assert [shape.visual_role for shape in frames.shapes] == ["region-frame-rule"]
    assert frames.diagnostics == ()


def test_unnamed_frame_keeps_legacy_role_projection_and_geometry():
    frames = complete_region_frames(Tokens({"region-frame": {"stroke": "#111111", "strokeWidth": 2}}),
                                    (decision("legacy"),))

    shape, = frames.shapes
    assert shape.placement_id == "region-frame:legacy"
    assert shape.visual_role is None
    assert shape.bounds == Rect(D(1), D(1), D(98), D(58))
