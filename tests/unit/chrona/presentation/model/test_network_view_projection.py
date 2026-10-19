from datetime import date
from dataclasses import replace
import pytest

from chrona.presentation.contracts.resources import (
    ViewComparison,
    ViewInput,
    ViewNetworkIntent,
    ViewOrdering,
    ViewRow,
    ViewRowItem,
    ViewRows,
    ViewSelection,
    ViewVisibility,
    ViewWindow,
    freeze,
)
from chrona.presentation.model.field_roles import FieldDescriptor, FieldRoleBindings
from chrona.presentation.model.projection import (
    NetworkLabelSourceError,
    build_review_projection,
)


def _project(objects=None, relations=()):
    source_objects = objects or {
        "z": {"title": "Zulu", "fields": {"caption": "Z label"}},
        "a": {"title": "Alpha", "fields": {"caption": "A label"}},
        "m": {"title": "Middle", "fields": {"caption": "M label"}},
        "outside": {"title": "Outside", "fields": {"caption": "Hidden"}},
    }
    return {
        "version": "timeline/v0.7",
        "project": {"id": "network-projection"},
        "objects": {
            object_id: {
                "type": "task",
                "title": value["title"],
                "fields": value.get("fields", {}),
                "schedule": {"mode": "fixed-span", "start": "2027-01-01", "end": "2027-01-02"},
            }
            for object_id, value in source_objects.items()
        },
        "entities": {},
        "relations": list(relations),
    }


def _view(*, selected=("z", "a", "m"), ordering=None, rows_mode="automatic",
          row_order=None, label_source="title"):
    items = tuple(
        ViewRowItem(object_id, "primary", object_id, "stacked")
        for object_id in (row_order or selected)
    )
    rows = ViewRows(
        rows_mode,
        (ViewRow("explicit-row", None, 0, None, None, None, items),)
        if rows_mode == "explicit" else (),
    )
    return ViewInput(
        selection=ViewSelection(tuple(selected), ("span",)),
        grouping=None,
        ordering=ordering,
        window=ViewWindow("selected-planned", None, None, 0),
        comparison=ViewComparison(None, "optional", None, None, ()),
        visibility=ViewVisibility(False, "semantic", "none"),
        table_columns=(),
        annotations=(),
        rows=rows,
        axis=None,
        markers=(),
        shading=None,
        time_presentation=None,
        annotation_presentation=None,
        surface="dependency-network",
        network=ViewNetworkIntent(label_source),
    )


def _placements(object_ids):
    return {
        object_id: {"start": date(2027, 1, 1), "end": date(2027, 1, 2)}
        for object_id in object_ids
    }


@pytest.mark.parametrize("rows_mode", ("automatic", "explicit"))
def test_network_nodes_use_global_ordering_for_each_row_mode(rows_mode):
    project = _project()
    placements = _placements(project["objects"])
    # The explicit row deliberately lists the reverse order. The network uses
    # the same global View ordering without changing that row's own order.
    view = _view(
        rows_mode=rows_mode,
        row_order=("z", "a", "m"),
        ordering=ViewOrdering("plannedStart", "descending", "title"),
    )

    projection = build_review_projection(project, placements, view, None)

    assert projection.network is not None
    assert [node.object_id for node in projection.network.nodes] == ["a", "m", "z"]
    assert [node.order_key for node in projection.network.nodes] == [(0,), (1,), (2,)]
    if rows_mode == "explicit":
        assert [item.object_id for item in projection.rows[0].items] == ["z", "a", "m"]
        timeline_projection = build_review_projection(
            project, placements, replace(view, surface="table-timeline", network=None), None,
        )
        assert [item.object_id for item in timeline_projection.rows[0].items] == ["z", "a", "m"]


@pytest.mark.parametrize("rows_mode", ("automatic", "explicit"))
def test_network_global_order_uses_primary_descending_values_before_tie_break(rows_mode):
    project = _project()
    placements = _placements(project["objects"])
    placements.update({
        "z": {"start": date(2027, 1, 1), "end": date(2027, 1, 2)},
        "a": {"start": date(2027, 1, 3), "end": date(2027, 1, 4)},
        "m": {"start": date(2027, 1, 2), "end": date(2027, 1, 3)},
    })
    view = _view(
        rows_mode=rows_mode,
        row_order=("z", "a", "m"),
        ordering=ViewOrdering("plannedStart", "descending", "id"),
    )

    projection = build_review_projection(project, placements, view, None)

    assert projection.network is not None
    assert [node.object_id for node in projection.network.nodes] == ["a", "m", "z"]


