from chrona.presentation.model.semantic_registry import (
    ContrastClass,
    contrast_binding,
    contrast_bindings,
    semantic_binding,
)
from chrona.presentation.scene.capabilities import theme_role_contract, theme_role_property_consumer


def test_row_rule_is_a_decoration_path_with_only_stroke_paint():
    binding = semantic_binding("rowRule")
    assert (binding.primitive_kind, binding.purpose, binding.scene_role, binding.theme_role) == (
        "decoration", "row-rule", "row-rule", "row-rule")
    assert binding.contrast_class is ContrastClass.DECORATION
    assert contrast_binding("row-rule") == binding
    assert binding in contrast_bindings(ContrastClass.DECORATION)

    contract = theme_role_contract("row-rule")
    assert contract is not None
    assert contract.scene_kinds == frozenset(("Path",))
    assert contract.properties == frozenset(("stroke", "strokeWidth", "opacity"))
    assert all(theme_role_property_consumer("row-rule", name) == contract.consumer
               for name in contract.properties)
    assert all(theme_role_property_consumer("row-rule", name) is None
               for name in ("fill", "dash", "gradientStart", "backgroundTreatment"))
