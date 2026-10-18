from dataclasses import replace
from datetime import date

import pytest

from chrona.presentation.contracts.resources import (
    ViewComparison, ViewGroupHeader, ViewGrouping, ViewInput, ViewRows,
    ViewVisibility, ViewWindow, _PrivateGroupingMode,
)
from chrona.presentation.model.hierarchy_names import close_member_names, member_name_key, plot_name_selected
from chrona.presentation.model.surface_content import table_value
from chrona.presentation.model.projection import (
    FoldedPointProjection, ReviewItem, ReviewLaneRowProjection, ReviewProjection,
    ReviewRowProjection,
)


def _view(by=_PrivateGroupingMode.PROJECT_ROOT_GROUP, *, content=("path",), header=None):
    return ViewInput(
        None, ViewGrouping(by, None, (), None, "header", None, None, header=header),
        None, ViewWindow("selected-planned", None, None, 0),
        ViewComparison(None, "optional", None, None, ()),
        ViewVisibility({"placement": "plot", "content": content}, "none", "none"),
        (), (), ViewRows("automatic", ()), None, (), None, None, None,
    )


def _item(**changes):
    item = ReviewItem(
        "task", "Provision", "point", {"at": date(2026, 1, 2)}, None, None, (),
        group_id="root", item_id="task", hierarchy_path=("root", "phase", "task"),
        hierarchy_titles=("Platform", "Infrastructure", "Provision"),
    )
    return replace(item, **changes)


def _projection(item):
    return ReviewProjection((item,), (date(2026, 1, 1), date(2026, 1, 3)), (), (),
                            rows=(ReviewRowProjection("row", "", "root", item.item_id, (item,)),))


@pytest.mark.parametrize("kind", ["primary", "combined", "actual"])
def test_root_header_covers_only_the_same_primary_ancestor(kind):
    item = _item(source_kind=kind)
    names = close_member_names(_projection(item), _view())
    assert names[member_name_key(item, "row")] == "Infrastructure / Provision"
    assert names[member_name_key(item)] == "Platform / Infrastructure / Provision"
    with pytest.raises(TypeError):
        names[member_name_key(item)] = "mutation"


@pytest.mark.parametrize("by", ["field", "objectType", "none"])
def test_coincident_group_or_entity_id_cannot_hide_a_containment_level(by):
    item = _item(group_label="Platform")
    names = close_member_names(_projection(item), _view(by))
    assert names[member_name_key(item, "row")] == "Platform / Infrastructure / Provision"


@pytest.mark.parametrize("kind", ["snapshot", "scenario"])
def test_primary_header_does_not_cover_a_different_source_with_the_same_ids(kind):
    item = _item(source_kind=kind, hierarchy_titles=("Other platform", "Old phase", "Provision"))
    names = close_member_names(_projection(item), _view())
    assert names[member_name_key(item, "row")] == "Other platform / Old phase / Provision"


@pytest.mark.parametrize("template", ["Overview", "{{title}}"])
def test_a_header_template_without_the_object_title_covers_nothing(template):
    item = _item()
    names = close_member_names(_projection(item), _view(header=ViewGroupHeader(template)))
    assert names[member_name_key(item, "row")] == "Platform / Infrastructure / Provision"


def test_hidden_header_and_legacy_title_name_do_not_select_relative_paths():
    item = _item()
    view = _view()
    hidden = replace(view, grouping=replace(view.grouping, presentation="band"))
    assert close_member_names(_projection(item), hidden)[member_name_key(item, "row")] == (
        "Platform / Infrastructure / Provision")
    assert not close_member_names(_projection(item), _view(content=("title", "finishDelta")))


def test_only_typed_enclosing_hierarchy_rows_cover_levels_not_an_unrelated_visible_row():
    item = _item()
    root = _item(object_id="root", item_id="root", title="Platform", hierarchy_path=("root",),
                 hierarchy_titles=("Platform",))
    projection = replace(_projection(item), hierarchy_grouping=True, rows=(
        ReviewRowProjection("parent", "", "", "root", (root,)),
        replace(_projection(item).rows[0], parent_row_id="parent"),
    ))
    assert close_member_names(projection, _view("hierarchy"))[member_name_key(item, "row")] == (
        "Infrastructure / Provision")
    projection = replace(projection, rows=(projection.rows[0], replace(projection.rows[1], parent_row_id=None)))
    assert close_member_names(projection, _view("hierarchy"))[member_name_key(item, "row")] == (
        "Platform / Infrastructure / Provision")


def test_lane_and_folded_names_share_the_same_identity_based_header_coverage():
    item = _item()
    projection = replace(_projection(item), rows=(), lane_rows=(
        ReviewLaneRowProjection("lane", "root", (item,), ("task",)),),
        folded_points=(FoldedPointProjection(item, "root"),))
    names = close_member_names(projection, _view())
    assert names[member_name_key(item, "lane")] == "Infrastructure / Provision"
    assert names[member_name_key(item, "root")] == "Infrastructure / Provision"


def test_path_includes_a_standalone_member_and_never_looks_up_an_unrelated_project():
    item = _item(hierarchy_path=(), hierarchy_titles=())
    assert table_value(item, {}, "path") == "Provision"
    assert table_value(replace(item, title=""), {}, "path") == "task"
    snapshot = _item(source_kind="snapshot", hierarchy_titles=("Other", "Old", "Provision"))
    unrelated = {"objects": {"root": {"title": "Wrong primary title"}}}
    assert table_value(snapshot, unrelated, "path") == "Other / Old / Provision"


@pytest.mark.parametrize("labels,expected", [
    (True, True), (False, False),
    ({"placement": "plot", "content": ["title"]}, True),
    ({"placement": "both", "content": ["path", "finishDelta"]}, True),
    ({"placement": "plot", "content": ["path"]}, True),
    ({"placement": "plot", "content": ["finishDelta"]}, False),
    ({"placement": "table", "content": ["path"]}, False),
    ({"placement": "none", "content": ["title"]}, False),
])
def test_folded_and_key_row_name_admission_is_independent_of_name_source(labels, expected):
    view = _view()
    view = replace(view, visibility=replace(view.visibility, labels=labels))
    assert plot_name_selected(view) is expected
