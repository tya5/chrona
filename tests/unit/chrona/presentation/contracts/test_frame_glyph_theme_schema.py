"""#888 frame-glyph bindings are an additive optional Theme v0.15 contract."""
from __future__ import annotations

from chrona.presentation.contracts import ClosureIdentity, parse_contract
from chrona.presentation.contracts.resources import SchemaContractError


def _theme():
    return {
        "version": "chrona/theme/v0.15", "kind": "theme", "id": "frame-glyph-schema",
        "body": {
            "values": {
                "glyph-size": {"type": "number", "value": 8},
                "glyph-pitch": {"type": "number", "value": 12},
                "glyph-symbol": {"type": "symbol", "value": {"shape": {"catalog": "fixture:frame"}}},
                "glyph-fidelity": {"type": "fidelity", "value": "decorative-optional"},
            },
            "roles": {"frame-glyph": {
                "symbol": "glyph-symbol", "glyphSize": "glyph-size", "glyphPitch": "glyph-pitch",
                "artworkFidelity": "glyph-fidelity",
            }},
            "colorBindings": {"frame-glyph.fill": "accent"},
        },
    }


def test_frame_glyph_named_number_bindings_are_admitted_in_live_theme_schema():
    value = _theme()

    contract = parse_contract(ClosureIdentity("theme", value["id"], "test", "sha256:" + "a" * 64), value)

    assert contract.theme_input["body"]["roles"]["frame-glyph"] == value["body"]["roles"]["frame-glyph"]


def test_frame_glyph_size_and_pitch_bindings_remain_named_token_references():
    value = _theme()
    value["body"]["roles"]["frame-glyph"]["glyphSize"] = 8

    try:
        parse_contract(ClosureIdentity("theme", value["id"], "test", "sha256:" + "b" * 64), value)
    except SchemaContractError as error:
        assert error.violation is not None
        assert error.violation.pointer.startswith("/body/roles/frame-glyph/glyphSize")
    else:
        raise AssertionError("literal glyphSize must not replace its named number-token binding")
