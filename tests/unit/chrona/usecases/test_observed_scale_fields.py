from datetime import date

from chrona.presentation.model.field_roles import FieldRoleBindings
from chrona.presentation.model.projection import ReviewItem, ReviewProjection
from chrona.usecases.render_review import _observed_scale_values


def _item(object_id, fields, bindings=FieldRoleBindings()):
    return ReviewItem(
        object_id, object_id, "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)},
        None, None, (), fields=fields, field_bindings=bindings,
    )


def _projection(*items):
    return ReviewProjection(tuple(items), (date(2026, 1, 1), date(2026, 1, 2)), (), ())


def test_direct_field_reads_keep_projection_order_and_preserve_zero_and_false():
    projection = _projection(
        _item("a", {"risk": 0}),
        _item("b", {"risk": False}),
        _item("c", {"risk": "high"}),
    )

    assert _observed_scale_values({"source": {"field": "risk"}}, projection) == (
        "0", "false", "high",
    )


def test_field_role_alias_is_resolved_against_each_items_source_bindings():
    primary = _item("same-object", {"primaryRisk": "low"},
                    FieldRoleBindings((("risk", "primaryRisk"),)))
    scenario = _item("same-object", {"scenarioRisk": "high"},
                     FieldRoleBindings((("risk", "scenarioRisk"),)))

    assert _observed_scale_values({"source": {"fieldRole": "risk"}},
                                  _projection(primary, scenario)) == ("low", "high")


def test_absent_and_explicit_null_fields_are_omitted_but_do_not_stop_later_values():
    projection = _projection(
        _item("missing", {}),
        _item("null", {"risk": None}),
        _item("present", {"risk": "medium"}),
    )

    assert _observed_scale_values({"source": {"field": "risk"}}, projection) == ("medium",)


def test_unmapped_role_or_nonfield_selector_has_no_observed_values():
    projection = _projection(_item("a", {"risk": "high"}))

    assert _observed_scale_values({"source": {"fieldRole": "unmapped"}}, projection) == ()
    assert _observed_scale_values({"source": {"facet": "finishDelta"}}, projection) == ()
    assert _observed_scale_values(None, projection) == ()
