"""Explicit, schema-validated serialization of completed inspection Scenes."""
from __future__ import annotations

import json
import math
from typing import Any, Mapping


from chrona.presentation.scene.model import (
    PRIMARY_LANE_MARK_PURPOSES, DecorationDisposition, InspectionScene, LinearGradient, RadialGradient,
    PatternGeometry, SceneIconPath, SceneLaneObstacle, SceneLaneRectObstacle,
    SceneLaneSegmentObstacle, ScenePaint, ScenePrimitive, SceneSurface, StrokeFinish,
    TextLayout, requires_lane_member_provenance,
)
from chrona.resources import schema_validator


class SceneSerializationError(ValueError):
    """The completed Scene cannot truthfully become its public document."""


def _scene_error(detail: str) -> SceneSerializationError:
    return SceneSerializationError(f"E_SCENE_SERIALIZATION: {detail}")


def _brief(value: object) -> str:
    if isinstance(value, str):
        clipped = value[:64]
        return repr(clipped + ("…" if len(value) > len(clipped) else ""))
    if value is None or isinstance(value, (bool, int, float)):
        return repr(value)
    return f"<{type(value).__name__}>"


def serialize_scene(scene: InspectionScene) -> bytes:
    """Return canonical UTF-8 scene-v0.6 JSON after typed and schema validation."""
    document = scene_document(scene)
    validate_scene_document(document)
    try:
        return (json.dumps(document, ensure_ascii=False, separators=(",", ":"),
                           allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError) as error:
        raise _scene_error(f"canonical JSON encoding rejected the completed Scene document ({type(error).__name__})") from error


def scene_document(scene: InspectionScene) -> dict[str, Any]:
    """Map each public Scene field explicitly; no dataclass reflection is used."""
    has_catalog_pattern = any(primitive.pattern is not None and primitive.pattern.primitives
                              for surface in scene.surfaces for primitive in surface.primitives)
    has_v07_paint = any(primitive.paint is not None and (primitive.paint.glow is not None
                                                    or primitive.paint.wobble is not None
                                                    or primitive.paint.radial_gradient is not None
                                                    or (primitive.paint.gradient is not None
                                                        and primitive.paint.gradient.stop_opacities is not None))
                   for surface in scene.surfaces for primitive in surface.primitives)
    has_tilt = any(primitive.text_layout is not None and primitive.text_layout.orientation == "tilt"
                   for surface in scene.surfaces for primitive in surface.primitives)
    has_scale = any(primitive.text_layout is not None and primitive.text_layout.horizontal_scale != 1
                    for surface in scene.surfaces for primitive in surface.primitives)
    has_runs = any(primitive.text_layout is not None and primitive.text_layout.runs
                   for surface in scene.surfaces for primitive in surface.primitives)
    has_fit = any(primitive.viewer_fit != "raw" or (primitive.text_layout is not None and primitive.text_layout.fit is not None)
                  for surface in scene.surfaces for primitive in surface.primitives)
    has_stroke_clip = any(primitive.stroke_clip is not None for surface in scene.surfaces for primitive in surface.primitives)
    has_marker_axis = any(marker is not None and (marker.angle_degrees is not None or marker.physical_units)
                         for surface in scene.surfaces for primitive in surface.primitives
                         for marker in (primitive.marker_start, primitive.marker_end))
    has_relation_endpoint_identity = any(
        primitive.from_instance_id is not None or primitive.to_instance_id is not None
        for surface in scene.surfaces for primitive in surface.primitives)
    return {
        "version": ("chrona/scene/v0.7" if has_catalog_pattern or has_v07_paint or has_tilt or has_scale or has_runs or has_fit or has_marker_axis or has_stroke_clip
                    or has_relation_endpoint_identity
                    else "chrona/scene/v0.6"),
        "kind": "scene",
        "provenance": {
            "mode": scene.provenance.mode,
            "chronaVersion": scene.provenance.chrona_version,
            "resources": [
                {"kind": kind, "id": identifier, "revision": revision,
                 "contentIdentity": identity}
                for kind, identifier, revision, identity in scene.provenance.resources
            ],
        },
        "viewport": _viewport(scene.viewport),
        "requiredCapabilities": list(scene.required_capabilities),
        "surfaces": [_surface(surface) for surface in scene.surfaces],
        "manifest": {
            "version": scene.manifest.version,
            "settingsVersion": scene.manifest.settings_version,
            "viewport": _viewport(scene.manifest.viewport),
            "selectedObjectIds": list(scene.manifest.selected_object_ids),
            "fontAssetIdentities": list(scene.manifest.font_asset_identities),
            "contentFamilyCounts": {
                "relations": scene.manifest.content_family_counts.relations,
                "annotations": scene.manifest.content_family_counts.annotations,
                "notes": scene.manifest.content_family_counts.notes,
                "legendEntries": scene.manifest.content_family_counts.legend_entries,
                "summaryPanels": scene.manifest.content_family_counts.summary_panels,
                "groupDetails": scene.manifest.content_family_counts.group_details,
                "milestones": scene.manifest.content_family_counts.milestones,
                "observationRows": scene.manifest.content_family_counts.observation_rows,
            },
            "surfaceScales": [_scale(item) for item in scene.manifest.surface_scales],
            "visualRoleCounts": dict(scene.manifest.visual_role_counts),
        },
        "diagnostics": list(scene.diagnostics),
        **({"fontWarnings": [{"code": "W_FONT_TABULAR_UNAVAILABLE", "role": item.role,
                              "family": item.family, "weight": item.weight,
                              "requestedSpacing": item.requested_spacing,
                              "effectiveSpacing": item.effective_spacing}
                             for item in scene.font_warnings]} if scene.font_warnings else {}),
    }


def validate_scene_document(document: Mapping[str, Any]) -> None:
    """Validate schema shape plus cross-reference invariants JSON Schema cannot state."""
    schema_name = None
    try:
        version = document.get("version")
        schema_name = {"chrona/scene/v0.6": "scene-v0.6.schema.yaml",
                       "chrona/scene/v0.7": "scene-v0.7.schema.yaml"}.get(version)
        if schema_name is None:
            raise _scene_error(f"document.version={_brief(version)}; expected chrona/scene/v0.6 or chrona/scene/v0.7")
        errors = tuple(schema_validator(schema_name).iter_errors(document))
    except Exception as error:  # schema resource failures have no public partial document
        nested = str(error).split(": ", 1)[-1] if isinstance(error, SceneSerializationError) else type(error).__name__
        raise _scene_error(f"{schema_name or 'Scene schema'} validation could not complete: {_brief(nested)}") from error
    if errors:
        first = errors[0]
        path = "/" + "/".join(str(part)[:64] for part in first.absolute_path)
        raise _scene_error(f"{schema_name} rejected the document: {len(errors)} schema error(s), first at {path or '/'}")
    if not _finite(document):
        raise _scene_error("document contains a non-finite numeric Scene fact; check completed bounds, paint, or measurement fields")
    if not _references_are_closed(document):
        raise _scene_error("surface cross-references must resolve among declared slots, rows, columns, primitives, and lane facts")


def _references_are_closed(document: Mapping[str, Any]) -> bool:
    surfaces = document.get("surfaces")
    if not isinstance(surfaces, list):
        return False
    for surface in surfaces:
        if not isinstance(surface, Mapping):
            return False
        slots = {item.get("id") for item in surface.get("slots", ()) if isinstance(item, Mapping)}
        row_items = surface.get("rows", ())
        rows = {item.get("id") for item in row_items if isinstance(item, Mapping)}
        lane_rows = {item.get("id") for item in row_items
                     if isinstance(item, Mapping) and "laneMarkBandBlock" in item}
        for row_item in row_items:
            if not isinstance(row_item, Mapping) or "laneMarkBandBlock" not in row_item:
                continue
            bounds = row_item.get("bounds")
            anchor = row_item.get("laneMarkBandBlock")
            if (not isinstance(bounds, Mapping) or not isinstance(anchor, (int, float))
                    or anchor < bounds.get("block", math.inf)
                    or anchor > bounds.get("block", -math.inf) + bounds.get("blockSize", -math.inf)):
                return False
        columns = {item.get("id") for item in surface.get("columns", ()) if isinstance(item, Mapping)}
        if (None in slots or None in rows or None in columns or len(slots) != len(surface.get("slots", ()))
                or len(rows) != len(surface.get("rows", ())) or len(columns) != len(surface.get("columns", ()) )):
            return False
        primitives = surface.get("primitives", ())
        by_id = {item.get("id"): (index, item) for index, item in enumerate(primitives)
                 if isinstance(item, Mapping)}
        if len(by_id) != len(primitives):
            return False
        fan_in_counts: dict[str, int] = {}
        lane_mode = surface.get("laneMode")
        lane_members = surface.get("laneMembers", ())
        if lane_mode is None:
            if lane_members or surface.get("laneObstacles") or "laneClearance" in surface:
                return False
        else:
            lane_obstacles = surface.get("laneObstacles", ())
            lane_clearance = surface.get("laneClearance")
            if (lane_mode != "lanes" or not lane_members or not lane_obstacles
                    or not _valid_number(lane_clearance) or lane_clearance < 0):
                return False
            if (len(lane_rows) != len(row_items)
                    or any(not isinstance(item, Mapping) or "laneMarkBandBlock" not in item
                           for item in row_items)):
                return False
            inventory: dict[str, tuple[str, str]] = {}
            member_keys: set[tuple[str, str]] = set()
            primary_ids: set[str] = set()
            member_row_ids: set[str] = set()
            for member in lane_members:
                if not isinstance(member, Mapping):
                    return False
                row_id, member_id = member.get("rowId"), member.get("memberId")
                emitted = member.get("emittedPrimitiveIds")
                primary = member.get("primaryMarkIds")
                if (row_id not in lane_rows or not isinstance(member_id, str) or not member_id
                        or not isinstance(emitted, list) or not emitted
                        or not isinstance(primary, list) or not primary
                        or not set(primary) <= set(emitted)):
                    return False
                key = (row_id, member_id)
                if key in member_keys or len(set(emitted)) != len(emitted) or len(set(primary)) != len(primary):
                    return False
                member_keys.add(key)
                member_row_ids.add(row_id)
                for primitive_id in emitted:
                    if primitive_id in inventory:
                        return False
                    inventory[primitive_id] = key
                primary_ids.update(primary)
            tagged_inventory = {primitive.get("id"): (primitive.get("laneRowId"), primitive.get("laneMemberId"))
                                for primitive in primitives if primitive.get("laneRowId") is not None}
            if inventory != tagged_inventory or any(item not in by_id for item in inventory):
                return False
            if member_row_ids != lane_rows:
                return False
            if any(by_id[item][1].get("purpose") not in PRIMARY_LANE_MARK_PURPOSES
                   for item in primary_ids):
                return False
            if any(requires_lane_member_provenance(item.get("kind"), item.get("purpose"))
                   and item.get("laneRowId") is None for item in primitives):
                return False
            expected_obstacles = set(inventory)
            obstacle_primitives: set[str] = set()
            facet_ids: set[str] = set()
            for obstacle in lane_obstacles:
                if not isinstance(obstacle, Mapping):
                    return False
                primitive_id = obstacle.get("primitiveId")
                key = (obstacle.get("rowId"), obstacle.get("memberId"))
                facet_id = obstacle.get("facetId")
                if (primitive_id not in expected_obstacles or inventory[primitive_id] != key
                        or not isinstance(facet_id, str) or not facet_id or facet_id in facet_ids):
                    return False
                facet_ids.add(facet_id)
                obstacle_primitives.add(primitive_id)
                geometry = obstacle.get("geometry")
                if not isinstance(geometry, Mapping):
                    return False
                if geometry.get("kind") == "rect":
                    left, top = geometry.get("left"), geometry.get("top")
                    right, bottom = geometry.get("right"), geometry.get("bottom")
                    if (not all(_valid_number(value) for value in (left, top, right, bottom))
                            or right <= left or bottom <= top):
                        return False
                elif geometry.get("kind") == "stroked-segment":
                    start, end = geometry.get("start"), geometry.get("end")
                    stroke_width = geometry.get("strokeWidth")
                    if (not isinstance(start, list) or len(start) != 2
                            or not isinstance(end, list) or len(end) != 2
                            or not all(_valid_number(value) for value in (*start, *end, stroke_width))
                            or stroke_width < 0 or start == end):
                        return False
                else:
                    return False
            if obstacle_primitives != expected_obstacles:
                return False
        for index, primitive in enumerate(primitives):
            if not isinstance(primitive, Mapping):
                return False
            paint = primitive.get("paint")
            radial = paint.get("radialGradient") if isinstance(paint, Mapping) else None
            if radial is not None and not _radial_paint_is_closed(primitive, paint, radial):
                return False
            row, column, purpose = primitive.get("tableRowId"), primitive.get("tableColumnId"), primitive.get("purpose")
            lane_row, lane_member = primitive.get("laneRowId"), primitive.get("laneMemberId")
            if ((lane_row is None) != (lane_member is None)
                    or (lane_row is not None and (lane_row not in lane_rows or not lane_row or not lane_member))):
                return False
            if primitive.get("slotId") not in slots:
                return False
            fan_in = primitive.get("fanIn")
            if fan_in is not None:
                if (primitive.get("kind") != "Path" or primitive.get("sourceKind") != "relation"
                        or not isinstance(primitive.get("fromInstanceId"), str)
                        or not isinstance(primitive.get("toInstanceId"), str)):
                    return False
                target_port, owner_id = fan_in.get("targetPortId"), fan_in.get("terminalOwnerId")
                if (not isinstance(target_port, str) or not target_port
                        or not isinstance(owner_id, str) or not owner_id):
                    return False
                owner_entry = by_id.get(owner_id)
                if owner_entry is None:
                    return False
                owner = owner_entry[1]
                owner_fan = owner.get("fanIn")
                if (owner.get("kind") != "Path" or owner.get("sourceKind") != "relation"
                        or owner.get("toInstanceId") != primitive.get("toInstanceId")
                        or not isinstance(owner_fan, Mapping)
                        or owner_fan.get("targetPortId") != target_port
                        or owner_fan.get("terminalOwnerId") != owner_id):
                    return False
                if primitive.get("id") == owner_id:
                    if owner_fan != fan_in:
                        return False
                elif primitive.get("markerEnd") is not None:
                    return False
                fan_in_counts[owner_id] = fan_in_counts.get(owner_id, 0) + 1
            if purpose == "table-cell":
                if row not in rows or column not in columns:
                    return False
            elif purpose == "table-column-label":
                if row is not None or column not in columns:
                    return False
            elif row is not None or column is not None:
                return False
            host_placement_id = primitive.get("hostPlacementId")
            if host_placement_id is not None:
                host = by_id.get(host_placement_id)
                if (primitive.get("kind") != "Text" or host is None
                        or host[1].get("slotId") != primitive.get("slotId")
                        or host[1].get("paintOrder", 0) >= primitive.get("paintOrder", 0)):
                    return False
            clip_source_id = primitive.get("clipSourceId")
            if clip_source_id is not None:
                source = by_id.get(clip_source_id)
                if (source is None or source[1].get("paintOrder", 0) > primitive.get("paintOrder", 0)
                        or (source[1].get("paintOrder", 0) == primitive.get("paintOrder", 0) and source[0] >= index)
                        or source[1].get("kind") not in {"Rect", "Symbol"}
                        or (source[1].get("kind") == "Symbol" and not source[1].get("symbol"))
                        or source[1].get("slotId") != primitive.get("slotId")):
                    return False
        if any(count < 2 for count in fan_in_counts.values()):
            return False
    return True


def _radial_paint_is_closed(primitive: Mapping[str, Any], paint: Mapping[str, Any],
                            radial: Mapping[str, Any]) -> bool:
    """Check the finite fixed-ink alpha program even for raw JSON Scene documents."""
    if (primitive.get("kind") != "Rect" or "pattern" in primitive
            or any(key in paint for key in ("stroke", "strokeWidth", "gradient", "shadow", "glow",
                                             "wobble", "strokeFinish", "image"))):
        return False
    stops = radial.get("stops")
    fill = paint.get("fill")
    if not isinstance(stops, list) or len(stops) not in {2, 3} or not isinstance(fill, str):
        return False
    if any(not isinstance(stop, Mapping) or stop.get("color") != fill for stop in stops):
        return False
    offsets = [stop.get("offset") for stop in stops]
    opacities = [stop.get("opacity") for stop in stops]
    return (offsets[0] == 0 and offsets[-1] == 1
            and all(_finite_scalar(offset) for offset in offsets)
            and all(left < right for left, right in zip(offsets, offsets[1:]))
            and opacities == ([0, 1] if len(stops) == 2 else [0, 0, 1]))


def _finite_scalar(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, ValueError):
        return False


def _finite(value: Any) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, Mapping):
        return all(_finite(item) for item in value.values())
    if isinstance(value, (tuple, list)):
        return all(_finite(item) for item in value)
    return True


