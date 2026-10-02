"""#584 A584-3: the Theme `annotationContainer.tiltDegrees` declaration."""
from __future__ import annotations

from decimal import Decimal

import pytest

from chrona.presentation.color_scheme import resolve_theme
from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr

ROLE = "annotation-note-box"


def _tokens(degrees, **options):
    parts = sr.bundle()
    ak.with_tilt(parts, degrees, **options)
    resolved = resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    return ThemeTokenView(resolved)


def test_a_rectangle_container_may_declare_a_tilt_cycle():
    container = _tokens([4, -3.5, 0]).annotation_container(ROLE)
    assert container.outline == "rectangle"
    assert container.tilt_degrees == (Decimal("4"), Decimal("-3.5"), Decimal("0"))


def test_a_container_without_tilt_has_none():
    parts = sr.bundle()
    theme = parts["theme"]["body"]
    theme["values"]["plain-container"] = {"type": "annotationContainer", "value": {"outline": "rectangle", "cornerRadius": 0}}
    theme["roles"][ROLE]["annotationContainer"] = "plain-container"
    resolved = resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    assert ThemeTokenView(resolved).annotation_container(ROLE).tilt_degrees is None


@pytest.mark.parametrize("degrees", [15, -15, 0.01])
def test_the_bound_is_fifteen_degrees_inclusive(degrees):
    assert _tokens([degrees]).annotation_container(ROLE).tilt_degrees == (Decimal(str(degrees)),)


@pytest.mark.parametrize("degrees", [[], [15.01], [-16], [3, 40], ["4"], [None], [True], [float("inf")], "4", 4])
def test_an_invalid_cycle_is_a_token_type_error_at_the_property(degrees):
    with pytest.raises(ThemeTokenError) as failure:
        _tokens(degrees).annotation_container(ROLE)
    assert failure.value.diagnostic_id == "E_THEME_TOKEN_TYPE"
    assert failure.value.path.endswith("/annotationContainer/tiltDegrees")


def test_a_balloon_or_image_container_cannot_tilt():
    parts = sr.bundle()
    theme = parts["theme"]["body"]
    theme["values"]["balloon-container"] = {"type": "annotationContainer", "value": {
        "outline": "balloon", "cornerRadius": 0.2, "tailBaseEm": 0.6, "tiltDegrees": [3]}}
    theme["roles"][ROLE]["annotationContainer"] = "balloon-container"
    resolved = resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    with pytest.raises(ThemeTokenError) as failure:
        ThemeTokenView(resolved).annotation_container(ROLE)
    assert failure.value.diagnostic_id == "E_THEME_TOKEN_TYPE" and failure.value.path.endswith("/tiltDegrees")


def test_the_theme_schema_rejects_a_tilt_on_a_balloon_or_image_and_an_out_of_range_angle(tmp_path):
    source = ak.project()
    for index, value in enumerate((
            {"outline": "balloon", "cornerRadius": 0.2, "tailBaseEm": 0.6, "tiltDegrees": [3]},
            {"outline": "rectangle", "cornerRadius": 0, "tiltDegrees": [16]},
            {"outline": "rectangle", "cornerRadius": 0, "tiltDegrees": []})):
        parts = sr.bundle()
        ak.with_view_notes(parts, source)
        parts["theme"]["body"]["values"]["tilt-container"] = {"type": "annotationContainer", "value": value}
        parts["theme"]["body"]["roles"][ROLE]["annotationContainer"] = "tilt-container"
        directory = tmp_path / str(index)
        directory.mkdir()
        with pytest.raises(Exception) as failure:
            sr.render(directory, source, presentation=parts)
        assert "E_THEME_SCHEMA" in str(failure.value)
