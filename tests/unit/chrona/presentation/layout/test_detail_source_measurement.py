"""Detail measurement and native owners consume the same selected facts."""
from datetime import date
from decimal import Decimal

import pytest

from chrona.presentation.layout.sources import measure_sources
from chrona.presentation.layout.surface_content import detail_source_inputs
from chrona.presentation.model.theme_tokens import ThemeTokenView
from tests.unit.chrona.presentation.layout.test_sources import _table_metrics, theme
from tests.unit.chrona.presentation.scene.test_v05_builder import surface_content


def test_detail_source_inputs_use_actual_entries_not_synthetic_panel_names():
    content = surface_content(group_details=(("team", "Team", "Description"),),
        milestones=(("gate", "Gate", date(2026, 1, 2)),),
        observation_columns=(("value", "Value"),),
        observation_rows=(("reading", "Supplier report", "critical", (("value", "42"),)),))
    sources = detail_source_inputs(content)
    assert sources["group-details"].lines == ("Team: Description",)
    assert sources["milestones"].lines == ("Gate — 2026-01-02",)
    assert sources["observations"].lines == ("Supplier report",)
    assert sources["observations"].table.cells[0].semantic_id == "observationCriticalCell"
    assert sources["observations"].item_count == 1


def test_observations_measure_declared_columns_and_visible_provenance_row_height():
    content = surface_content(observation_columns=(("one", "First"), ("two", "Second")),
        observation_rows=(("reading", "Supplier", "normal", (("one", "A"), ("two", "B"))),))
    resolved = theme()
    sources = detail_source_inputs(content)
    measured = measure_sources(sources, resolved, font_metrics=_table_metrics())
    observation = measured.measurements["observations"]
    treatment = ThemeTokenView(resolved).text_treatment("text")
    assert observation.preferred_block == 3 * treatment.font_size * treatment.line_height
    assert 0 < observation.min_inline <= observation.preferred_inline
    assert observation.preferred_inline >= Decimal(8)  # declared table gutter contributes


def test_observations_intrinsic_width_includes_long_visible_source_attribution():
    source = "Supplier attribution " * 20
    content = surface_content(observation_columns=(("v", "V"),),
        observation_rows=(("r", source, "normal", (("v", "1"),)),))
    measured = measure_sources(detail_source_inputs(content), theme(), font_metrics=_table_metrics())
    assert float(measured.measurements["observations"].preferred_inline) == pytest.approx(
        _table_metrics().width(source, 14))


def test_empty_detail_inputs_contain_no_placeholder_copy():
    sources = detail_source_inputs(surface_content())
    assert all(not source.lines for source in sources.values())
    assert not sources["observations"].table.columns and not sources["observations"].table.cells
