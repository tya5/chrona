"""Group tab geometry (#882): the declaration, the completed Rect, folded header rows and role admission."""
from __future__ import annotations

from decimal import Decimal

import pytest

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.surface_backgrounds import compose_group_tabs
from chrona.presentation.layout.surface_groups import (
    GroupHeaderExtentUpdate, GroupTabSpec, check_group_tab_inline, group_tab_bounds, replace_group_header_extent,
    resolve_group_tab, group_tag_bounds,
)
from chrona.presentation.layout.surface_quality import GroupPlacement
from chrona.presentation.model.theme_tokens import ThemeTokenError
from chrona.presentation.scene.capabilities import theme_catalog_pattern_consumer, theme_role_property_consumer

HEADER = Rect(Decimal(36), Decimal(100), Decimal(400), Decimal(20))


class _Tokens:
    """The four Theme reads the declaration uses, over one role binding."""

    def __init__(self, role: dict | None, *, mode: str = "horizontal", **numbers: float) -> None:
        self.role, self.numbers = role, {name: Decimal(str(value)) for name, value in numbers.items()}
        self.mode = mode

    def writing_mode(self, role: str):
        assert role == "groupHeader"
        return self.mode

    def optional_background(self, role: str):
        assert role == "group-tab"
        if self.role is None or not {"backgroundTreatment", "backgroundPaintOrder"} & set(self.role):
            return None
        return self.role["backgroundTreatment"], self.role["backgroundPaintOrder"]

    def background(self, role: str):
        return self.optional_background(role)

    def optional_number(self, role: str, name: str):
        return self.numbers.get(name)

    def optional_choice(self, role: str, name: str, allowed):
        value = (self.role or {}).get(name)
        if value is not None and value not in allowed:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/{name}")
        return value


def _tokens(position=None, treatment="fill", **numbers) -> _Tokens:
    role = {"backgroundTreatment": treatment, "backgroundPaintOrder": 20}
    if position:
        role["tabPosition"] = position
    return _Tokens(role, **numbers)


# --- the declaration ---------------------------------------------------------------------------------------


def test_no_role_and_a_role_that_names_neither_treatment_nor_order_declare_no_tab():
    assert resolve_group_tab(_Tokens(None)) is None
    assert resolve_group_tab(_Tokens({"tabInlineSize": "x"}, tabInlineSize=40)) is None


def test_a_role_with_treatment_none_declares_no_tab_even_with_sizes():
    assert resolve_group_tab(_tokens(treatment="none", tabInlineSize=40)) is None


def test_the_defaults_are_a_start_tab_with_no_gap_and_the_header_block_size():
    spec = resolve_group_tab(_tokens(tabInlineSize=40))

    assert spec == GroupTabSpec(Decimal(40), None, Decimal(0), "start")
    assert spec.reserved == 40


def test_every_property_is_read():
    spec = resolve_group_tab(_tokens("end", tabInlineSize=40, tabBlockSize=12, tabGap=6))

    assert spec == GroupTabSpec(Decimal(40), Decimal(12), Decimal(6), "end")
    assert spec.reserved == 46


@pytest.mark.parametrize("numbers, prop", [
    ({}, "tabInlineSize"), ({"tabInlineSize": 0}, "tabInlineSize"), ({"tabInlineSize": -1}, "tabInlineSize"),
    ({"tabInlineSize": 40, "tabBlockSize": 0}, "tabBlockSize"), ({"tabInlineSize": 40, "tabBlockSize": -2}, "tabBlockSize"),
    ({"tabInlineSize": 40, "tabGap": -0.5}, "tabGap"),
])
def test_an_undrawable_declaration_names_the_role_and_property(numbers, prop):
    with pytest.raises(LayoutError) as caught:
        resolve_group_tab(_tokens(**numbers))

    assert caught.value.diagnostic_id == "E_LAYOUT_GROUP_TAB_SIZE"
    assert caught.value.path == f"/body/roles/group-tab/{prop}"
    assert caught.value.detail.startswith(f"group-tab:{prop}:")