def _surface(surface: SceneSurface) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": surface.surface_id,
        "slots": [
            _omit({"id": item.slot_id, "source": item.source, "scaleId": item.scale_id,
                   "bounds": _bounds(item.bounds), "priority": item.priority,
                   "overflow": item.overflow}) for item in surface.slots
        ],
        "rows": [_omit({"id": item.row_id, "objectId": item.object_id, "groupId": item.group_id,
                        "bounds": _bounds(item.bounds),
                        "laneMarkBandBlock": item.lane_mark_band_block}) for item in surface.rows],
        "columns": [{"id": item.column_id, "label": item.label, "bounds": _bounds(item.bounds)}
                    for item in surface.columns],
        "groups": [_omit({"id": item.group_id, "headerBounds": _bounds(item.header_bounds)
                            if item.header_bounds is not None else None,
                            "contentBounds": _bounds(item.content_bounds)}) for item in surface.groups],
        "primitives": [_primitive(item) for item in surface.primitives],
    }
    if surface.scale_manifest is not None:
        result["scale"] = _scale(surface.scale_manifest)
    if surface.canvas_paint is not None:
        result["canvasPaint"] = _paint(surface.canvas_paint)
    # A public Scene is a completed render contract: consumers must never
    # infer an extent from primitive geometry or their own target viewport.
    if surface.canvas_bounds is None:
        raise _scene_error(f"surface { _brief(surface.surface_id) } has no completed canvasBounds")
    result["canvasBounds"] = _bounds(surface.canvas_bounds)
    if surface.fit_warnings:
        result["fitWarnings"] = [_fit_warning(item) for item in surface.fit_warnings]
    if surface.decoration_dispositions:
        result["decorationDispositions"] = [
            {"visualRole": item.visual_role, "disposition": item.disposition}
            for item in surface.decoration_dispositions
        ]
    if surface.lane_mode is not None:
        result["laneMode"] = surface.lane_mode
        result["laneMembers"] = [
            {"rowId": item.row_id, "memberId": item.member_id,
             "emittedPrimitiveIds": list(item.emitted_primitive_ids),
             "primaryMarkIds": list(item.primary_mark_ids)}
            for item in surface.lane_members
        ]
        result["laneObstacles"] = [_lane_obstacle(item) for item in surface.lane_obstacles]
        result["laneClearance"] = surface.lane_clearance
    return result


