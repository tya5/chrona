from chrona.presentation.model.surface_content import display_value


def test_declared_table_missing_values_are_normalized_before_scene_construction():
    assert display_value(None, "blank") == ""
    assert display_value(None, "em-dash") == "—"
    assert display_value(None, "unknown") == "unknown"


def test_declared_table_value_is_not_replaced_by_a_missing_policy():
    assert display_value("ready", "blank") == "ready"
    assert display_value(4, "em-dash") == "+4d"
