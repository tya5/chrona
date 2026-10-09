from datetime import date
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

from chrona.presentation.layout.mark_geometry import compose_item_marks
from chrona.presentation.layout import surface_completion
from chrona.presentation.layout.presentation import MarkBandFrame, MarkGeometry
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_quality import RowPlacement, ScalePlacement, SlotPlacement
from chrona.presentation.layout.surface_quality import TextPlacement, VisualRequest
from chrona.presentation.layout.surface_visuals import place_text_visuals
from chrona.presentation.layout import surface_annotations
from chrona.presentation.model.diagnostic_sources import DiagnosticProvenance, DiagnosticSubject
from chrona.presentation.model.projection import ObservationState, ReviewItem, ReviewProjection, ReviewRowProjection
from chrona.presentation.scene.v05_builder import build_scene_input, compose_review_surface
from tests.unit.chrona.presentation.scene.test_v05_builder import (
    _Font, _manifest, _theme, _title_measurement, surface_content,
)
from tests.support import synthetic_review as sr
from chrona.presentation.layout.sources import MeasuredSources, SourceInput
from chrona.presentation.layout.surface_composer import compose_surface_layout
from chrona.presentation.layout.surface_quality import SurfaceLayoutRequest
from chrona.presentation.model.presentation_contract import normalize_presentation_input
from chrona.presentation.model.theme_tokens import ThemeTokenView