def test_a_position_other_than_start_or_end_is_a_theme_token_error():
    with pytest.raises(ThemeTokenError):
        resolve_group_tab(_tokens("middle", tabInlineSize=40))


def test_a_zero_gap_is_allowed():
    assert resolve_group_tab(_tokens(tabInlineSize=40, tabGap=0)).gap == 0


# --- the completed Rect ------------------------------------------------------------------------------------


def test_a_start_tab_stands_on_the_header_inline_start_with_the_header_block_size():
    assert group_tab_bounds(GroupTabSpec(Decimal(40), None, Decimal(6), "start"), HEADER) == Rect(
        Decimal(36), Decimal(100), Decimal(40), Decimal(20))


def test_an_end_tab_stands_on_the_header_inline_end():
    assert group_tab_bounds(GroupTabSpec(Decimal(40), None, Decimal(6), "end"), HEADER) == Rect(
        Decimal(396), Decimal(100), Decimal(40), Decimal(20))


def test_an_explicit_block_size_keeps_the_block_start():
    assert group_tab_bounds(GroupTabSpec(Decimal(40), Decimal(12), Decimal(0), "start"), HEADER).block_size == 12


def test_a_block_size_equal_to_the_header_is_allowed_and_a_larger_one_is_not():
    assert group_tab_bounds(GroupTabSpec(Decimal(40), Decimal(20), Decimal(0), "start"), HEADER).block_size == 20
    with pytest.raises(LayoutError) as caught:
        group_tab_bounds(GroupTabSpec(Decimal(40), Decimal("20.01"), Decimal(0), "start"), HEADER)
    assert caught.value.path == "/body/roles/group-tab/tabBlockSize"


def test_tab_plus_gap_must_be_smaller_than_the_header_inline_size():
    check_group_tab_inline(GroupTabSpec(Decimal(390), None, Decimal(9), "start"), HEADER)  # 399 < 400
    for reserved in (Decimal(400), Decimal(401)):
        with pytest.raises(LayoutError) as caught:
            check_group_tab_inline(GroupTabSpec(reserved - 6, None, Decimal(6), "end"), HEADER)
        assert caught.value.path == "/body/roles/group-tab/tabInlineSize"
        assert caught.value.detail == f"group-tab:tabInlineSize:{reserved}:400"


# --- folded header rows ------------------------------------------------------------------------------------


def _groups() -> tuple[GroupPlacement, GroupPlacement]:
    return (GroupPlacement("a", Rect(Decimal(36), Decimal(100), Decimal(400), Decimal(80)), HEADER),
            GroupPlacement("b", Rect(Decimal(36), Decimal(200), Decimal(400), Decimal(80)),
                           Rect(Decimal(36), Decimal(200), Decimal(400), Decimal(20))))


def test_one_tab_per_header_in_group_order_with_the_role_paint_order_and_no_tab_without_a_header():
    groups = _groups() + (GroupPlacement("c", Rect(Decimal(36), Decimal(300), Decimal(400), Decimal(80)), None),)

    shapes = compose_group_tabs(groups=groups, theme_tokens=_tokens(tabInlineSize=40))

    assert [(item.placement_id, item.source_ref, item.semantic_id, item.kind, item.paint_order) for item in shapes] == [
        ("group-tab:a", "a", "groupTab", "Rect", 20), ("group-tab:b", "b", "groupTab", "Rect", 20)]
    # The header spans table and timeline, so the tab belongs to the combined review-surface slot, as a `both` band does.
    assert {item.slot_id for item in shapes} == {"review-surface"}


def test_the_theme_without_the_role_composes_no_tab():
    assert compose_group_tabs(groups=_groups(), theme_tokens=_Tokens(None)) == ()


def test_a_header_enlarged_by_folded_marks_gives_the_default_tab_its_final_block_size():
    groups = _groups()
    enlarged = Rect(HEADER.inline, HEADER.block, HEADER.inline_size, Decimal(54))
    groups = replace_group_header_extent(groups, GroupHeaderExtentUpdate(groups[0], enlarged))

    shapes = {item.source_ref: item for item in compose_group_tabs(groups=groups, theme_tokens=_tokens(tabInlineSize=40))}

    assert (shapes["a"].bounds.block_size, shapes["b"].bounds.block_size) == (54, 20)


