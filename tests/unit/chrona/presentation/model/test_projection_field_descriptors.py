from datetime import date

from chrona.presentation.contracts.resources import (
    ViewComparison,
    ViewInput,
    ViewRow,
    ViewRowItem,
    ViewRows,
    ViewVisibility,
    ViewWindow,
)
from chrona.presentation.model.field_roles import FieldDescriptor, FieldRoleBindings
from chrona.presentation.model.projection import build_review_projection


def _project(title):
    return {
        "objects": {"same-id": {"title": title, "fields": {"risk": "high"}}},
        "entities": {},
        "fieldRoles": {"risk": "risk"},
    }


def _view():
    row = ViewRow("r", None, 0, None, None, None, (
        ViewRowItem("snapshot-item", "snapshot", "same-id", "stacked"),
        ViewRowItem("scenario-item", "scenario", "same-id", "stacked", scenario_id="variant"),
        ViewRowItem("primary-item", "primary", "same-id", "stacked"),
    ))
    return ViewInput(
        None, None, None,
        ViewWindow("selected-planned", None, None, 0),
        ViewComparison(None, "optional", None, None, ()),
        ViewVisibility(False, "none", "none"), (), (),
        ViewRows("explicit", (row,)), None, (), None, None, None,
    )


def _bindings(kind):
    return FieldRoleBindings.from_project(
        {"fieldRoles": {"risk": "risk"}},
        object_descriptors={
            "same-id": (FieldDescriptor("risk", kind, enum_values=(("high",) if kind == "enum" else ())),),
        },
    )


def test_projection_keeps_exact_primary_snapshot_and_scenario_descriptors():
    primary_bindings = _bindings("enum")
    snapshot_bindings = _bindings("string")
    scenario_bindings = _bindings("boolean")
    projection = build_review_projection(
        _project("Primary"),
        {"same-id": {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}},
        _view(), None,
        snapshot_project=_project("Snapshot"),
        snapshot_placements={"same-id": {"start": date(2025, 12, 1), "end": date(2025, 12, 2)}},
        scenarios={"variant": (
            _project("Scenario"),
            {"same-id": {"start": date(2026, 2, 1), "end": date(2026, 2, 2)}},
        )},
        field_bindings=primary_bindings,
        snapshot_field_bindings=snapshot_bindings,
        scenario_field_bindings={"variant": scenario_bindings},
    )

    items = {item.source_kind: item for item in projection.rows[0].items}
    assert set(items) == {"primary", "snapshot", "scenario"}
    assert {item.object_id for item in items.values()} == {"same-id"}
    assert items["primary"].field_bindings is primary_bindings
    assert items["snapshot"].field_bindings is snapshot_bindings
    assert items["scenario"].field_bindings is scenario_bindings
    assert {
        source: item.field_bindings.read_result(
            item.fields, {"fieldRole": "risk"}, object_id=item.object_id
        ).descriptor.kind
        for source, item in items.items()
    } == {"primary": "enum", "snapshot": "string", "scenario": "boolean"}


def test_projection_defaults_keep_existing_source_local_bindings_without_descriptors():
    projection = build_review_projection(
        _project("Primary"),
        {"same-id": {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}},
        _view(), None,
        snapshot_project=_project("Snapshot"),
        snapshot_placements={"same-id": {"start": date(2025, 12, 1), "end": date(2025, 12, 2)}},
        scenarios={"variant": (
            _project("Scenario"),
            {"same-id": {"start": date(2026, 2, 1), "end": date(2026, 2, 2)}},
        )},
    )

    items = {item.source_kind: item for item in projection.rows[0].items}
    assert {source: item.field_bindings.field_for("risk") for source, item in items.items()} == {
        "primary": "risk", "snapshot": "risk", "scenario": "risk",
    }
    assert all(item.field_bindings.read_result(
        item.fields, {"fieldRole": "risk"}, object_id=item.object_id
    ).descriptor is None for item in items.values())
