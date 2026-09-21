from datetime import date

from chrona.presentation.model.projection import build_review_projection


def test_explicit_row_composes_serial_task_and_milestone_under_one_owner():
    project = {"objects": {
        "design": {"title": "Design", "fields": {"owner": "A"}},
        "implement": {"title": "Implement", "fields": {"owner": "A"}},
        "gate": {"title": "Gate", "fields": {"owner": "A"}},
    }, "entities": {}}
    view = {"body": {
        "comparison": {"actual": "optional"},
        "window": {"mode": "selected-planned"},
        "rows": {"mode": "explicit", "items": [{
            "id": "owner-a", "label": "Owner A", "group": "firmware",
            "tableSubject": "design", "items": [
                {"id": "design", "source": {"kind": "primary", "object": "design"}},
                {"id": "implement", "source": {"kind": "primary", "object": "implement"}},
                {"id": "gate", "source": {"kind": "primary", "object": "gate"}},
            ],
        }]},
    }}
    projection = build_review_projection(project, {
        "design": {"start": date(2026, 1, 1), "end": date(2026, 1, 5)},
        "implement": {"start": date(2026, 1, 5), "end": date(2026, 1, 10)},
        "gate": {"at": date(2026, 1, 10)},
    }, view, None)

    assert len(projection.rows) == 1
    row = projection.rows[0]
    assert (row.row_id, row.label, row.group_id, row.table_subject_id) == ("owner-a", "Owner A", "firmware", "design")
    assert [(item.item_id, item.object_id, item.source_kind) for item in row.items] == [
        ("design", "design", "primary"), ("implement", "implement", "primary"), ("gate", "gate", "primary")]


def test_explicit_row_resolves_named_snapshot_item():
    project = {"objects": {"task": {"title": "Current", "fields": {}}}, "entities": {}}
    historic = {"objects": {"task": {"title": "Historic", "fields": {}}}, "entities": {}}
    view = {"body": {"comparison": {"actual": "optional"}, "window": {"mode": "selected-planned"},
        "rows": {"mode": "explicit", "items": [{"id": "r", "items": [
            {"id": "old", "source": {"kind": "snapshot", "object": "task"}},
            {"id": "now", "source": {"kind": "primary", "object": "task"}}]}]}}}
    projection = build_review_projection(project, {"task": {"start": date(2026, 2, 1), "end": date(2026, 2, 2)}},
        view, None, snapshot_project=historic,
        snapshot_placements={"task": {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}})
    assert [(item.source_kind, item.title, item.planned["start"]) for item in projection.rows[0].items] == [
        ("snapshot", "Historic", date(2026, 1, 1)), ("primary", "Current", date(2026, 2, 1))]
