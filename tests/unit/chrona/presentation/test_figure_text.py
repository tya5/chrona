from __future__ import annotations

import pytest

from chrona.presentation.figure_text import FigureTextError, figure_ids, resolve_figure_text


def test_literal_without_marker_is_preserved_byte_for_byte():
    source = "  ordinary {braces} and unmatched { text  "
    assert figure_ids(source) == frozenset()
    assert resolve_figure_text(source, {}) == source


def test_escaped_figure_notation_is_literal():
    source = "{{figure:shown}}"
    assert figure_ids(source) == frozenset()
    assert resolve_figure_text(source, {}) == "{figure:shown}"


def test_resolves_signed_zero_and_repeated_references():
    source = "{figure:up} / {figure:down} / {figure:zero} / {figure:up}"
    figures = {"up": 12, "down": -4, "zero": 0}
    assert figure_ids(source) == frozenset(figures)
    assert resolve_figure_text(source, figures) == "12 / -4 / 0 / 12"


def test_multiple_references_and_escaped_braces_compose():
    assert resolve_figure_text("{{{figure:n}}} days", {"n": 3}) == "{3} days"


@pytest.mark.parametrize("source", [
    "{figure:", "{figure:}", "{figure:x", "{figure:x}}", "{title} {figure:x}",
    "{figure:x} }",
])
def test_malformed_or_nonfigure_fields_are_rejected(source):
    with pytest.raises(FigureTextError) as failure:
        figure_ids(source)
    assert failure.value.code == "E_VIEW_FIGURE_TEMPLATE"


def test_unknown_reference_names_id_and_known_figures():
    with pytest.raises(FigureTextError) as failure:
        resolve_figure_text("{figure:missing}", {"known": 4})
    assert failure.value.code == "E_VIEW_FIGURE_UNKNOWN"
    assert "missing" in failure.value.detail and "known" in failure.value.detail


def test_resolution_does_not_mutate_mapping():
    figures = {"f": -2}
    before = figures.copy()
    assert resolve_figure_text("Value {figure:f}", figures) == "Value -2"
    assert figures == before
