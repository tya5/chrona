from datetime import date

from chrona.presentation.model.presentation_contract import normalize_presentation_input
from chrona.presentation.model.semantic_registry import enabled_semantics, semantic_binding
from chrona.presentation.model.surface_content import SurfaceContentInput


def test_normalizer_consumes_member_label_alias_once() -> None:
    contract = normalize_presentation_input(SurfaceContentInput(show_member_labels=True))

    assert contract.labels.enabled is True
    assert contract.labels.placement == "none"
    assert contract.labels.content == ("title",)


def test_normalizer_retains_canonical_time_fact() -> None:
    as_of = date(2027, 8, 20)
    contract = normalize_presentation_input(SurfaceContentInput(as_of=as_of))

    assert contract.time.as_of == as_of


def test_registry_declares_stable_as_of_scene_role() -> None:
    binding = semantic_binding("asOf")

    assert binding.scene_role == "as-of"
    assert binding.theme_role == "asOf"


def test_enabled_semantics_are_registry_derived() -> None:
    bindings = enabled_semantics(
        has_as_of=True,
        has_group_headers=False,
        has_calendar_closure=False,
        has_axis_bands=False,
        has_legend=False,
        has_annotations=False,
    )

    assert [binding.semantic_id for binding in bindings] == ["planned", "actual", "asOf"]