def _lane_obstacle(item: SceneLaneObstacle) -> dict[str, Any]:
    if isinstance(item.geometry, SceneLaneRectObstacle):
        geometry: dict[str, Any] = {
            "kind": "rect", "left": item.geometry.left, "top": item.geometry.top,
            "right": item.geometry.right, "bottom": item.geometry.bottom,
        }
    elif isinstance(item.geometry, SceneLaneSegmentObstacle):
        geometry = {"kind": "stroked-segment", "start": list(item.geometry.start),
                    "end": list(item.geometry.end), "strokeWidth": item.geometry.stroke_width}
    else:
        raise _scene_error(f"lane obstacle primitive_id={_brief(item.primitive_id)} has unsupported geometry type {type(item.geometry).__name__}; expected rectangle or stroked segment")
    return {"facetId": item.facet_id, "primitiveId": item.primitive_id,
            "rowId": item.row_id, "memberId": item.member_id,
            "class": item.obstacle_class, "geometry": geometry}


def _valid_number(value: Any) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


def _fit_warning(value: Any) -> dict[str, Any]:
    return {
        "code": value.code,
        "placementId": value.placement_id,
        "sourceRef": value.source_ref,
        "failureKind": value.failure_kind,
        "behaviour": value.behaviour,
        "requiredInline": value.required_inline,
        "requiredBlock": value.required_block,
        "availableInline": value.available_inline,
        "availableBlock": value.available_block,
    }