def _surface(item, content, rows=()):
    projection = ReviewProjection((item,), (date(2026, 1, 1), date(2026, 2, 1)), (), (), rows=rows)
    measurement = MeasuredSources(
        {"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
        {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
         "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8),
         "timeline.mark.blockSize": Decimal(8)},
    )
    value = build_scene_input(projection=projection, surface_content=content,
                              layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"),
                              resolved_theme=_theme(), font_metrics=_Font(), measured_sources=measurement,
                              capabilities={"svg": True})
    return compose_review_surface(value)


def test_open_actual_diagnostics_keep_exact_layout_string_and_typed_project_subject():
    scale = ScalePlacement("surface", "primary", date(2026, 1, 1), date(2026, 1, 10),
                           100.0, 190.0, 100.0, 10.0)
    roles = {
        "planned": MarkGeometry(0.5, 0.25, 0, 0.0),
        "snapshot": MarkGeometry(0.5, 0.25, 0, 0.0),
        "actual": MarkGeometry(0.4, 0.6, 1, 0.0),
        "missing-actual": MarkGeometry(0.4, 0.6, 2, 0.0),
    }
    frame = MarkBandFrame.zero_origin(scale, 10.0, roles)
    theme = SimpleNamespace(variant_symbol=lambda _role: {"shape": "circle"})
    item = SimpleNamespace(
        object_id="team/a~:42", title="Firmware / launch",
        source_type="span", planned={"start": date(2026, 1, 1), "end": date(2026, 1, 4)},
        actual={"start": date(2026, 1, 2), "openUntil": "asOf"},
        observation_state=ObservationState.RECORDED,
    )

    result = compose_item_marks(item=item, instance_id="row:team/a~:42", source_kind="combined",
                                frame=frame, as_of=None, theme_tokens=theme, slot_id="timeline")

    diagnostic = "W_LAYOUT_OPEN_ACTUAL_AS_OF_REQUIRED:team/a~:42"
    assert result.diagnostics == (diagnostic,)
    assert result.diagnostic_provenance == (DiagnosticProvenance(
        diagnostic, (DiagnosticSubject("/objects/team~1a~0:42", "Firmware / launch"),)),)


def test_scene_builder_projects_object_primitive_subjects_without_scene_identity_changes():
    item = ReviewItem("team/a~:42", "Firmware / launch", "span",
                      {"start": date(2026, 1, 1), "end": date(2026, 2, 1)}, None, None,
                      ("planned", "missing-actual"), observation_state=ObservationState.DUE_UNOBSERVED)
    surface = _surface(item, surface_content(( ("name", "Name"), ),
                                             ((item.object_id, "name", "Firmware"),)))

    expected = DiagnosticSubject.project_object(item.object_id, item.title)
    owners = {record.primitive_id: record.subjects for record in surface.primitive_provenance}
    assert owners[f"planned:{item.object_id}"] == (expected,)
    assert owners[f"missing-actual:{item.object_id}"] == (expected,)
    assert owners[f"cell:{item.object_id}:name"] == (expected,)
    assert not surface.diagnostic_provenance
    assert all(primitive.scene_id in {item.primitive_id for item in surface.primitive_provenance}
               for primitive in surface.primitives if primitive.source_ref == item.object_id
               and primitive.purpose in {"planned", "missingActual", "tableCell"})
    # The sidecar is absent from the passive Scene primitive document facts.
    assert all(not hasattr(primitive, "subjects") for primitive in surface.primitives)


def test_suppressed_member_label_keeps_owner_even_without_scene_primitive():
    item = ReviewItem("obj/suppressed", "A" * 600, "span",
                      {"start": date(2026, 1, 1), "end": date(2026, 2, 1)}, None, None,
                      ("planned", "missing-actual"), observation_state=ObservationState.DUE_UNOBSERVED)
    surface = _surface(item, surface_content(label_placement="plot", label_content=("title",),
                                             label_side="auto", label_overflow="suppress"))
    diagnostic = next(value for value in surface.diagnostics
                      if value.startswith("W_LAYOUT_LABEL_SUPPRESSED:"))
    assert diagnostic == "W_LAYOUT_LABEL_SUPPRESSED:member-label:obj/suppressed"
    assert DiagnosticProvenance(diagnostic, (DiagnosticSubject.project_object(
        "obj/suppressed", "A" * 600),)) in surface.diagnostic_provenance
    assert not any(primitive.scene_id == "member-label:obj/suppressed" for primitive in surface.primitives)


def test_explicit_row_cell_uses_selected_table_subject_not_row_id_or_last_variant():
    primary = ReviewItem("object-77", "Current title", "span",
                         {"start": date(2026, 1, 1), "end": date(2026, 2, 1)}, None, None,
                         ("planned",), item_id="current", source_kind="primary")
    snapshot = replace(primary, title="Selected snapshot title", item_id="historical", source_kind="snapshot")
    row = ReviewRowProjection("row-not-an-object", "Row title", "", "historical", (snapshot, primary))
    content = surface_content((("name", "Name"),), ((row.row_id, "name", "Selected snapshot title"),),
                              row_decoration="alternate")
    surface = _surface(primary, content, (row,))
    owners = {item.primitive_id: item.subjects for item in surface.primitive_provenance}
    assert owners[f"cell:{row.row_id}:name"] == (
        DiagnosticSubject.project_object("object-77", "Selected snapshot title"),)
    assert owners[f"row-band:{row.row_id}"] == (
        DiagnosticSubject.project_object("object-77", "Selected snapshot title"),
        DiagnosticSubject.project_object("object-77", "Current title"))


def test_row_density_fit_warning_carries_project_subject_without_changing_geometry(monkeypatch):
    from types import SimpleNamespace

    from chrona.presentation.model.projection import ReviewRowProjection

    class Tokens:
        def optional_color(self, *_args): return None
        def optional_number(self, *_args): return None
        def optional_pattern(self, *_args): return None
        def has_role(self, *_args): return False

    viewport = Rect(Decimal(0), Decimal(0), Decimal(50), Decimal(50))
    timeline = SlotPlacement("timeline", "timeline", viewport)
    row = RowPlacement("row-obj-1", "obj-1", "", Rect(Decimal(0), Decimal(60), Decimal(50), Decimal(20)))
    item = ReviewItem("obj-1", "Object title", "span",
                      {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}, None, None, ())
    review_row = ReviewRowProjection("row-obj-1", "Object title", "", "obj-1", (item,))
    manifest = SimpleNamespace(decisions=(), fit_warnings=(), viewport=viewport)
    request = SimpleNamespace(theme_tokens=Tokens(), font_metrics=None, layout_manifest=manifest)

    monkeypatch.setattr(surface_completion, "place_axis_band_visuals", lambda *_args, **_kwargs: SimpleNamespace(icons=()))
    monkeypatch.setattr(surface_completion, "validate_background_shapes", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(surface_completion, "build_lane_emissions", lambda *_args, **_kwargs: ())
    monkeypatch.setattr(surface_completion, "complete_hosted_text_identity", lambda texts, *_args: texts)
    monkeypatch.setattr(surface_completion, "stamp_surface_fits", lambda texts, shapes, *_args: (texts, shapes))
    monkeypatch.setattr(surface_completion, "complete_catalog_patterns", lambda *_args: ())
    monkeypatch.setattr(surface_completion, "complete_canvas_texture", lambda *_args: None)
    monkeypatch.setattr(surface_completion, "complete_canvas_overlays",
                        lambda *_args: SimpleNamespace(pattern=None, radial=None))
    monkeypatch.setattr(surface_completion, "complete_aligned_strokes", lambda *_args: ())
    monkeypatch.setattr(surface_completion, "complete_region_frames",
                        lambda *_args: SimpleNamespace(shapes=(), slots=(), extents=(), diagnostics=(), patterns=()))
    monkeypatch.setattr(surface_completion, "complete_frame_glyphs",
                        lambda *_args: SimpleNamespace(shapes=(), slots=(), extents=(), diagnostics=(), patterns=()))
    context = surface_completion.SurfaceCompletionContext(
        request=request, projection=SimpleNamespace(lane_membership=None), layout_manifest=manifest,
        review_rows=(review_row,), rows=(row,), tracks=(), groups=(), scale=None,
        slots=(timeline,), by_source={"timeline": timeline}, timeline=timeline, axis=timeline, table=timeline,
        table_bounds=(0, 0, 50, 50), timeline_bounds=(0, 0, 50, 50), column_placements=(),
        text=[], marks=[], shapes=[], relations=[], icons=[], placement_decisions=[], axis_tier_outcomes=(),
        diagnostics=[], mark_absences=(), axis_band_targets={}, detail_panel_warnings=(), side_content_warnings=[],
        text_visual_warnings=[], visible_label_overflows=[], visible_route_fallbacks=[],
        visible_group_header_overflows=[], lane_label_suppressions=[],
    )

    placement = surface_completion.complete_surface_layout(context).placement
    warning = next(item for item in placement.fit_warnings if item.code == "W_LAYOUT_ROW_DENSITY")
    assert warning.subjects == (DiagnosticSubject.project_object("obj-1", "Object title"),)
    assert warning.source_ref == "obj-1"
    assert row.bounds == Rect(Decimal(0), Decimal(60), Decimal(50), Decimal(20))


def test_detail_milestone_overflow_carries_only_its_explicit_project_reference():
    item = ReviewItem("gate", "Gate " * 80, "point", {"at": date(2026, 1, 2)}, None, None, ())
    projection = ReviewProjection((item,), (date(2026, 1, 1), date(2026, 2, 1)), (), ())
    content = surface_content(milestones=((item.object_id, item.title, date(2026, 1, 2)),))
    manifest = _manifest("title", "table", "timeline", "timeline-axis", "milestones")
    manifest = replace(manifest, decisions=tuple(
        replace(decision, bounds=Rect(Decimal(0), Decimal(900), Decimal(1), Decimal(20)))
        if decision.source == "milestones" else decision for decision in manifest.decisions))
    measurement = MeasuredSources(
        {"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
        {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
         "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8),
         "timeline.mark.blockSize": Decimal(8)},
    )
    placement = compose_surface_layout(SurfaceLayoutRequest(
        projection=projection, presentation_contract=normalize_presentation_input(content),
        surface_content=content, layout_manifest=manifest, measured_sources=measurement,
        theme_tokens=ThemeTokenView(_theme()), font_metrics=_Font(), capabilities={"svg": True},
    )).placement

    warning = next(value for value in placement.fit_warnings
                   if value.placement_id == "milestone:gate" and value.code == "W_LAYOUT_VISIBLE_OVERFLOW")
    assert warning.subjects == (DiagnosticSubject.project_object("gate", item.title),)


def test_text_visual_overflow_uses_typed_table_cell_object_link_only():
    class Metric:
        def width(self, value, size, **_kwargs): return len(value) * size
        def cap_height_at(self, size): return size * .7

    item = ReviewItem("obj-visual", "Cell owner", "span",
                      {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}, None, None, ())
    icon = SimpleNamespace(icon_id="icon", kind="icon", content_identity="sha256:icon",
                           viewport=(10, 10), payload=(), alternative="icon")
    request = SimpleNamespace(
        visual_requests=(VisualRequest("cell", (("object", item.object_id), ("column", "name")),
                                       ref="icon"),), icon_assets={"icon": icon},
        font_metrics=Metric(), theme_tokens=SimpleNamespace(icon_ratios=lambda _role: (Decimal(1), Decimal("0.2"))),
        surface_content=SimpleNamespace(table_cells=(SimpleNamespace(object_id=item.object_id),)),
        projection=SimpleNamespace(items=(item,)),
    )
    text = TextPlacement("cell:obj-visual:name", item.object_id, "Long",
                         Rect(Decimal(0), Decimal(0), Decimal(5), Decimal(12)), "text",
                         baseline=(0, 10), lines=("Long",), font_family="Test", font_weight=400,
                         font_size=10, line_height=1.2, available_inline_start=0, available_inline_size=5)

    batch = place_text_visuals((text,), request)
    assert batch.warnings[0].subjects == (DiagnosticSubject.project_object(item.object_id, item.title),)

    request.surface_content = SimpleNamespace(table_cells=())
    assert place_text_visuals((text,), request).warnings[0].subjects == ()


def test_annotation_diagnostics_use_only_explicit_resolved_project_anchor(tmp_path, monkeypatch):
    item_title = "Launch gate"
    source = sr.project({
        "gate": sr.point("gate", date(2026, 1, 5), owner="team", title=item_title),
        "next": sr.point("next", date(2026, 2, 5), owner="team", title="Next gate"),
    })
    parts = sr.bundle()
    parts["view"] = sr.lane_view(parts["view"])
    sr.add_notes(source, parts["view"], ["gate"], [sr.candidate("plot-near", connector="leader")], words=0)
    body = parts["view"]["body"]
    body["visibility"].setdefault("fallback", {})["annotations"] = ["end", "suppress"]
    body["annotations"][0].pop("candidates")
    body["annotations"][0]["placement"] = {"side": "end", "alignment": "center"}
    monkeypatch.setattr(surface_annotations, "place_label", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(surface_annotations, "project_annotation_box", lambda *_args, **_kwargs: None)

    rendered = sr.render(tmp_path, source, presentation=parts, viewport=(1200, 800))
    expected = DiagnosticSubject.project_object("gate", item_title)
    records = {record.diagnostic: record.subjects for record in rendered.surface.diagnostic_provenance}
    assert records["W_LAYOUT_ANNOTATION_SUPPRESSED:annotation:note-0"] == (expected,)
    warning = next(value for value in rendered.surface.fit_warnings
                   if value.code == "W_LAYOUT_LABEL_OVERFLOW" and value.source_ref == "note-0")
    assert warning.subjects == (expected,)
    primitive_owners = {record.primitive_id: record.subjects
                        for record in rendered.surface.primitive_provenance}
    summary_text = next(primitive for primitive in rendered.surface.primitives
                        if primitive.scene_id == "annotation-summary:note-0")
    assert primitive_owners[summary_text.scene_id] == (expected,)
