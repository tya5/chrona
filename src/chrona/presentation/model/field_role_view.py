"""Resolve primary-Project role availability before presentation composition."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import replace
from typing import Any, TypeVar

from chrona.presentation.contracts.resources import (
    ContractError, TableColumn, ViewGrouping, ViewInput, ViewLaneColumn, _PrivateGroupingMode, freeze,
)
from chrona.presentation.model.field_roles import FieldRoleBindings
from chrona.presentation.model.info_diagnostics import UnboundFieldRole


_Column = TypeVar("_Column", TableColumn, ViewLaneColumn)


def resolve_role_grouping(grouping: ViewGrouping | None,
                          bindings: FieldRoleBindings) -> ViewGrouping | None:
    """Select the declared field or the View's explicit unbound-role fallback."""
    if grouping is None or grouping.field_role is None:
        return grouping
    field = bindings.field_for(grouping.field_role)
    if field is None and grouping.fallback == "hierarchy":
        return replace(grouping, by=_PrivateGroupingMode.PROJECT_ROOT_GROUP,
                       field=None, field_role=None, fallback=None)
    return replace(grouping, by="field" if field is not None else grouping.fallback,
                   field=field, field_role=None, fallback=None)


def resolve_field_role_view(view: ViewInput, project: Mapping[str, Any]
                            ) -> tuple[ViewInput, tuple[UnboundFieldRole, ...]]:
    """Bind availability once; item field values still use their own Project map.

    This never changes an authored resource or its identity. Only new role
    references are normalized; existing direct-field inputs retain their View.
    """
    bindings = FieldRoleBindings.from_project(project)
    missing: dict[str, list[str]] = defaultdict(list)

    def unavailable(role: str | None, path: str) -> bool:
        if role is None or bindings.field_for(role) is not None:
            return False
        missing[role].append(path)
        return True

    grouping = view.grouping
    if grouping is not None:
        if not (grouping.field_role is not None and bindings.field_for(grouping.field_role) is None
                and grouping.fallback == "hierarchy"):
            unavailable(grouping.field_role, "/body/grouping/by/fieldRole")
    grouping = resolve_role_grouping(grouping, bindings)

    def columns(values: tuple[_Column, ...], prefix: str) -> tuple[_Column, ...]:
        return tuple(column for index, column in enumerate(values)
                     if not (isinstance(column.source, Mapping)
                             and unavailable(column.source.get("fieldRole"),
                                             f"{prefix}/{index}/source/fieldRole")))

    table_columns = columns(view.table_columns, "/body/tableColumns")
    if view.rows.mode != "lanes" and view.table_columns and not table_columns:
        raise ContractError("E_VIEW_TABLE_COLUMNS_EMPTY", "no table columns remain after unbound field roles are omitted",
                            "/body/tableColumns")
    if view.hierarchy_column is not None and view.hierarchy_column not in {column.id for column in table_columns}:
        raise ContractError("E_VIEW_HIERARCHY_COLUMN_UNKNOWN",
                            f"hierarchyColumn {view.hierarchy_column!r} names an omitted field-role column",
                            "/body/hierarchyColumn")
    rows = view.rows
    if rows.lane_table is not None:
        rows = replace(rows, lane_table=replace(rows.lane_table,
            columns=columns(rows.lane_table.columns, "/body/rows/laneTable/columns")))
    if rows.lane_keys is not None and unavailable(rows.lane_keys.field_role, "/body/rows/laneKeys/fieldRole"):
        keys = replace(rows.lane_keys, field_role=None)
        rows = replace(rows, lane_keys=keys if keys.field is not None or keys.by_object is not None else None)

    color = view.color_encoding
    if color is not None and "fieldRole" in color["source"]:
        role = color["source"]["fieldRole"]
        color = (None if unavailable(role, "/body/colorEncoding/source/fieldRole") else
                 freeze({**color, "source": {"field": bindings.field_for(role)}}))
    visuals = []
    for index, visual in enumerate(view.visuals):
        encoding = visual.encoding
        if encoding is not None and "fieldRole" in encoding:
            role = encoding["fieldRole"]
            if unavailable(role, f"/body/visuals/{index}/encoding/fieldRole"):
                continue
            encoding = freeze({**{key: value for key, value in encoding.items() if key != "fieldRole"},
                               "field": bindings.field_for(role)})
            visual = replace(visual, encoding=encoding)
        visuals.append(visual)
    resolved = replace(view, grouping=grouping, table_columns=table_columns, rows=rows,
                       color_encoding=color, visuals=tuple(visuals))
    info = tuple(UnboundFieldRole(role, tuple(paths)) for role, paths in missing.items())
    return (view if resolved == view else resolved), info