def _primitive(item: ScenePrimitive) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": item.scene_id, "kind": item.kind, "sourceRef": item.source_ref,
        "sourceKind": item.source_kind, "purpose": item.purpose,
        "visualRole": item.visual_role, "bounds": _bounds(item.bounds), "slotId": item.slot_id,
    }
    optional = {
        "text": item.text, "baseline": _point(item.baseline) if item.baseline is not None else None,
        "textLayout": _text_layout(item.text_layout) if item.text_layout is not None else None,
        "paint": _paint(item.paint) if item.paint is not None else None,
        "cornerRadius": item.corner_radius,
        "pathCommands": [_path(item_path) for item_path in item.path_commands] if item.path_commands else None,
        "points": [_point(point) for point in item.points] if item.points else None,
        "href": item.href, "linkTitle": item.link_title, "tableRowId": item.table_row_id,
        "tableColumnId": item.table_column_id,
        "laneRowId": item.lane_row_id, "laneMemberId": item.lane_member_id,
        "markerStart": _marker(item.marker_start) if item.marker_start is not None else None,
        "markerEnd": _marker(item.marker_end) if item.marker_end is not None else None,
        "pattern": _pattern(item.pattern) if item.pattern is not None else None,
        "symbol": {"outline": [_path(path) for path in item.symbol.outline]} if item.symbol is not None else None,
        "icon": _icon(item) if item.kind == "Icon" else None,
        "paintOrder": item.paint_order,
        "hostPlacementId": item.host_placement_id,
        "clipSourceId": item.clip_source_id,
        "strokeClip": ({"outside": item.stroke_clip.outside, "region": _bounds(item.stroke_clip.region),
                        **({"outline": [_path(command) for command in item.stroke_clip.outline]}
                           if item.stroke_clip.outline else {})} if item.stroke_clip is not None else None),
        "fromInstanceId": item.from_instance_id,
        "toInstanceId": item.to_instance_id,
        "fanIn": ({"targetPortId": item.fan_in.target_port_id,
                   "terminalOwnerId": item.fan_in.terminal_owner_id}
                  if item.fan_in is not None else None),
        "contrastTreatment": item.contrast_treatment,
        "endTreatment": item.end_treatment if item.end_treatment != "closed" else None,
        "viewerFit": item.viewer_fit if item.viewer_fit != "raw" else None,
    }
    result.update(_omit(optional))
    return result


