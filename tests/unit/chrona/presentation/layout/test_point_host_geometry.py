from dataclasses import replace
from datetime import date
from decimal import Decimal as D

from chrona.presentation.layout.mark_geometry import SymbolPartPlacement
from chrona.presentation.layout.model import PointHostMode, Rect
from chrona.presentation.layout.point_host_geometry import complete_hosted_point_geometry, translate_point_block
from chrona.presentation.layout.point_hosting import PointHostPlan, resolve_point_host_plan
from chrona.presentation.layout.surface_quality import MarkPlacement, PathCommand
from chrona.presentation.model.projection import ReviewItem, ReviewProjection


def _marks():
    commands = (PathCommand("move", ((10., 100.),)),
                PathCommand("quadratic", ((14., 104.), (10., 108.))))
    point = MarkPlacement("planned:p", "p", Rect(D(6), D(100), D(8), D(8)),
        (10., 104.), (10., 104.), mark_shape="point", paint_order=100,
        path_commands=commands, symbol_parts=(SymbolPartPlacement(commands),),
        lane_row_id="child", lane_member_id="p", lane_source_kind="primary",
        pattern_origin=(6., 100.))
    span = MarkPlacement("planned:a", "a", Rect(D(0), D(10), D(30), D(4)),
        (0., 12.), (30., 12.), paint_order=100)
    return point, span


def _plan():
    span = ReviewItem("a", "A", "span", {"start": date(2026, 1, 1),
        "end": date(2026, 1, 30)}, None, None, ())
    point = ReviewItem("p", "P", "point", {"at": date(2026, 1, 10)},
        None, None, (), parent_id="a")
    projection = ReviewProjection((span, point), (date(2026, 1, 1), date(2026, 2, 1)), (), ())
    return resolve_point_host_plan(projection, as_of=None, mode=PointHostMode.SPAN_WHEN_INSIDE)


def test_complete_geometry_moves_all_point_operands_but_not_dates_or_semantic_identity():
    point, span = _marks()
    placed, same_span = complete_hosted_point_geometry(_plan(), (point, span))
    assert same_span is span
    assert placed.bounds == Rect(D(6), D(8), D(8), D(8))
    assert placed.start_port == placed.end_port == (10., 12.)
    assert placed.path_commands[1].points == ((14., 12.), (10., 16.))
    assert placed.symbol_parts[0].commands == placed.path_commands
    assert placed.pattern_origin == (6., 8.)
    assert placed.physical_host.placement_id == "planned:a"
    assert placed.physical_host.row_id == "a"
    assert (placed.lane_row_id, placed.lane_member_id, placed.source_ref) == ("child", "p", "p")
    assert placed.paint_order > span.paint_order


def test_zero_origin_and_final_frame_use_identical_relative_offset():
    point, span = _marks()
    source_point = translate_point_block(point, -100.)
    source_span = replace(span, bounds=replace(span.bounds, block=D(0)),
                          start_port=(0., 2.), end_port=(30., 2.))
    provisional = complete_hosted_point_geometry(_plan(), (source_point, source_span), source_frame=True)[0]
    translated = translate_point_block(provisional, 10.)
    final = complete_hosted_point_geometry(_plan(), (point, span))[0]
    assert translated.bounds == final.bounds
    assert translated.start_port == final.start_port and translated.end_port == final.end_port
    assert translated.path_commands == final.path_commands
    assert translated.symbol_parts == final.symbol_parts
    assert translated.pattern_origin == final.pattern_origin
    assert provisional.physical_host is None and final.physical_host is not None


def test_default_off_returns_the_original_inventory_without_replacing_marks():
    marks = _marks()
    assert complete_hosted_point_geometry(PointHostPlan(), marks) is marks
