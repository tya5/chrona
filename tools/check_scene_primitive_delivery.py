"""Reject public Scene-model fields without an explicit live delivery owner."""
from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "src/chrona/presentation/scene/model.py"
SOURCE = ROOT / "src/chrona/presentation"


@dataclass(frozen=True)
class Owner:
    delivery: str
    consumer: str
    fields: tuple[str, ...]


def _owner(delivery: str, consumer: str, fields: str) -> Owner:
    return Owner(delivery, consumer, tuple(fields.split()))


# Fields are deliberately literal.  New public Scene data has no delivery
# authority until it is added here with a real consumer.
OWNERS = {
    "ScenePaint": (_owner("inspection", "scene/serialization.py", "fill stroke stroke_width dash opacity gradient radial_gradient shadow stroke_finish image glow wobble"),),
    "LinearGradient": (_owner("inspection", "scene/serialization.py", "start end stops fidelity stop_opacities"),
                      _owner("adapter", "renderers/v05_svg.py", "stop_opacities")),
    "RadialGradient": (_owner("inspection", "scene/serialization.py", "center radii stops fidelity"),
                       _owner("adapter", "renderers/v05_svg.py", "center radii stops")),
    "RadialGradientStop": (_owner("inspection", "scene/serialization.py", "offset color opacity"),
                           _owner("adapter", "renderers/v05_svg.py", "offset color opacity")),
    "DropShadow": (_owner("inspection", "scene/serialization.py", "color offset_x offset_y blur opacity fidelity"),),
    "Glow": (_owner("inspection", "scene/serialization.py", "color blur opacity fidelity region"),
             _owner("adapter", "renderers/v05_svg.py", "color blur opacity region")),
    "StrokeWobble": (_owner("inspection", "scene/serialization.py", "amplitude wavelength seed fidelity closed outline"),
                     _owner("adapter", "renderers/v05_svg.py", "closed outline")),
    "StrokeFinish": (_owner("inspection", "scene/serialization.py", "line_cap line_join fidelity"),),
    "ImageFill": (_owner("inspection", "scene/serialization.py", "asset_identity viewport tiles"),
                 _owner("adapter", "renderers/v05_svg.py", "payload")),
    "ImageTile": (_owner("inspection", "scene/serialization.py", "source destination"),),
    "TextLayout": (_owner("inspection", "scene/serialization.py", "bounds baseline lines family weight font_size line_height asset_identity letter_spacing text_transform numeric_spacing orientation rotation_degrees horizontal_scale fit runs"),
                   _owner("adapter", "renderers/v05_svg.py", "horizontal_scale fit runs")),
    "TextRun": (_owner("inspection", "scene/serialization.py", "text font_size inline_size"),
                _owner("adapter", "renderers/v05_svg.py", "text font_size")),
    "SceneIconPath": (_owner("inspection", "scene/serialization.py", "commands fill stroke stroke_width line_cap line_join opacity"),),
    "PatternStroke": (_owner("inspection", "scene/serialization.py", "start end width"),),
    "PatternGeometry": (_owner("inspection", "scene/serialization.py", "tile_inline_size tile_block_size angle_degrees strokes density_basis_points primitives origin region_bounds clip_bounds corner_radius"),),
    "SymbolGeometry": (_owner("inspection", "scene/serialization.py", "outline"),),
    "ScenePrimitive": (
        _owner("inspection", "scene/serialization.py", "scene_id kind source_ref source_kind purpose visual_role bounds slot_id text baseline text_layout marker_start marker_end pattern symbol paint corner_radius path_commands points href link_title icon_kind icon_asset_identity icon_viewport icon_paths icon_alternative icon_decorative table_row_id table_column_id paint_order host_placement_id clip_source_id end_treatment contrast_treatment lane_row_id lane_member_id stroke_clip"),
        _owner("derived", "scene/v05_builder.py", "icon_path_geometry glyph_paint_mode glyph_paint_color glyph_stroke_width glyph_line_cap glyph_line_join"),
        _owner("adapter", "renderers/v05_svg.py", "icon_raster"),
        _owner("inspection", "scene/serialization.py", "viewer_fit"),
        _owner("inspection", "scene/serialization.py", "from_instance_id to_instance_id fan_in"),
        _owner("adapter", "renderers/v05_svg.py", "viewer_fit"),
        _owner("adapter", "renderers/v05_svg.py", "stroke_clip"),
        _owner("derived", "scene/visual_capabilities.py", "visual_capability_source_ref"),
        _owner("derived", "scene/v05_builder.py", "image_fill_pending"),
    ),
    "SceneSlot": (_owner("inspection", "scene/serialization.py", "slot_id source scale_id bounds priority overflow"),),
    "SceneRow": (_owner("inspection", "scene/serialization.py", "object_id group_id bounds row_id lane_mark_band_block"),),
    "SceneColumn": (_owner("inspection", "scene/serialization.py", "column_id label bounds"),),
    "SceneGroup": (_owner("inspection", "scene/serialization.py", "group_id header_bounds content_bounds"),),
    "SceneLaneMember": (_owner("inspection", "scene/serialization.py", "row_id member_id emitted_primitive_ids primary_mark_ids"),),
    "SceneLaneRectObstacle": (_owner("inspection", "scene/serialization.py", "left top right bottom"),),
    "SceneLaneSegmentObstacle": (_owner("inspection", "scene/serialization.py", "start end stroke_width"),),
    "SceneLaneObstacle": (_owner("inspection", "scene/serialization.py", "facet_id primitive_id row_id member_id obstacle_class geometry"),),
    "SurfaceScaleManifest": (_owner("inspection", "scene/serialization.py", "surface_id scale_id domain_start domain_end range_start range_end origin unit_ratio"),),
    "ContentFamilyCounts": (_owner("inspection", "scene/serialization.py", "relations annotations notes legend_entries summary_panels group_details milestones observation_rows"),),
    "SceneManifest": (_owner("inspection", "scene/serialization.py", "version settings_version viewport selected_object_ids font_asset_identities content_family_counts surface_scales visual_role_counts"),),
    "SceneSurface": (
        _owner("inspection", "scene/serialization.py", "surface_id slots rows groups scale_manifest primitives canvas_paint columns canvas_bounds fit_warnings decoration_dispositions lane_mode lane_members lane_obstacles lane_clearance"),
        _owner("derived", "scene/v05_builder.py", "diagnostics info_diagnostics"),
        # Runtime warning provenance is consumed by the use case, not serialized.
        _owner("derived", "../usecases/render_review.py", "diagnostic_provenance primitive_provenance canvas_warning"),
    ),
    "SceneProvenance": (_owner("inspection", "scene/serialization.py", "mode chrona_version resources"),),
    "DecorationDisposition": (_owner("inspection", "scene/serialization.py", "visual_role disposition"),),
    "InspectionScene": (_owner("inspection", "scene/serialization.py", "provenance viewport required_capabilities surfaces manifest diagnostics font_warnings"),),
}


