"""The surface completion phase wires region-frame glyph completions into the shared handoff."""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from chrona.presentation.layout import surface_completion
from chrona.presentation.layout.model import LayoutDecision, Rect, RegionFrame
from chrona.presentation.layout.surface_quality import SlotPlacement

D = Decimal


class Tokens:
    def __init__(self, *, roles=()):
        self.roles = set(roles)

    def has_role(self, role):
        return role in self.roles

    def optional_color(self, _role, _property):
        return None

    def optional_number(self, _role, prop):
        assert prop in {"frameCornerRadius", "strokeWidth"}
        return None

    def optional_pattern(self, _role):
        return None

    def number(self, _role, prop):
        return {"glyphSize": D(10), "glyphPitch": D(20)}[prop]

    def symbol(self, _role):
        return {"shape": {"catalog": "fixture:border"}}

    def catalog_glyph(self, reference):
        assert reference == "fixture:border"
        return {"viewport": {"inlineSize": 10, "blockSize": 10},
                "parts": [{"data": "M0 0L10 0L10 10L0 10Z", "paint": "fill"}]}


def _node(node_id, bounds, *, parent_frame=True):
    return LayoutDecision(node_id, "column" if parent_frame else "slot",
                          Rect(*(D(value) for value in bounds)),
                          frame=RegionFrame(D(0), True, "crest"))


def _context(decisions, tokens):
    viewport = Rect(D(0), D(0), D(50), D(50))
    manifest = SimpleNamespace(decisions=tuple(decisions), fit_warnings=(), viewport=viewport)
    request = SimpleNamespace(theme_tokens=tokens, font_metrics=None, layout_manifest=manifest,
                              declared_viewport=None)
    slot = SlotPlacement("timeline", "timeline", Rect(D(0), D(0), D(50), D(50)))
    return surface_completion.SurfaceCompletionContext(
        request=request, projection=SimpleNamespace(lane_membership=None), layout_manifest=manifest,
        review_rows=(), rows=(), tracks=(), groups=(), scale=None,
        slots=(slot,), by_source={"timeline": slot}, timeline=slot, axis=slot, table=slot,
        table_bounds=(0, 0, 50, 50), timeline_bounds=(0, 0, 50, 50), column_placements=(),
        text=[], marks=[], shapes=[], relations=[], icons=[], placement_decisions=[],
        axis_tier_outcomes=(), diagnostics=[], mark_absences=(), axis_band_targets={},
        detail_panel_warnings=(), side_content_warnings=[], text_visual_warnings=[],
        visible_label_overflows=[], visible_route_fallbacks=[], visible_group_header_overflows=[],
        lane_label_suppressions=[],
    )


def _isolate_unrelated_work(monkeypatch):
    monkeypatch.setattr(surface_completion, "place_axis_band_visuals",
                        lambda *_args, **_kwargs: SimpleNamespace(icons=()))
    monkeypatch.setattr(surface_completion, "validate_background_shapes", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(surface_completion, "build_lane_emissions", lambda *_args, **_kwargs: ())
    monkeypatch.setattr(surface_completion, "complete_hosted_text_identity", lambda texts, *_args: texts)
    monkeypatch.setattr(surface_completion, "stamp_surface_fits", lambda texts, shapes, *_args: (texts, shapes))
    monkeypatch.setattr(surface_completion, "complete_catalog_patterns", lambda *_args: ())
    monkeypatch.setattr(surface_completion, "complete_canvas_texture", lambda *_args: None)
    monkeypatch.setattr(surface_completion, "complete_aligned_strokes", lambda *_args: ())


def test_surface_completion_wires_rect_then_glyph_per_node_and_preserves_parent_order(monkeypatch):
    _isolate_unrelated_work(monkeypatch)
    parent = _node("title", (D(-15), D(-10), D(80), D(80)))
    child = _node("title-detail", (D(5), D(5), D(35), D(35)))
    tokens = Tokens(roles={"region-frame-crest", "frame-glyph-crest"})

    completed = surface_completion.complete_surface_layout(
        _context((parent, child), tokens)).placement

    assert [(shape.placement_id, shape.kind, shape.source_ref) for shape in completed.shapes] == [
        ("region-frame:title", "Rect", "layout-node:title"),
        ("frame-glyph:title", "Glyph", "layout-node:title"),
        ("region-frame:title-detail", "Rect", "layout-node:title-detail"),
        ("frame-glyph:title-detail", "Glyph", "layout-node:title-detail"),
    ]
    shapes = {shape.placement_id: shape for shape in completed.shapes}
    assert shapes["region-frame:title"].bounds == shapes["frame-glyph:title"].bounds
    assert shapes["frame-glyph:title"].visual_role == "frame-glyph-crest"
    assert shapes["frame-glyph:title"].slot_id == "frame-glyph-slot:title"
    assert [slot.slot_id for slot in completed.slots] == [
        "timeline", "frame:title", "frame:title-detail",
        "frame-glyph-slot:title", "frame-glyph-slot:title-detail",
    ]
    assert completed.canvas_bounds == Rect(D(-15), D(-10), D(80), D(80))
    assert completed.diagnostics == ()


def test_surface_completion_without_frame_roles_matches_a_profile_without_frames(monkeypatch):
    _isolate_unrelated_work(monkeypatch)
    framed = (_node("title", (D(-15), D(-10), D(80), D(80))),)
    plain = (LayoutDecision("title", "slot", Rect(D(-15), D(-10), D(80), D(80))),)

    no_roles = surface_completion.complete_surface_layout(
        _context(framed, Tokens())).placement
    no_frames = surface_completion.complete_surface_layout(
        _context(plain, Tokens())).placement

    assert no_roles.shapes == no_frames.shapes == ()
    assert no_roles.slots == no_frames.slots
    assert no_roles.diagnostics == no_frames.diagnostics == ()
    assert no_roles.canvas_bounds == no_frames.canvas_bounds


def test_glyph_only_role_expands_the_canvas_without_a_region_frame_rect(monkeypatch):
    _isolate_unrelated_work(monkeypatch)
    decision = _node("title", (D(-15), D(-10), D(80), D(80)))
    tokens = Tokens(roles={"frame-glyph-crest"})

    completed = surface_completion.complete_surface_layout(_context((decision,), tokens)).placement

    assert [(shape.placement_id, shape.kind) for shape in completed.shapes] == [
        ("frame-glyph:title", "Glyph"),
    ]
    assert completed.canvas_bounds == Rect(D(-15), D(-10), D(80), D(80))
    assert [slot.slot_id for slot in completed.slots] == ["timeline", "frame-glyph-slot:title"]


def test_surface_completion_propagates_whole_glyph_omission_without_slots(monkeypatch):
    _isolate_unrelated_work(monkeypatch)
    no_content = LayoutDecision("empty", "slot", Rect(D(0), D(0), D(100), D(100)),
                                frame=RegionFrame(D(0), False, "crest"))
    too_small = _node("small", (D(0), D(0), D(25), D(40)))
    tokens = Tokens(roles={"frame-glyph-crest"})

    completed = surface_completion.complete_surface_layout(
        _context((no_content, too_small), tokens)).placement

    assert completed.shapes == ()
    assert [slot.slot_id for slot in completed.slots] == ["timeline"]
    assert completed.diagnostics == (
        "I_LAYOUT_FRAME_GLYPH_OMITTED:empty:no-content",
        "I_LAYOUT_FRAME_GLYPH_OMITTED:small:too-small",
    )
