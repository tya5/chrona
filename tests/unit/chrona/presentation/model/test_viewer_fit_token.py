"""#1050: the `viewerFit` / `viewerFitAdjust` role reader and its rejected combinations (the Theme schema also
rejects an unknown value or an adjust without `text-follows-box`; the container conflicts live in named tokens, which
only the reader can resolve)."""
from __future__ import annotations

import pytest

from chrona.presentation.layout.annotation_border import NO_BORDER  # noqa: F401  (the border reader is the neighbour)
from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView, ViewerFitToken
from tests.unit.chrona.presentation.model.test_theme_tokens import _theme, _theme_with_annotation_container

PLAIN = {"outline": "rectangle", "cornerRadius": 0}
INSET = {"top": 0.5, "right": 1, "bottom": 0.5, "left": 1}
ARTWORK = {"glyph": "set:frame", "sliceInsets": {"top": 1, "right": 1, "bottom": 1, "left": 1}, "unitEm": 1}


def _view(container=None, **role):
    theme = _theme_with_annotation_container(container if container is not None else PLAIN)
    theme["body"]["roles"]["annotation"].update(role)
    return ThemeTokenView(theme)


def test_absence_is_raw_and_the_default_adjust_is_spacing():
    assert ThemeTokenView(_theme()).viewer_fit("annotation") == ViewerFitToken("raw", "spacing")
    assert _view().viewer_fit("annotation") == ViewerFitToken("raw", "spacing")
    assert _view(viewerFit="raw").viewer_fit("annotation") == ViewerFitToken("raw", "spacing")
    assert _view(viewerFit="text-follows-box").viewer_fit("annotation") == ViewerFitToken("text-follows-box", "spacing")


def test_the_adjust_is_read_with_text_follows_box():
    token = _view(viewerFit="text-follows-box", viewerFitAdjust="spacingAndGlyphs").viewer_fit("annotation")
    assert token == ViewerFitToken("text-follows-box", "spacingAndGlyphs")


@pytest.mark.parametrize("role,pointer", [
    ({"viewerFit": "justify"}, "/body/roles/annotation/viewerFit"),
    ({"viewerFit": True}, "/body/roles/annotation/viewerFit"),
    ({"viewerFit": "text-follows-box", "viewerFitAdjust": "stretch"}, "/body/roles/annotation/viewerFitAdjust"),
    ({"viewerFitAdjust": "spacing"}, "/body/roles/annotation/viewerFitAdjust"),
    ({"viewerFit": "raw", "viewerFitAdjust": "spacing"}, "/body/roles/annotation/viewerFitAdjust"),
    ({"viewerFit": "box-follows-text", "viewerFitAdjust": "spacing"}, "/body/roles/annotation/viewerFitAdjust"),
])
def test_an_unknown_value_or_an_adjust_without_text_follows_box_names_its_declaration(role, pointer):
    with pytest.raises(ThemeTokenError) as raised:
        _view(**role).viewer_fit("annotation")
    assert (raised.value.diagnostic_id, raised.value.path) == ("E_THEME_TOKEN_TYPE", pointer)


def test_box_follows_text_is_valid_for_a_plain_rectangle_with_or_without_a_container_or_insets():
    plain = {"viewerFit": "box-follows-text"}
    assert ThemeTokenView(_theme()).viewer_fit("annotation").mode == "raw"
    theme = _theme()
    theme["body"]["roles"]["annotation"] = dict(plain)  # no container at all: today's plain rectangle
    assert ThemeTokenView(theme).viewer_fit("annotation").mode == "box-follows-text"
    assert _view(**plain).viewer_fit("annotation").mode == "box-follows-text"
    assert _view(dict(PLAIN, contentInsetEm=INSET), **plain).viewer_fit("annotation").mode == "box-follows-text"
    # a start-side border is a separate static strip and is followable
    assert _view(dict(PLAIN, border={"start": {"width": 3}}), **plain).viewer_fit("annotation").mode == "box-follows-text"


@pytest.mark.parametrize("container,name", [
    ({"outline": "balloon", "cornerRadius": 0.2, "tailBaseEm": 0.6}, "outline"),
    ({"outline": "image", "image": "chrona:frame", "cornerRadius": 0,
      "sliceInsetsEm": INSET, "contentInsetEm": INSET}, "outline"),
    ({"outline": "rectangle", "cornerRadius": 0.2}, "cornerRadius"),
    ({"outline": "rectangle", "cornerRadius": 0, "tiltDegrees": [-1, 1]}, "tiltDegrees"),
    ({"outline": "rectangle", "cornerRadius": 0, "contentInsetEm": INSET, "artwork": ARTWORK}, "artwork"),
    ({"outline": "rectangle", "cornerRadius": 0, "inlineSize": "fill"}, "inlineSize"),
    ({"outline": "rectangle", "cornerRadius": 0, "border": {"end": {"width": 1}}}, "border/end"),
    ({"outline": "rectangle", "cornerRadius": 0, "border": {"top": {"width": 1}}}, "border/top"),
    ({"outline": "rectangle", "cornerRadius": 0, "border": {"bottom": {"width": 1}}}, "border/bottom"),
    ({"outline": "rectangle", "cornerRadius": 0, "border": {"start": {"width": 1}, "end": {"width": 2}}}, "border/end"),
])
def test_a_box_that_cannot_follow_its_text_is_refused_at_the_offending_declaration(container, name):
    with pytest.raises(ThemeTokenError) as raised:
        _view(container, viewerFit="box-follows-text").viewer_fit("annotation")
    assert raised.value.diagnostic_id == "E_THEME_TOKEN_TYPE"
    assert raised.value.path == f"/body/roles/annotation/annotationContainer/{name}"


@pytest.mark.parametrize("container", [
    {"outline": "balloon", "cornerRadius": 0.2, "tailBaseEm": 0.6},
    {"outline": "rectangle", "cornerRadius": 0.2},
    {"outline": "rectangle", "cornerRadius": 0, "tiltDegrees": [-1, 1]},
    {"outline": "rectangle", "cornerRadius": 0, "inlineSize": "fill"},
    {"outline": "rectangle", "cornerRadius": 0, "border": {"end": {"width": 1}}},
])
def test_text_follows_box_composes_with_every_container_the_other_mode_refuses(container):
    assert _view(container, viewerFit="text-follows-box").viewer_fit("annotation").mode == "text-follows-box"


@pytest.mark.parametrize("role", ["as-of-label-chip", "member-label-chip", "finish-delta-chip", "period-label-chip"])
def test_each_registered_chip_role_admits_a_square_solid_follower(role):
    theme = _theme()
    theme["body"]["roles"][role] = {"viewerFit": "box-follows-text", "fill": "chipFill"}
    theme["body"]["values"]["chipFill"] = {"type": "color", "value": "#ffffff"}
    assert ThemeTokenView(theme).viewer_fit(role).mode == "box-follows-text"


def test_physical_square_chip_radius_overrides_a_nonzero_legacy_radius():
    theme = _theme()
    theme["body"]["roles"]["member-label-chip"] = {
        "viewerFit": "box-follows-text", "fill": "chipFill", "cornerRadius": "square", "markCornerRadius": "rounded"}
    theme["body"]["values"].update({"chipFill": {"type": "color", "value": "#ffffff"},
                                      "square": {"type": "radius", "value": 0},
                                      "rounded": {"type": "number", "value": 0.2}})
    assert ThemeTokenView(theme).viewer_fit("member-label-chip").mode == "box-follows-text"