def _icon(item: ScenePrimitive) -> dict[str, Any]:
    if item.icon_kind is None or item.icon_asset_identity is None or item.icon_viewport is None:
        missing = tuple(name for name, value in (("icon_kind", item.icon_kind),
                                                  ("icon_asset_identity", item.icon_asset_identity),
                                                  ("icon_viewport", item.icon_viewport)) if value is None)
        raise _scene_error(f"Icon primitive {_brief(item.scene_id)} is missing required Scene fields {missing!r}")
    result: dict[str, Any] = {
        "kind": item.icon_kind, "assetIdentity": item.icon_asset_identity,
        "viewport": {"inlineSize": item.icon_viewport[0], "blockSize": item.icon_viewport[1]},
        "alternative": item.icon_alternative or "", "decorative": item.icon_decorative,
    }
    if item.icon_kind == "raster":
        result["encoding"] = "png"
    elif item.icon_kind == "vector":
        result["paths"] = [_icon_path(path) for path in item.icon_paths]
    return result


def _icon_path(path: SceneIconPath) -> dict[str, Any]:
    return _omit({"commands": [{"kind": kind, "points": [_point(point) for point in points]}
                                for kind, points in path.commands], "fill": path.fill,
                  "stroke": path.stroke, "strokeWidth": path.stroke_width,
                  "lineCap": path.line_cap, "lineJoin": path.line_join, "opacity": path.opacity})


