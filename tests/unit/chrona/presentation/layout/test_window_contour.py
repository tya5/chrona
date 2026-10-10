from decimal import Decimal

import pytest

import chrona.presentation.layout.filled_contour as contour_ops
from chrona.presentation.layout.filled_contour import WindowContourError, clip_span_contour
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.surface_quality import PathCommand as C, is_closed_stroke_contour


def _rect(x, y, width, height):
    points = ((x, y), (x + width, y), (x + width, y + height),
              (x, y + height), (x, y))
    return (C("move", (points[0],)), *(C("line", (point,)) for point in points[1:]))


def _host(x, y, width, height):
    return Rect(*(Decimal(str(value)) for value in (x, y, width, height)))


def _coordinates(commands):
    return tuple(point for command in commands for point in command.points)


def _rounded():
    return (C("move", ((0.0, 2.0),)), C("line", ((2.0, 0.0),)),
            C("quadratic", ((4.0, 0.0), (4.0, 2.0))), C("line", ((4.0, 8.0),)),
            C("quadratic", ((4.0, 10.0), (2.0, 10.0))), C("line", ((0.0, 8.0),)),
            C("line", ((0.0, 2.0),)))


@pytest.mark.parametrize(
    ("cut_start", "cut_finish", "expected_apices"),
    [(True, False, ((2.5, 5.0),)), (False, True, ((17.5, 5.0),)),
     (True, True, ((2.5, 5.0), (17.5, 5.0)))],
)
def test_rectangle_cut_notches_have_exact_relative_geometry(cut_start, cut_finish, expected_apices):
    original = _rect(0, 0, 20, 10)
    result = clip_span_contour(original, _host(0, 0, 20, 10), cut_start=cut_start,
                               cut_finish=cut_finish, source_ref="span:7", facet="actual")

    coordinates = _coordinates(result)
    assert all(apex in coordinates for apex in expected_apices)
    assert is_closed_stroke_contour(result)
    for edge in ([0.0] if cut_start else []) + ([20.0] if cut_finish else []):
        assert {(edge, 2.5), (edge, 7.5)}.issubset(set(coordinates))


def test_rounded_contour_keeps_uncut_quadratic_edge_and_no_cut_identity():
    original = _rounded()
    unchanged = clip_span_contour(original, _host(-1, -1, 10, 12), cut_start=False,
                                  cut_finish=False, source_ref="span:r", facet="planned")
    assert unchanged is original

    clipped = clip_span_contour(original, _host(0, 0, 4, 10), cut_start=True,
                                cut_finish=False, source_ref="span:r", facet="planned")
    assert is_closed_stroke_contour(clipped)
    assert any(command.kind == "quadratic" and command.points[-1][0] == 4.0
               for command in clipped)
    assert (1.0, 5.0) in _coordinates(clipped)


def test_unnotched_contour_is_intersected_with_host():
    original = _rect(-5, 0, 20, 10)
    clipped = clip_span_contour(original, _host(0, 0, 10, 10), cut_start=False,
                                cut_finish=False, source_ref="span:c", facet="actual")
    assert is_closed_stroke_contour(clipped)
    assert set(_coordinates(clipped)) == {(0.0, 0.0), (10.0, 0.0),
                                          (10.0, 10.0), (0.0, 10.0)}


def test_narrow_host_has_no_pixel_minimum_for_notch_depth():
    result = clip_span_contour(_rect(0, 0, 0.4, 10), _host(0, 0, 0.4, 10),
                               cut_start=True, cut_finish=False,
                               source_ref="span:narrow", facet="actual")
    assert any(x == pytest.approx(0.1) and y == pytest.approx(5.0)
               for x, y in _coordinates(result))
    assert min(x for x, _ in _coordinates(result)) >= 0.0
    assert max(x for x, _ in _coordinates(result)) <= 0.4

    tiny_width = 0.00001
    tiny = clip_span_contour(_rect(0, 0, tiny_width, 1), _host(0, 0, tiny_width, 1),
                             cut_start=True, cut_finish=False,
                             source_ref="span:tiny", facet="actual")
    tiny_points = _coordinates(tiny)
    assert any(px == pytest.approx(tiny_width / 4) and py == pytest.approx(0.5)
               for px, py in tiny_points)
    assert min(px for px, _ in tiny_points) >= 0.0
    assert max(px for px, _ in tiny_points) <= tiny_width


