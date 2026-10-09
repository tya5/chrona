"""Owner-local diagnostics name the input operands that failed Layout checks."""
from datetime import date
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.balloon_geometry import balloon_outline
from chrona.presentation.layout.comparison_marks import comparison_marks
from chrona.presentation.layout.icon_geometry import complete_icon_paths
from chrona.presentation.layout.image_slice_geometry import image_slice_tiles
from chrona.presentation.layout.labels import LabelRect
from chrona.presentation.layout.mark_geometry import glyph_parts, symbol_parts
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.path_geometry import open_span_path, rounded_orthogonal_path
from chrona.presentation.layout.pattern_placement import complete_pattern_placement
from chrona.presentation.layout.ports import connector_boundary_ports
from chrona.presentation.layout.presentation import MarkBandFrame, MarkGeometry
from chrona.presentation.layout.relation_terminals import marker_geometry
from chrona.presentation.layout.surface_quality import MarkPlacement, ScalePlacement
from chrona.presentation.model.diagnostic_sources import DiagnosticSubject
from chrona.presentation.model.projection import ObservationState


def test_mark_geometry_diagnostics_name_bad_shape_and_glyph_operands() -> None:
    with pytest.raises(ValueError, match=r"E_THEME_TOKEN_TYPE:.*shape\.catalog='missing-glyph'"):
        symbol_parts({"shape": {"catalog": "missing-glyph"}}, (0, 0, 10, 10), catalog_glyphs={})

    with pytest.raises(ValueError, match=r"E_THEME_TOKEN_TYPE:.*viewport.*\(0, 10\)"):
        glyph_parts({"viewport": {"inlineSize": 0, "blockSize": 10}, "parts": []}, (0, 0, 10, 10))

    with pytest.raises(ValueError, match=r"E_PRESENTATION_PRIMITIVE_INVALID:.*width=-1"):
        symbol_parts({"shape": "diamond"}, (0, 0, -1, 10))


def test_composed_marks_keep_exact_project_subject_without_changing_geometry() -> None:
    from chrona.presentation.layout.mark_geometry import compose_item_marks

    start, end = date(2026, 1, 1), date(2026, 1, 5)
    frame = MarkBandFrame.zero_origin(
        ScalePlacement("surface", "time", start, end, 0, 100, 0, 25), 20,
        {role: MarkGeometry(.5, .25, index, 0) for index, role in enumerate(("planned", "actual", "missing-actual"))},
    )
    item = SimpleNamespace(object_id="task/17", title="Exact comparison variant", source_type="point",
                           planned={"at": start}, actual={}, observation_state=ObservationState.UNAVAILABLE)
    result = compose_item_marks(item=item, instance_id="variant-2", source_kind="planned",
                                frame=frame, as_of=None,
                                theme_tokens=SimpleNamespace(variant_symbol=lambda _role: {"shape": "diamond"}),
                                slot_id="timeline")

    assert len(result.marks) == 1
    mark = result.marks[0]
    assert mark.placement_id == "planned:variant-2"
    assert mark.source_ref == item.object_id
    assert mark.bounds.inline_size == mark.bounds.block_size == 10
    assert mark.subjects == (DiagnosticSubject.project_object(item.object_id, item.title),)


def test_comparison_diagnostic_names_invalid_mode() -> None:
    with pytest.raises(ValueError, match=r"E_PRESENTATION_COMPARISON_MODE:.*comparison_mode='sideways'"):
        comparison_marks((), comparison_mode="sideways")


def test_mark_input_diagnostic_names_source_and_bad_planned_dates() -> None:
    item = SimpleNamespace(object_id="task-17", source_type="span",
                           planned={"start": date(2026, 1, 2), "end": date(2026, 1, 1)}, actual={})
    with pytest.raises(ValueError, match=r"E_PRESENTATION_MARK_INPUT:.*task-17.*planned.start"):
        comparison_marks((item,), comparison_mode="stacked")


def test_path_and_port_diagnostics_identify_bad_segment_or_endpoint() -> None:
    with pytest.raises(ValueError, match=r"E_LAYOUT_PATH_INPUT:.*segment 0.*diagonal"):
        rounded_orthogonal_path(((0, 0), (2, 3)), 0)
    with pytest.raises(ValueError, match=r"E_LAYOUT_PATH_INPUT:.*inline_size=0"):
        open_span_path(inline=0, block=0, inline_size=0, block_size=5, radius=0)

    mark = MarkPlacement("planned:item", "item", Rect(0, 0, 10, 10), (0, 5), (10, 5), mark_shape="point")
    with pytest.raises(ValueError, match=r"E_PRESENTATION_ANCHOR_MISSING:.*endpoint='middle'"):
        connector_boundary_ports(mark, "middle", (20, 20))


def test_terminal_diagnostic_names_the_invalid_closed_token() -> None:
    with pytest.raises(ValueError, match=r"E_THEME_TOKEN_TYPE:.*shape='triangle-ish'"):
        marker_geometry({"shape": "triangle-ish", "headLength": 4, "headWidth": 4})


def test_pattern_layout_error_carries_the_bad_primitive_field() -> None:
    pattern = {
        "tile": {"inlineSize": 10, "blockSize": 10}, "angle": 0,
        "densityBasisPoints": 1000,
        "primitives": [{"kind": "circle", "cx": 2, "cy": 2, "radius": 1}],
    }
    with pytest.raises(LayoutError, match=r"E_PRESENTATION_PRIMITIVE_INVALID:.*primitives\[0\].*radius=0"):
        complete_pattern_placement(
            {**pattern, "primitives": [{"kind": "circle", "cx": 2, "cy": 2, "radius": 0}]},
            Rect(0, 0, 20, 20),
        )


def test_image_slice_diagnostic_names_invalid_source_viewport() -> None:
    with pytest.raises(ValueError, match=r"E_LAYOUT_IMAGE_SLICE_GEOMETRY:.*viewport=\(0, 10\)"):
        image_slice_tiles((0, 0, 20, 20), viewport=(0, 10), slice_insets=(1, 1, 1, 1))


def test_icon_diagnostic_names_invalid_normalized_viewport() -> None:
    with pytest.raises(ValueError, match=r"E_PRESENTATION_PRIMITIVE_INVALID:.*viewport dimensions \(0, 10\)"):
        complete_icon_paths(SimpleNamespace(viewport=(0, 10), paths=()), (0, 0, 10, 10), 1)


def test_balloon_diagnostic_names_invalid_corner_geometry() -> None:
    with pytest.raises(ValueError, match=r"E_LAYOUT_BALLOON_GEOMETRY:.*corner_radius=-1"):
        balloon_outline(LabelRect(0, 0, 20, 10), (10, -5), corner_radius=-1, tail_base=4)
