"""Final completed legend ambiguity diagnostics (#1703)."""
from xml.etree import ElementTree

from tests.integration.test_realized_legends import _detail, _parts, _render, _source
from tests.support import synthetic_review as sr


def _codes(rendered):
    return tuple(item.payload["code"] for item in rendered.warning_records)


def test_realized_equal_actual_and_planned_figures_warn_with_both_semantic_keys(tmp_path):
    parts = _parts()
    bindings = parts["theme"]["body"]["colorBindings"]
    bindings["planned.fill"] = "positive"
    parts["theme"]["body"]["roles"]["planned"]["markCornerRadius"] = "mark-radius-rounded"
    detail = _detail()
    detail["body"]["legend"] = [{"role": "planned", "label": "Work"},
                                  {"role": "actual", "label": "Observed"}]
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "collision-actual",
              "body": {"asOf": "2026-02-20", "observations": [
                  {"id": "track-observed", "sequence": 1, "projectObjectId": "track",
                   "actual": {"start": "2026-02-02", "finish": "2026-02-11"}}]}}
    rendered = _render(tmp_path, _source(), actual=actual, parts=parts, detail=detail)

    assert "W_LEGEND_SWATCH_COLLISION" in _codes(rendered)
    collision = next(item for item in rendered.warning_records
                     if item.payload["code"] == "W_LEGEND_SWATCH_COLLISION")
    subjects = collision.payload["sourceSubjects"]
    assert len(subjects) == 2
    assert {subject["title"] for subject in subjects} == {"Work (planned)", "Observed (actual)"}
    assert "same completed figure" in collision.payload["message"]
    assert "no further detail" not in collision.payload["message"]
    swatches = tuple(item for item in rendered.surface.primitives if item.purpose == "legend-swatch")
    matching = tuple(item for item in swatches if item.visual_role in {"planned", "actual"})
    assert len({item.paint.fill for item in matching}) == 1
    assert "W_LEGEND_SWATCH_COLLISION" in rendered.scene.diagnostics
    svg = ElementTree.fromstring(rendered.artifact.content)
    serialized_ids = {node.attrib.get("data-scene-id") for node in svg.iter()}
    assert {item.scene_id for item in matching} <= serialized_ids
    collision_refs = {subject["sourceRef"].removeprefix("legend-key:") for subject in subjects}
    assert collision_refs == {"planned", next(item.source_ref for item in matching
                                               if item.visual_role == "actual")}
    assert len(tuple(item for item in matching if item.source_ref in collision_refs)) == 2


def test_duplicate_displayed_label_is_checked_after_scope_text_and_filters(tmp_path):
    parts = _parts()
    detail = _detail()
    detail["body"]["legend"] = [{"role": "planned", "label": "Shared"},
                                  {"role": "actual", "label": "Shared"}]
    # Both meanings are present in the final projection; the displayed text is the
    # completed label, not its source label or key identity.
    source = _source()
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "duplicate-label-actual",
              "body": {"asOf": "2026-02-20", "observations": [
                  {"id": "track-observed", "sequence": 1, "projectObjectId": "track",
                   "actual": {"start": "2026-02-02", "finish": "2026-02-11"}}]}}
    rendered = _render(tmp_path, source, actual=actual, parts=parts, detail=detail)

    assert "W_LEGEND_LABEL_DUPLICATE" in _codes(rendered)
    duplicate = next(item for item in rendered.warning_records
                     if item.payload["code"] == "W_LEGEND_LABEL_DUPLICATE")
    assert {subject["title"] for subject in duplicate.payload["sourceSubjects"]} == {
        "Shared (planned)", "Shared (actual)"}
    assert "same displayed label" in duplicate.payload["message"]
    assert "no further detail" not in duplicate.payload["message"]


def test_filtered_away_duplicate_candidates_do_not_warn(tmp_path):
    parts = _parts()
    detail = _detail(("actual", "Same"), ("forecast", "Same"))
    rendered = _render(tmp_path, _source(), parts=parts, detail=detail)

    assert "W_LEGEND_LABEL_DUPLICATE" not in _codes(rendered)


def test_equal_black_point_states_share_one_complete_faithful_key(tmp_path):
    """One owner and identical completed figure cover both states without duplicate keys."""
    parts = _parts()
    colors = parts["scheme"]["body"]["colors"]
    colors.update(text="#101828", accent="#101828", positive="#101828",
                  insideLabelPlanned="#FFFFFF", insideLabelActual="#FFFFFF")
    parts["theme"]["body"]["values"]["milestone-symbol"]["value"] = {
        "shape": "glyph", "viewBox": [10, 10], "parts": [
            {"d": "M5 0L10 5L5 10L0 5Z", "paint": "fill"},
            {"d": "M5 0L10 5L5 10L0 5Z", "paint": "stroke"},
        ],
    }
    source = _source()
    actual = {
        "version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "black-point-actual",
        "body": {"asOf": "2026-02-20", "observations": [
            {"id": "gate-observed", "sequence": 1, "projectObjectId": "gate",
             "actual": {"at": "2026-02-13"}},
        ]},
    }
    detail = _detail(("milestone", "Gate"))
    rendered = sr.render(tmp_path, source, presentation=parts, actual=actual,
                         detail=detail, viewport=(1600, 900))

    assert "W_LEGEND_SWATCH_COLLISION" not in _codes(rendered)
    assert [item.text for item in rendered.surface.primitives
            if item.purpose == "legend-label" and item.source_ref.startswith("milestone:")] == ["Gate"]

    swatches = tuple(item for item in rendered.surface.primitives
                     if item.purpose == "legend-swatch"
                     and item.scene_id.startswith(("legend-swatch:actual:", "legend-swatch:milestone")))
    assert len(swatches) == 3  # One complete three-part diamond key, not a palette union.
    assert {item.source_ref.split(":", 1)[0] for item in swatches} == {"milestone"}
    figures = {source_ref: tuple(item for item in swatches if item.source_ref == source_ref)
               for source_ref in {item.source_ref for item in swatches}}
    assert len(figures) == 1 and {len(parts) for parts in figures.values()} == {3}
    assert all(item.paint.fill == "#101828" or item.paint.stroke == "#101828" for item in swatches)
    svg = ElementTree.fromstring(rendered.artifact.content)
    serialized = {node.get("data-scene-id"): node for node in svg.iter()
                  if node.get("data-scene-id")}
    assert {item.scene_id for item in swatches} <= serialized.keys()
    assert all(serialized[item.scene_id].get("fill") == "#101828"
               or serialized[item.scene_id].get("stroke") == "#101828" for item in swatches)