def test_translated_nonbinary_narrow_host_both_cuts_stay_strictly_inside():
    x, y, width, height = 0.1, 3.7, 0.4, 10.0
    result = clip_span_contour(_rect(x, y, width, height), _host(x, y, width, height),
                               cut_start=True, cut_finish=True,
                               source_ref="span:translated", facet="actual")
    coordinates = _coordinates(result)
    xs = [point[0] for point in coordinates]
    ys = [point[1] for point in coordinates]
    assert min(xs) >= x and max(xs) <= x + width
    assert min(ys) >= y and max(ys) <= y + height
    assert any(px == pytest.approx(x + 0.05) and py == pytest.approx(y + height / 2)
               for px, py in coordinates)
    assert any(px == pytest.approx(x + width - 0.05) and py == pytest.approx(y + height / 2)
               for px, py in coordinates)


def test_contained_uncut_identity_does_not_require_native_pathops(monkeypatch):
    original = _rect(0.1, 0.2, 0.4, 3.0)
    monkeypatch.setattr(contour_ops, "pathops", None)
    assert clip_span_contour(original, _host(0, 0, 1, 4), cut_start=False,
                             cut_finish=False, source_ref="span:contained",
                             facet="planned") is original


@pytest.mark.parametrize("failure", ["unavailable", "operation"])
def test_path_backend_failures_are_bounded(failure, monkeypatch):
    if failure == "unavailable":
        monkeypatch.setattr(contour_ops, "pathops", None)
    else:
        def fail(*_args, **_kwargs):
            raise RuntimeError("private backend failure")

        monkeypatch.setattr(contour_ops.pathops, "op", fail)
    with pytest.raises(WindowContourError) as caught:
        clip_span_contour(_rect(0, 0, 4, 4), _host(0, 0, 4, 4), cut_start=True,
                          cut_finish=False, source_ref="span:backend", facet="actual")
    assert (caught.value.stage, caught.value.reason) in {
        ("intersection", "operation-failed"), ("notch", "operation-failed")}
    assert caught.value.source_ref == "span:backend"
    assert caught.value.facet == "actual"
    assert "private backend failure" not in str(caught.value)


def test_nonfinite_contour_fails_with_bounded_identity():
    invalid = _rect(0, 0, 2, 2)[:-2] + (C("line", ((float("inf"), 2.0),)),
                                       C("line", ((0, 0),)))
    with pytest.raises(WindowContourError) as caught:
        clip_span_contour(invalid, _host(0, 0, 2, 2), cut_start=True,
                          cut_finish=False, source_ref="span:bad", facet="actual")
    assert (caught.value.stage, caught.value.reason) == ("input", "nonfinite")
    assert "inf" not in str(caught.value)
    assert isinstance(caught.value, LayoutError)
    assert caught.value.diagnostic_id == "E_LAYOUT_WINDOW_CLIP"
    assert caught.value.path == "/layout/windowContour"
    assert "source_ref='span:bad'" in caught.value.detail


@pytest.mark.parametrize("host", [
    Rect(Decimal(0), Decimal(0), Decimal(0), Decimal(2)),
    Rect(Decimal(0), Decimal(0), Decimal(2), Decimal(-1)),
    Rect(Decimal(0), Decimal(0), Decimal("Infinity"), Decimal(1)),
])
def test_nonpositive_or_nonfinite_host_fails_at_input(host):
    with pytest.raises(WindowContourError) as caught:
        clip_span_contour(_rect(0, 0, 2, 2), host, cut_start=True,
                          cut_finish=False, source_ref="span:host", facet="actual")
    assert caught.value.diagnostic_id == "E_LAYOUT_WINDOW_CLIP"
    assert caught.value.stage == "input"


def test_output_outside_authored_host_fails_closed(monkeypatch):
    original_world = contour_ops._host_world

    def outside(commands, x, y, width, height):
        result = original_world(commands, x, y, width, height)
        return tuple(C(command.kind, tuple((px + 0.01, py) for px, py in command.points))
                     for command in result)

    monkeypatch.setattr(contour_ops, "_host_world", outside)
    with pytest.raises(WindowContourError) as caught:
        clip_span_contour(_rect(0, 0, 4, 4), _host(0, 0, 4, 4), cut_start=True,
                          cut_finish=False, source_ref="span:outside", facet="actual")
    assert (caught.value.stage, caught.value.reason) == ("output", "outside-host")