def _text_layout(value: TextLayout) -> dict[str, Any]:
    result = {"bounds": _bounds(value.bounds), "baseline": _point(value.baseline),
            "lines": list(value.lines), "family": value.family, "weight": value.weight,
            "fontSize": value.font_size, "lineHeight": value.line_height,
            "assetIdentity": value.asset_identity}
    if value.letter_spacing != 0:
        result["letterSpacing"] = value.letter_spacing
    if value.text_transform != "none":
        result["textTransform"] = value.text_transform
    result["numericSpacing"] = value.numeric_spacing
    result["orientation"] = value.orientation
    result["rotationDegrees"] = value.rotation_degrees
    if value.horizontal_scale != 1:
        result["horizontalScale"] = value.horizontal_scale
    if value.runs:
        result["runs"] = [[{"text": run.text, "fontSize": run.font_size, "inlineSize": run.inline_size}
                           for run in line] for line in value.runs]
    if value.fit is not None:
        fit: dict[str, Any] = {"mode": value.fit.mode}
        if value.fit.line_inline_sizes:
            fit["adjust"] = value.fit.adjust
            fit["lineInlineSizes"] = list(value.fit.line_inline_sizes)
        else:
            fit["boxId"] = value.fit.box_id
            fit["endPadSpaces"] = value.fit.end_pad_spaces
        result["fit"] = fit
    return result


