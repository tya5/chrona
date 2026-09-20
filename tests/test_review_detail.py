from copy import deepcopy
from datetime import date
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import pytest

from chrona.presentation_scene import SurfaceContentInput, build_presentation_scene
from chrona.presentation_settings import builtin_bases
from chrona.presentation_svg import render_scene_surface_svg
from chrona.review_detail import ReviewDetailError, resolve_review_detail_profile


def items():
    return (
        SimpleNamespace(object_id="task", title="Task", source_type="span",
                        planned={"start": date(2026, 1, 1), "end": date(2026, 1, 10)},
                        actual=None, finish_delta=None, group_id="firmware", group_label="Firmware", fields={}),
        SimpleNamespace(object_id="gate", title="Release Gate", source_type="point",
                        planned={"at": date(2026, 1, 20)}, actual=None, finish_delta=None,
                        group_id="validation", group_label="Validation", fields={}),
    )


def settings():
    value = builtin_bases()["executive-v0.2"]
    value["context"]["viewport"]["height"] = 1200
    value["layout"]["regions"].append({
        "id": "detail", "layout": "grid",
        "block": {"kind": "fixed", "value": 260, "min": 260, "max": 260},
        "tracks": [
            {"kind": "fraction", "value": 1, "min": 0, "max": 10000},
            {"kind": "fraction", "value": 2, "min": 0, "max": 10000},
            {"kind": "fraction", "value": 1, "min": 0, "max": 10000},
        ],
        "gap": 12,
    })
    value["layout"]["slots"].update({
        "groupDetails": {"region": "detail", "track": 0, "source": "group-details",
                         "priority": "required", "overflow": "diagnose", "align": "stretch"},
        "observations": {"region": "detail", "track": 1, "source": "observations",
                         "priority": "required", "overflow": "diagnose", "align": "stretch"},
        "milestones": {"region": "detail", "track": 2, "source": "milestones",
                       "priority": "required", "overflow": "diagnose", "align": "stretch"},
    })
    return value


def profile():
    return {
        "version": "chrona/review-detail-profile/v0.1", "id": "detail",
        "body": {
            "groupDetails": [
                {"groupId": "validation", "label": "Validation", "description": "Release evidence."},
                {"groupId": "firmware", "label": "Firmware", "description": "Implementation readiness."},
            ],
            "milestones": ["gate"],
            "observations": {
                "columns": [{"id": "owner", "label": "Owner"}, {"id": "status", "label": "Status"}],
                "rows": [{"id": "note-1", "source": "example-record-R-001", "emphasis": "attention",
                          "cells": {"owner": "Firmware", "status": "Attention"}}],
            },
        },
    }


def content(resolved):
    return SurfaceContentInput(
        group_details=resolved.group_details, milestones=resolved.milestones,
        observation_columns=resolved.observation_columns,
        observation_rows=resolved.observation_rows,
    )


def test_profile_resolves_selected_facts_and_view_group_order():
    resolved = resolve_review_detail_profile(profile(), items(), settings())
    assert [entry[0] for entry in resolved.group_details] == ["firmware", "validation"]
    assert resolved.milestones == (("gate", "Release Gate", date(2026, 1, 20)),)
    assert resolved.observation_rows[0][1] == "example-record-R-001"


def test_profile_rejects_schema_semantics_references_and_slot_mismatch():
    invalid = profile()
    invalid["body"]["observations"]["rows"][0]["cells"].pop("status")
    with pytest.raises(ReviewDetailError, match="E_DETAIL_OBSERVATION_CELLS"):
        resolve_review_detail_profile(invalid, items(), settings())

    invalid = profile()
    invalid["body"]["milestones"] = ["task"]
    with pytest.raises(ReviewDetailError, match="E_DETAIL_MILESTONE_REFERENCE"):
        resolve_review_detail_profile(invalid, items(), settings())

    invalid = profile()
    invalid["body"]["groupDetails"][0]["groupId"] = "unknown"
    with pytest.raises(ReviewDetailError, match="E_DETAIL_GROUP_REFERENCE"):
        resolve_review_detail_profile(invalid, items(), settings())

    no_slot = settings()
    del no_slot["layout"]["slots"]["milestones"]
    with pytest.raises(ReviewDetailError, match="E_DETAIL_SLOT_REQUIRED:milestones"):
        resolve_review_detail_profile(profile(), items(), no_slot)