def test_network_selection_closes_edges_to_selected_nodes_only():
    project = _project(relations=(
        {"id": "kept", "type": "dependency", "from": {"object": "z"}, "to": {"object": "a"}},
        {"id": "outgoing", "type": "dependency", "from": {"object": "a"}, "to": {"object": "outside"}},
        {"id": "incoming", "type": "dependency", "from": {"object": "outside"}, "to": {"object": "z"}},
    ))
    view = _view(selected=("z", "a"))

    projection = build_review_projection(project, _placements(project["objects"]), view, None)

    assert projection.network is not None
    assert {node.object_id for node in projection.network.nodes} == {"z", "a"}
    assert [(edge.relation_id, edge.source_id, edge.target_id) for edge in projection.network.edges] == [
        ("relation:id:kept", "z", "a"),
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        ("title", {"z": "Zulu", "a": "Alpha", "m": "Middle"}),
        ("id", {"z": "z", "a": "a", "m": "m"}),
        (freeze({"field": "caption"}), {"z": "Z label", "a": "A label", "m": "M label"}),
        (freeze({"fieldRole": "responsible"}), {"z": "Zulu", "a": "Alpha", "m": "Middle"}),
    ),
)
def test_network_node_labels_resolve_title_id_and_shared_field_forms(source, expected):
    project = _project()
    view = _view(label_source=source)

    projection = build_review_projection(project, _placements(project["objects"]), view, None)

    assert projection.network is not None
    assert {node.object_id: node.title for node in projection.network.nodes} == expected


@pytest.mark.parametrize("label_source", ("omitted", None))
def test_network_omitted_or_null_label_source_uses_project_titles(label_source):
    project = _project()
    view = _view(label_source="title" if label_source == "omitted" else label_source)
    if label_source == "omitted":
        view = replace(view, network=ViewNetworkIntent())

    projection = build_review_projection(project, _placements(project["objects"]), view, None)

    assert projection.network is not None
    assert {node.object_id: node.title for node in projection.network.nodes} == {
        "z": "Zulu", "a": "Alpha", "m": "Middle",
    }


def test_network_label_field_role_uses_its_source_local_profile_default():
    project = _project(objects={"z": {"title": "Zulu", "fields": {}}})
    bindings = FieldRoleBindings.from_project(
        {**project, "fieldRoles": {"responsible": "display_name"}},
        object_descriptors={
            "z": (FieldDescriptor("display_name", "string", default="Assigned by profile", has_default=True),),
        },
    )
    projection = build_review_projection(
        project,
        _placements(project["objects"]),
        _view(selected=("z",), label_source=freeze({"fieldRole": "responsible"})),
        None,
        field_bindings=bindings,
    )

    assert projection.network is not None
    assert projection.network.nodes[0].title == "Assigned by profile"


@pytest.mark.parametrize(
    ("fields", "source", "expected"),
    (
        ({}, freeze({"field": "caption"}), "Zulu"),
        ({"caption": None}, freeze({"field": "caption"}), "Zulu"),
        ({}, freeze({"fieldRole": "unbound"}), "Zulu"),
        ({"caption": ""}, freeze({"field": "caption"}), ""),
    ),
)
def test_network_field_missing_null_unbound_and_empty_string_semantics(fields, source, expected):
    project = _project(objects={"z": {"title": "Zulu", "fields": fields}})
    projection = build_review_projection(
        project, _placements(project["objects"]), _view(selected=("z",), label_source=source), None,
    )

    assert projection.network is not None
    assert projection.network.nodes[0].title == expected


@pytest.mark.parametrize("invalid", (True, 7, ["name"], {"name": "Zulu"}))
def test_network_field_nonstring_fails_with_typed_source_and_object_identity(invalid):
    project = _project(objects={"z": {"title": "Zulu", "fields": {"caption": invalid}}})

    with pytest.raises(NetworkLabelSourceError) as caught:
        build_review_projection(
            project,
            _placements(project["objects"]),
            _view(selected=("z",), label_source=freeze({"field": "caption"})),
            None,
        )

    error = caught.value
    assert (error.code, error.source_ref, error.object_id, error.title, error.value_type) == (
        "E_VIEW_NETWORK_LABEL_SOURCE", "/body/network/nodeLabel/source", "z", "Zulu", type(invalid).__name__,
    )