def _paint(value: ScenePaint) -> dict[str, Any]:
    result = _omit({"fill": value.fill, "stroke": value.stroke, "strokeWidth": value.stroke_width,
                    "dash": list(value.dash), "opacity": value.opacity,
                    "gradient": _gradient(value.gradient) if value.gradient is not None else None,
                    "shadow": _shadow(value.shadow) if value.shadow is not None else None,
                    "glow": _glow(value.glow) if value.glow is not None else None,
                    "radialGradient": _radial_gradient(value.radial_gradient) if value.radial_gradient is not None else None,
                    "wobble": _wobble(value.wobble) if value.wobble is not None else None,
                    "strokeFinish": _finish(value.stroke_finish) if value.stroke_finish is not None else None,
                    "image": _image(value.image) if value.image is not None else None})
    return result


def _image(value: Any) -> dict[str, Any]:
    """Serialize identity, viewport, and completed tiles only -- never raw bytes."""
    return {"assetIdentity": value.asset_identity,
            "viewport": {"inlineSize": value.viewport[0], "blockSize": value.viewport[1]},
            "tiles": [{"source": _bounds(tile.source), "destination": _bounds(tile.destination)}
                      for tile in value.tiles]}


def _gradient(value: LinearGradient) -> dict[str, Any]:
    stops = [{"offset": offset, "color": color} for offset, color in value.stops]
    if value.stop_opacities is not None:
        stops = [{**stop, "opacity": opacity} for stop, opacity in zip(stops, value.stop_opacities)]
    return {"start": _point(value.start), "end": _point(value.end), "stops": stops, "fidelity": value.fidelity}


def _radial_gradient(value: RadialGradient) -> dict[str, Any]:
    return {"center": _point(value.center), "radii": list(value.radii),
            "stops": [{"offset": stop.offset, "color": stop.color, "opacity": stop.opacity}
                      for stop in value.stops],
            "fidelity": value.fidelity}


def _shadow(value: Any) -> dict[str, Any]:
    return {"color": value.color, "offsetInline": value.offset_x, "offsetBlock": value.offset_y,
            "blur": value.blur, "opacity": value.opacity, "fidelity": value.fidelity}


