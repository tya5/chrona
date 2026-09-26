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
    "ScenePaint": (_owner("inspection", "scene/serialization.py", "fill stroke stroke_width dash opacity gradient shadow stroke_finish"),),
    "LinearGradient": (_owner("inspection", "scene/serialization.py", "start end stops fidelity"),),
    "DropShadow": (_owner("inspection", "scene/serialization.py", "color offset_x offset_y blur opacity fidelity"),),
    "StrokeFinish": (_owner("inspection", "scene/serialization.py", "line_cap line_join fidelity"),),
    "TextLayout": (_owner("inspection", "scene/serialization.py", "bounds baseline lines family weight font_size line_height asset_identity letter_spacing text_transform numeric_spacing orientation rotation_degrees"),),
    "SceneIconPath": (_owner("inspection", "scene/serialization.py", "commands fill stroke stroke_width line_cap line_join opacity"),),
    "PatternStroke": (_owner("inspection", "scene/serialization.py", "start end width"),),
    "PatternGeometry": (_owner("inspection", "scene/serialization.py", "tile_inline_size tile_block_size angle_degrees strokes"),),
    "SymbolGeometry": (_owner("inspection", "scene/serialization.py", "outline"),),
    "ScenePrimitive": (
        _owner("inspection", "scene/serialization.py", "scene_id kind source_ref source_kind purpose visual_role bounds slot_id text baseline text_layout marker_start marker_end pattern symbol paint corner_radius path_commands points href link_title icon_kind icon_asset_identity icon_viewport icon_paths icon_alternative icon_decorative table_row_id table_column_id paint_order host_placement_id clip_source_id end_treatment contrast_treatment"),
        _owner("derived", "scene/v05_builder.py", "icon_vector icon_stroke_scale"),
        _owner("adapter", "renderers/v05_svg.py", "icon_raster"),
        _owner("derived", "scene/visual_capabilities.py", "visual_capability_source_ref"),
    ),
    "SceneSlot": (_owner("inspection", "scene/serialization.py", "slot_id source scale_id bounds priority overflow"),),
    "SceneRow": (_owner("inspection", "scene/serialization.py", "object_id group_id bounds row_id"),),
    "SceneColumn": (_owner("inspection", "scene/serialization.py", "column_id label bounds"),),
    "SceneGroup": (_owner("inspection", "scene/serialization.py", "group_id header_bounds content_bounds"),),
    "SurfaceScaleManifest": (_owner("inspection", "scene/serialization.py", "surface_id scale_id domain_start domain_end range_start range_end origin unit_ratio"),),
    "ContentFamilyCounts": (_owner("inspection", "scene/serialization.py", "relations annotations notes legend_entries summary_panels group_details milestones observation_rows"),),
    "SceneManifest": (_owner("inspection", "scene/serialization.py", "version settings_version viewport selected_object_ids font_asset_identities content_family_counts surface_scales visual_role_counts"),),
    "SceneSurface": (
        _owner("inspection", "scene/serialization.py", "surface_id slots rows groups scale_manifest primitives canvas_paint columns canvas_bounds fit_warnings decoration_dispositions"),
        _owner("derived", "scene/v05_builder.py", "diagnostics"),
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
