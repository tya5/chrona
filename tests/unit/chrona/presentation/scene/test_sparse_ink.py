from chrona.presentation.scene.sparse_ink import selected_symbol_ink


def _symbol(identifier, commands, paint):
    return {"id": identifier, "paint": paint,
            "symbol": {"outline": [{"kind": kind, "points": [list(point) for point in points]}
                                  for kind, *points in commands]}}


def _closed(points):
    first, *rest = points
    return [("move", first), *(('line', point) for point in rest), ("line", first)]


RING = _closed([(0, 0), (100, 0), (100, 60), (0, 60)]) + _closed(
    [(10, 10), (10, 50), (90, 50), (90, 10)])


def test_fill_hole_does_not_count_as_ink_contact():
    ring = _symbol("ring", RING, {"fill": "#222222", "opacity": 1})
    ink, unreadable = selected_symbol_ink((ring,), (20, 20, 60, 20))
    assert ink == [] and unreadable is None


def test_fill_area_contact_returns_the_selected_ink():
    part = _symbol("fill", _closed([(0, 0), (100, 0), (100, 60), (0, 60)]),
                   {"fill": "#222222", "opacity": 1})
    assert selected_symbol_ink((part,), (20, 20, 60, 20)) == ([('fill', "#222222", 1.0)], None)


def test_stroke_contact_uses_half_width_and_miss_does_not_contribute():
    part = _symbol("stroke", [("move", (5, 0)), ("line", (5, 60))],
                   {"stroke": "#222222", "strokeWidth": 4, "opacity": 1})
    assert selected_symbol_ink((part,), (6.5, 20, 30, 10)) == ([('stroke', "#222222", 1.0)], None)
    assert selected_symbol_ink((part,), (7.5, 20, 30, 10)) == ([], None)


def test_malformed_touching_outline_returns_unreadable_identity():
    part = _symbol("broken", [("arc", (5, 0))], {"fill": "#222222", "opacity": 1})
    assert selected_symbol_ink((part,), (0, 0, 10, 10)) == ([], "broken")


def test_bad_opacity_fails_closed_only_when_its_ink_touches():
    part = _symbol("bad-opacity", _closed([(0, 0), (100, 0), (100, 60), (0, 60)]),
                   {"fill": "#222222", "opacity": 2})
    assert selected_symbol_ink((part,), (20, 20, 60, 20)) == ([], "bad-opacity")


def test_missing_paint_facts_return_the_legacy_fallback_identity():
    assert selected_symbol_ink(({"symbol": {"outline": []}},), (0, 0, 1, 1),
                               unreadable_identity="annotation-artwork") == (
        [], "annotation-artwork")


def test_fallback_identity_is_owned_by_the_caller_not_annotation_semantics():
    assert selected_symbol_ink(({},), (0, 0, 1, 1)) == ([], "sparse-ink")
    assert selected_symbol_ink(({},), (0, 0, 1, 1), unreadable_identity="frame-glyph") == ([], "frame-glyph")