def test_scene_owns_detail_geometry_metadata_and_deterministic_svg():
    config = settings()
    resolved = resolve_review_detail_profile(profile(), items(), config)
    scene = build_presentation_scene("Review", items(), (date(2026, 1, 1), date(2026, 2, 1)),
                                     config, content(resolved))
    surface = next(value for value in scene.surfaces if value.surface_id == "table-timeline")
    purposes = {node.purpose for node in surface.primitives}
    assert {"group-detail-label", "group-detail-description", "observation-cell",
            "observation-source", "milestone-digest-symbol", "milestone-digest-entry"} <= purposes
    assert scene.manifest.content_family_counts.group_details == 2
    assert scene.manifest.content_family_counts.milestones == 1
    assert scene.manifest.content_family_counts.observation_rows == 1
    svg = render_scene_surface_svg(surface, viewport=config["context"]["viewport"],
                                   theme=config["theme"], output=config["output"])
    assert svg == render_scene_surface_svg(surface, viewport=config["context"]["viewport"],
                                           theme=config["theme"], output=config["output"])
    root = ET.fromstring(svg)
    source = next(node for node in root.iter() if node.get("data-purpose") == "observation-source")
    assert source.get("data-source-ref") == "note-1" and source.text == "example-record-R-001"
    header = next(node for node in root.iter() if node.get("data-purpose") == "observation-header-band")
    label = next(node for node in root.iter() if node.get("data-purpose") == "observation-column-label")
    assert header.get("fill") == config["theme"]["paints"]["tableHeader"]["color"]
    assert label.get("fill") == config["theme"]["paints"]["text"]["color"]


def test_required_detail_overflow_diagnoses_with_owned_source():
    config = settings()
    detail_region = next(value for value in config["layout"]["regions"] if value["id"] == "detail")
    detail_region["block"] = {"kind": "fixed", "value": 40, "min": 40, "max": 40}
    resolved = resolve_review_detail_profile(profile(), items(), config)
    with pytest.raises(ValueError, match="E_LAYOUT_REQUIRED_OVERFLOW"):
        build_presentation_scene("Review", items(), (date(2026, 1, 1), date(2026, 2, 1)),
                                 config, content(resolved))


def test_required_slot_without_profile_content_is_rejected():
    with pytest.raises(ReviewDetailError, match="E_LAYOUT_SOURCE_UNAVAILABLE:groupDetails"):
        resolve_review_detail_profile(None, items(), settings())


def test_profile_independent_surface_bytes_are_unchanged():
    config = builtin_bases()["executive-v0.2"]
    resolved = resolve_review_detail_profile(None, items(), config)
    assert resolved == type(resolved)()
    direct = build_presentation_scene("Review", items(), (date(2026, 1, 1), date(2026, 2, 1)), config)
    explicit = build_presentation_scene("Review", items(), (date(2026, 1, 1), date(2026, 2, 1)),
                                        config, content(resolved))
    direct_surface = next(value for value in direct.surfaces if value.surface_id == "table-timeline")
    explicit_surface = next(value for value in explicit.surfaces if value.surface_id == "table-timeline")
    assert render_scene_surface_svg(direct_surface, viewport=config["context"]["viewport"],
                                    theme=config["theme"], output=config["output"]) == \
           render_scene_surface_svg(explicit_surface, viewport=config["context"]["viewport"],
                                    theme=config["theme"], output=config["output"])