def test_an_explicit_block_size_is_checked_against_the_final_extent_of_the_header():
    groups = _groups()
    enlarged = Rect(HEADER.inline, HEADER.block, HEADER.inline_size, Decimal(54))
    enlarged_groups = replace_group_header_extent(groups, GroupHeaderExtentUpdate(groups[0], enlarged))
    tokens = _tokens(tabInlineSize=40, tabBlockSize=30)

    with pytest.raises(LayoutError):  # 30 is above group b's 20
        compose_group_tabs(groups=enlarged_groups, theme_tokens=tokens)
    only_a = enlarged_groups[:1]
    assert compose_group_tabs(groups=only_a, theme_tokens=tokens)[0].bounds.block_size == 30


# --- role admission ----------------------------------------------------------------------------------------


@pytest.mark.parametrize("prop", ["tabInlineSize", "tabBlockSize", "tabGap", "tabPosition", "pattern", "fill", "stroke",
                                  "opacity", "backgroundTreatment", "backgroundPaintOrder"])
def test_the_role_admits_its_properties(prop):
    assert theme_role_property_consumer("group-tab", prop) is not None


@pytest.mark.parametrize("role", ["group-band", "group-header-band", "period-band", "row-band", "axis-band-decoration"])
@pytest.mark.parametrize("prop", ["tabInlineSize", "tabBlockSize", "tabGap", "tabPosition"])
def test_no_other_role_admits_a_tab_property(role, prop):
    assert theme_role_property_consumer(role, prop) is None


def test_the_group_roles_that_are_always_one_rect_admit_a_catalogue_pattern():
    # #1282: the group band, the group-header band and the row band join the tab; the calendar bands do not.
    for role in ("group-tab", "group-band", "group-header-band", "row-band"):
        assert theme_catalog_pattern_consumer(role, "pattern") is not None, role
        assert theme_role_property_consumer(role, "pattern") is not None, role
    for role in ("calendar-closed", "calendar-exception"):
        assert theme_catalog_pattern_consumer(role, "pattern") is None, role


def _tag_tokens(**numbers):
    return _Tokens({"tabTarget": "tag", "backgroundTreatment": "fill", "backgroundPaintOrder": 20},
                   mode="vertical", **numbers)


def test_tag_cell_is_shared_gap_inset_of_allocated_column_and_group_rows():
    tab = resolve_group_tab(_tag_tokens(tabGap=3))
    assert tab.target == "tag"
    assert group_tag_bounds(tab, (36, 22), HEADER) == Rect(Decimal(39), Decimal(103), Decimal(16), Decimal(14))


@pytest.mark.parametrize("column, rows", [((36, 6), HEADER), ((36, 22), Rect(Decimal(0), Decimal(0), Decimal(20), Decimal(6)))])
def test_nonpositive_tag_cell_reports_the_gap(column, rows):
    with pytest.raises(LayoutError) as caught:
        group_tag_bounds(resolve_group_tab(_tag_tokens(tabGap=3)), column, rows)
    assert caught.value.diagnostic_id == "E_LAYOUT_GROUP_TAB_SIZE"
    assert caught.value.path == "/body/roles/group-tab/tabGap"


def test_tag_without_a_displayed_column_or_groups_emits_no_plate():
    assert compose_group_tabs(groups=(), theme_tokens=_tag_tokens(), tag_column=(36, 16)) == ()
    assert compose_group_tabs(groups=(), theme_tokens=_tag_tokens(), tag_column=None) == ()


def test_negative_tag_gap_remains_a_layout_size_error():
    with pytest.raises(LayoutError) as caught:
        resolve_group_tab(_tag_tokens(tabGap=-1))
    assert caught.value.diagnostic_id == "E_LAYOUT_GROUP_TAB_SIZE"
    assert theme_catalog_pattern_consumer("calendar-closed", "pattern") is None  # the calendar bands stay off the list
