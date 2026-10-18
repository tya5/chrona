"""#1682: a profile field default is filled once, in the source-local accessor every occurrence reads through."""
from __future__ import annotations

from datetime import date

from chrona.presentation.model.field_roles import FieldDescriptor, FieldRoleBindings
from chrona.presentation.model.projection import FoldedPointProjection, build_review_projection
from chrona.presentation.model.style_rules import field_facts_for_item
from tests.unit.chrona.presentation.model.test_projection_field_descriptors import _view


def _bindings(default, *, has_default=True):
    return FieldRoleBindings.from_project(
        {"fieldRoles": {"risk": "risk"}},
        object_descriptors={"same-id": (FieldDescriptor("risk", "enum", "one", ("low", "medium", "high"), default, has_default),)})


def _project(fields):
    return {"objects": {"same-id": {"title": "T", "fields": fields}}, "entities": {}, "fieldRoles": {"risk": "risk"}}


def _fact(item, name="risk"):
    return next(fact for fact in field_facts_for_item(item) if fact.name == name)


def _projection(fields=None):
    fields = fields if fields is not None else {}
    placements = {"same-id": {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}}
    return build_review_projection(
        _project(fields), placements, _view(), None,
        snapshot_project=_project(fields), snapshot_placements=placements,
        scenarios={"variant": (_project(fields), placements)},
        field_bindings=_bindings("high"), snapshot_field_bindings=_bindings("low"),
        scenario_field_bindings={"variant": _bindings("medium")})


def test_each_source_occurrence_reads_its_own_pinned_default():
    items = {item.source_kind: item for item in _projection().rows[0].items}
    seen = {source: (_fact(item).present, _fact(item).value) for source, item in items.items()}
    assert seen == {"primary": (True, "high"), "snapshot": (True, "low"), "scenario": (True, "medium")}


def test_rows_items_and_folded_members_share_the_one_accessor():
    projection = _projection()
    in_rows = [item for row in projection.rows for item in row.items]
    folded = FoldedPointProjection(in_rows[0], "g", members=tuple(in_rows[1:]))
    every = [*projection.items, *in_rows, *folded.all_items]
    assert every and all(_fact(item).present and _fact(item).value for item in every)
    # the stored fields are untouched: no second fill path
    assert all("risk" not in (item.fields or {}) for item in every)


def test_absent_default_null_and_present_value_stay_distinct():
    bindings = _bindings("high")
    assert bindings.read_result({}, {"field": "risk"}, object_id="same-id").defaulted
    assert bindings.read_result({"risk": None}, {"field": "risk"}, object_id="same-id").value is None
    explicit = bindings.read_result({"risk": "low"}, {"field": "risk"}, object_id="same-id")
    assert (explicit.value, explicit.defaulted) == ("low", False)
    without = _bindings(None, has_default=False).read_result({}, {"field": "risk"}, object_id="same-id")
    assert (without.present, without.value, without.defaulted) == (False, None, False)
    # an object the declared profile does not type has no descriptor, so no default
    assert not bindings.read_result({}, {"field": "risk"}, object_id="other").present