def model_fields() -> dict[str, set[str]]:
    tree = ast.parse(MODEL.read_text(encoding="utf-8"))
    return {node.name: {item.target.id for item in node.body if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)}
            for node in tree.body if isinstance(node, ast.ClassDef) and any((isinstance(item, ast.Name) and item.id == "dataclass") or (isinstance(item, ast.Call) and isinstance(item.func, ast.Name) and item.func.id == "dataclass") for item in node.decorator_list)}


def _attributes(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load)}


def delivery_errors() -> tuple[str, ...]:
    fields, errors = model_fields(), []
    if set(fields) != set(OWNERS): errors.append("Scene delivery manifest classes differ from public Scene dataclasses")
    for name, declared in fields.items():
        owners = OWNERS.get(name, ())
        owned = {field for owner in owners for field in owner.fields}
        errors.extend(f"unowned {name} field: {field}" for field in sorted(declared - owned))
        errors.extend(f"stale Scene delivery owner: {name}.{field}" for field in sorted(owned - declared))
        for owner in owners:
            path = SOURCE / owner.consumer
            attrs = _attributes(path) if path.is_file() else set()
            if owner.delivery not in {"adapter", "inspection", "derived"}: errors.append(f"invalid delivery class: {name}.{owner.delivery}")
            errors.extend(f"undelivered {name} field: {field} ({owner.consumer})" for field in owner.fields if field not in attrs)
    return tuple(errors)


def main() -> int:
    errors = delivery_errors()
    if errors:
        print(*errors, sep="\n")
        return 1
    count = sum(len(value) for value in model_fields().values())
    print(f"{len(model_fields())} Scene dataclasses, {count} fields have explicit delivery owners")
    return 0


if __name__ == "__main__": sys.exit(main())
