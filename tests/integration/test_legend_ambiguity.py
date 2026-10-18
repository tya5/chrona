"""Final completed legend ambiguity diagnostics (#1703)."""
from xml.etree import ElementTree

from tests.integration.test_realized_legends import _detail, _parts, _render, _source


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
    assert {subject["sourceRef"].removeprefix("legend-key:") for subject in subjects} == {
        item.source_ref for item in matching}


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