def _glow(value: Any) -> dict[str, Any]:
    return {"color": value.color, "blur": value.blur, "opacity": value.opacity,
            "fidelity": value.fidelity, "region": _bounds(value.region)}


def _wobble(value: Any) -> dict[str, Any]:
    return {"amplitude": value.amplitude, "wavelength": value.wavelength, "seed": value.seed,
            "fidelity": value.fidelity, "closed": value.closed,
            "outline": [[[px, py] for px, py in polyline] for polyline in value.outline]}


def _finish(value: StrokeFinish) -> dict[str, Any]:
    return {"lineCap": value.line_cap, "lineJoin": value.line_join, "fidelity": value.fidelity}


def _marker(value: Any) -> dict[str, Any]:
    result = {"outline": [_path(item) for item in value.outline], "headLength": value.head_length,
            "headWidth": value.head_width, "attachmentOffset": value.attachment_offset,
            "paintMode": value.paint_mode}
    if value.angle_degrees is not None:
        result["angleDegrees"] = value.angle_degrees
    if value.physical_units:
        result["units"] = "userSpaceOnUse"
        if value.stroke_width is not None:
            result["strokeWidth"] = value.stroke_width
    return result


def _pattern(value: PatternGeometry) -> dict[str, Any]:
    if value.primitives:
        assert value.density_basis_points is not None and value.origin is not None
        assert value.region_bounds is not None and value.clip_bounds is not None
        assert value.corner_radius is not None
        primitives = []
        for item in value.primitives:
            if item.kind == "circle":
                primitive = {"kind": "circle", "cx": item.cx, "cy": item.cy,
                             "radius": item.radius}
                if item.fill_channel not in (None, "ink"):
                    primitive["fillChannel"] = item.fill_channel
                if item.stroke_width is not None:
                    primitive["strokeWidth"] = item.stroke_width
                primitives.append(primitive)
            elif item.kind == "rect":
                primitives.append({"kind": "rect", "x": item.x, "y": item.y,
                                   "inlineSize": item.inline_size, "blockSize": item.block_size})
            else:
                primitive = {"kind": "path", "paint": item.paint,
                             "commands": [{"kind": command.kind,
                                           "points": [coordinate for point in command.points
                                                      for coordinate in point]}
                                          for command in item.commands]}
                if item.paint == "stroke":
                    primitive.update(strokeWidth=item.stroke_width,
                                     lineCap=item.line_cap, lineJoin=item.line_join)
                primitives.append(primitive)
        return {"tileInlineSize": value.tile_inline_size,
                "tileBlockSize": value.tile_block_size,
                "angleDegrees": value.angle_degrees,
                "densityBasisPoints": value.density_basis_points,
                "primitives": primitives, "origin": _point(value.origin),
                "regionBounds": _bounds(value.region_bounds),
                "clipBounds": _bounds(value.clip_bounds),
                "cornerRadius": value.corner_radius}
    return {"tileInlineSize": value.tile_inline_size, "tileBlockSize": value.tile_block_size,
            "angleDegrees": value.angle_degrees,
            "strokes": [{"start": _point(item.start), "end": _point(item.end), "width": item.width}
                        for item in value.strokes]}


def _scale(value: Any) -> dict[str, Any]:
    return {"surfaceId": value.surface_id, "scaleId": value.scale_id,
            "domainStart": value.domain_start.isoformat(), "domainEnd": value.domain_end.isoformat(),
            "rangeStart": value.range_start, "rangeEnd": value.range_end,
            "origin": value.origin, "unitRatio": value.unit_ratio}


def _path(value: Any) -> dict[str, Any]:
    return {"kind": value.kind, "points": [_point(point) for point in value.points]}


def _bounds(value: tuple[float, float, float, float]) -> dict[str, float]:
    return {"inline": value[0], "block": value[1], "inlineSize": value[2], "blockSize": value[3]}


def _viewport(value: tuple[float, float]) -> dict[str, float]:
    return {"inlineSize": value[0], "blockSize": value[1]}


def _point(value: tuple[float, float]) -> list[float]:
    return [value[0], value[1]]


def _omit(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item is not None}
