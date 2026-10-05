"""Annotation artwork roles are consumed only by live container bindings (#1167)."""

from chrona.presentation.model.theme_role_consumers import unread_diagnostics, unread_roles
from chrona.presentation.scene.capabilities import theme_role_contract, theme_role_property_consumer


def _theme(*, roles, values):
    return {"roles": roles, "colorBindings": {}, "values": values}


def test_bound_annotation_artwork_layer_consumes_its_suffix_role():
    theme = _theme(
        roles={
            "annotation-note-box": {"annotationContainer": "scroll"},
            "annotation-artwork-rod-ink": {"fill": "accent"},
        },
        values={"scroll": {"type": "annotationContainer", "value": {
            "artwork": [{"glyph": "annotation-parts:scroll-rods", "role": "annotation-artwork-rod-ink"}],
        }}},
    )

    assert "annotation-artwork-rod-ink" not in unread_roles(theme, ())
    assert unread_diagnostics(theme, ()) == ()
    assert theme_role_contract("annotation-artwork-rod-ink") is not None


def test_role_in_an_unbound_container_token_is_still_unread():
    theme = _theme(
        roles={"annotation-artwork-unused": {"fill": "accent"}},
        values={"unused": {"type": "annotationContainer", "value": {
            "artwork": [{"glyph": "annotation-parts:scroll-rods", "role": "annotation-artwork-unused"}],
        }}},
    )

    assert unread_roles(theme, ()) == frozenset({"annotation-artwork-unused"})
    assert unread_diagnostics(theme, ()) == (
        "W_THEME_ROLE_UNREAD:/body/roles/annotation-artwork-unused",
    )


def test_malformed_artwork_suffix_does_not_join_the_capability_family():
    role = "annotation-artwork-1bad"
    theme = _theme(roles={role: {"annotationContainer": "unused"}}, values={})

    assert theme_role_contract(role) is None
    assert theme_role_property_consumer(role, "annotationContainer") is None
    assert unread_roles(theme, ()) == frozenset({role})


def test_legacy_single_artwork_object_keeps_the_base_role_behavior():
    theme = _theme(
        roles={
            "annotation-note-box": {"annotationContainer": "scroll"},
            "annotation-artwork": {"fill": "accent"},
        },
        values={"scroll": {"type": "annotationContainer", "value": {
            "artwork": {
                "glyph": "annotation-parts:scroll-mounting",
                "sliceInsets": {"top": 0.1, "right": 0.1, "bottom": 0.1, "left": 0.1},
                "unitEm": 1,
            },
        }}},
    )

    assert theme_role_contract("annotation-artwork") is not None
    assert unread_diagnostics(theme, ()) == ()
