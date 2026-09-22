from datetime import date

from chrona.presentation.model.presentation_contract import normalize_presentation_input
from chrona.presentation.model.semantic_registry import enabled_semantics, semantic_binding
from chrona.presentation.model.surface_content import SummaryContent, SurfaceContentInput


def surface_content(**overrides):
    value = dict(table_columns=(), table_cells=(), relations=(), annotations=(), show_member_labels=False,
                 label_placement="none", label_content=(), label_side="auto", label_overflow="diagnose",
                 relation_overflow="diagnose", group_presentation="band", axis_level="auto", axis_levels=(),
                 axis_ticks=None, as_of=None, as_of_label="As of", annotation_numbered=False,
                 calendar_closed=(), notes=(), legend_entries=(), coverage_text="", summary=SummaryContent(()),
                 template_values=(), group_details=(), milestones=(),
                 observation_columns=(), observation_rows=())
    value.update(overrides)
    return SurfaceContentInput(**value)


def test_normalizer_consumes_member_label_alias_once() -> None:
    contract = normalize_presentation_input(surface_content(show_member_labels=True))

    assert contract.labels.enabled is True
    assert contract.labels.placement == "none"
    assert contract.labels.content == ("title",)


def test_normalizer_retains_canonical_time_fact() -> None:
    as_of = date(2027, 8, 20)
    contract = normalize_presentation_input(surface_content(as_of=as_of))

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
