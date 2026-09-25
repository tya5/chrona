"""Explicit, schema-validated serialization of completed inspection Scenes."""
from __future__ import annotations

import json
import math
from typing import Any, Mapping

import jsonschema

from chrona.presentation.scene.model import (
    InspectionScene, LinearGradient, PatternGeometry, SceneIconPath,
    ScenePaint, ScenePrimitive, SceneSurface, StrokeFinish, TextLayout,
)
from chrona.resources import schema_document


class SceneSerializationError(ValueError):
    """The completed Scene cannot truthfully become its public document."""


def serialize_scene(scene: InspectionScene) -> bytes:
    """Return canonical UTF-8 scene-v0.6 JSON after typed and schema validation."""
    document = scene_document(scene)
    validate_scene_document(document)
    try:
        return (json.dumps(document, ensure_ascii=False, separators=(",", ":"),
                           allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError) as error:
        raise SceneSerializationError("E_SCENE_SERIALIZATION") from error


def scene_document(scene: InspectionScene) -> dict[str, Any]:
    """Map each public Scene field explicitly; no dataclass reflection is used."""
    return {
        "version": "chrona/scene/v0.6",
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
    }


def validate_scene_document(document: Mapping[str, Any]) -> None:
    """Validate schema shape plus cross-reference invariants JSON Schema cannot state."""
    try:
        errors = tuple(jsonschema.Draft202012Validator(
            schema_document("scene-v0.6.schema.yaml")
        ).iter_errors(document))
    except Exception as error:  # schema resource failures have no public partial document
        raise SceneSerializationError("E_SCENE_SERIALIZATION") from error
    if errors or not _finite(document) or not _references_are_closed(document):
        raise SceneSerializationError("E_SCENE_SERIALIZATION")


def _references_are_closed(document: Mapping[str, Any]) -> bool:
    surfaces = document.get("surfaces")
    if not isinstance(surfaces, list):
        return False
    for surface in surfaces:
        if not isinstance(surface, Mapping):
            return False
        slots = {item.get("id") for item in surface.get("slots", ()) if isinstance(item, Mapping)}
        rows = {item.get("id") for item in surface.get("rows", ()) if isinstance(item, Mapping)}
        columns = {item.get("id") for item in surface.get("columns", ()) if isinstance(item, Mapping)}
        if (None in slots or None in rows or None in columns or len(slots) != len(surface.get("slots", ()))
                or len(rows) != len(surface.get("rows", ())) or len(columns) != len(surface.get("columns", ()) )):
            return False
        primitives = surface.get("primitives", ())
        by_id = {item.get("id"): (index, item) for index, item in enumerate(primitives)
                 if isinstance(item, Mapping)}
        if len(by_id) != len(primitives):
            return False
        for index, primitive in enumerate(primitives):
            if not isinstance(primitive, Mapping):
                return False
            row, column, purpose = primitive.get("tableRowId"), primitive.get("tableColumnId"), primitive.get("purpose")
            if primitive.get("slotId") not in slots:
                return False
            if purpose == "table-cell":
                if row not in rows or column not in columns:
                    return False
            elif purpose == "table-column-label":
                if row is not None or column not in columns:
                    return False
            elif row is not None or column is not None:
                return False
            clip_source_id = primitive.get("clipSourceId")
            if clip_source_id is not None:
                source = by_id.get(clip_source_id)
                if (source is None or source[0] >= index or source[1].get("kind") not in {"Rect", "Symbol"}
                        or (source[1].get("kind") == "Symbol" and not source[1].get("symbol"))
                        or source[1].get("slotId") != primitive.get("slotId")):
                    return False
    return True


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
        "rows": [{"id": item.row_id, "objectId": item.object_id, "groupId": item.group_id,
                  "bounds": _bounds(item.bounds)} for item in surface.rows],
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
    if surface.canvas_bounds is not None:
        result["canvasBounds"] = _bounds(surface.canvas_bounds)
    if surface.fit_warnings:
        result["fitWarnings"] = [_fit_warning(item) for item in surface.fit_warnings]
    return result


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
        "markerStart": _marker(item.marker_start) if item.marker_start is not None else None,
        "markerEnd": _marker(item.marker_end) if item.marker_end is not None else None,
        "pattern": _pattern(item.pattern) if item.pattern is not None else None,
        "symbol": {"outline": [_path(path) for path in item.symbol.outline]} if item.symbol is not None else None,
        "icon": _icon(item) if item.kind == "Icon" else None,
        "paintOrder": item.paint_order if item.paint_order else None,
        "clipSourceId": item.clip_source_id,
        "endTreatment": item.end_treatment if item.end_treatment != "closed" else None,
    }
    result.update(_omit(optional))
    return result


def _icon(item: ScenePrimitive) -> dict[str, Any]:
    if item.icon_kind is None or item.icon_asset_identity is None or item.icon_viewport is None:
        raise SceneSerializationError("E_SCENE_SERIALIZATION")
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
    return result


def _paint(value: ScenePaint) -> dict[str, Any]:
    result = _omit({"fill": value.fill, "stroke": value.stroke, "strokeWidth": value.stroke_width,
                    "dash": list(value.dash), "opacity": value.opacity,
                    "gradient": _gradient(value.gradient) if value.gradient is not None else None,
                    "shadow": _shadow(value.shadow) if value.shadow is not None else None,
                    "strokeFinish": _finish(value.stroke_finish) if value.stroke_finish is not None else None})
    return result


def _gradient(value: LinearGradient) -> dict[str, Any]:
    return {"start": _point(value.start), "end": _point(value.end),
            "stops": [{"offset": offset, "color": color} for offset, color in value.stops],
            "fidelity": value.fidelity}


def _shadow(value: Any) -> dict[str, Any]:
    return {"color": value.color, "offsetInline": value.offset_x, "offsetBlock": value.offset_y,
            "blur": value.blur, "opacity": value.opacity, "fidelity": value.fidelity}


def _finish(value: StrokeFinish) -> dict[str, Any]:
    return {"lineCap": value.line_cap, "lineJoin": value.line_join, "fidelity": value.fidelity}


def _marker(value: Any) -> dict[str, Any]:
    return {"outline": [_path(item) for item in value.outline], "headLength": value.head_length,
            "headWidth": value.head_width, "attachmentOffset": value.attachment_offset,
            "paintMode": value.paint_mode}


def _pattern(value: PatternGeometry) -> dict[str, Any]:
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
