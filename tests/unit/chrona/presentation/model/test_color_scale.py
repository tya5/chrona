import pytest

from chrona.presentation.model.color_scale import ColorScaleError, resolve_color_scale
from chrona.presentation.color_scheme import ColorSchemeError, resolve_color_scheme


def _scale():
    return resolve_color_scale(
        {"scale": "owner", "target": "planned", "source": {"field": "owner"}, "domain": ["bus", "payload"]},
        {"owner": {"slots": {"bus": "bus", "payload": "payload"}}},
        {"bus": "#112233", "payload": "#445566"},
    )


def test_scale_resolves_explicit_value_to_named_slot():
    assert _scale().color_for("bus-task", {"owner": "bus"}) == "#112233"


def test_scale_rejects_unknown_or_missing_selected_value():
    for fields, operand in (({"owner": "other"}, "value='other'"), ({}, "value=None")):
        with pytest.raises(ColorScaleError) as caught:
            _scale().color_for("task", fields)
        error = caught.value
        assert error.code == "E_PRESENTATION_SCALE_VALUE"
        assert error.source_ref == "/body/colorEncoding"
        assert "object='task'" in error.detail and "field='owner'" in error.detail
        assert operand in error.detail


def test_scale_requires_an_exact_mapping_and_existing_slot():
    with pytest.raises(ColorScaleError, match="E_PRESENTATION_SCALE_MAPPING"):
        resolve_color_scale(
            {"scale": "owner", "target": "planned", "source": {"field": "owner"}, "domain": ["bus"]},
            {"owner": {"slots": {"payload": "payload"}}}, {"payload": "#445566"},
        )


def _resolve(encoding=None, scales=None, categories=None):
    return resolve_color_scale(
        {"scale": "owner", "target": "planned", "source": {"field": "owner"}, "domain": ["bus"]}
        if encoding is None else encoding,
        {"owner": {"slots": {"bus": "bus"}}} if scales is None else scales,
        {"bus": "#112233"} if categories is None else categories,
    )


def _mapping_error(call, *needles):
    with pytest.raises(ColorScaleError) as caught:
        call()
    message = str(caught.value)
    assert message.startswith("E_PRESENTATION_SCALE_MAPPING: "), message
    for needle in needles:
        assert needle in message, message


@pytest.mark.parametrize("call,needles", [
    (lambda: _resolve(encoding=[]), ("encoding=list of length 0", "expected a mapping")),
    (lambda: _resolve(encoding={"scale": [], "target": "planned", "source": {"field": "owner"}, "domain": ["bus"]}),
     ("encoding.scale=list of length 0", "string scale id")),
    (lambda: _resolve(encoding={"scale": "owner", "target": 7, "source": {"field": "owner"}, "domain": ["bus"]}),
     ("encoding.target=7", "target role")),
    (lambda: _resolve(encoding={"scale": "owner", "target": "planned", "source": "owner", "domain": ["bus"]}),
     ("encoding.source='owner'", "string field")),
    (lambda: _resolve(encoding={"scale": "owner", "target": "planned", "source": {}, "domain": ["bus"]}),
     ("encoding.source.field=None", "field name")),
    (lambda: _resolve(encoding={"scale": "owner", "target": "planned", "source": {"field": "owner"}, "domain": []}),
     ("encoding.domain=list of length 0", "nonempty sequence")),
    (lambda: _resolve(encoding={"scale": "owner", "target": "planned", "source": {"field": "owner"}, "domain": [7]}),
     ("encoding.domain[0]=7", "must be a string")),
    (lambda: _resolve(encoding={"scale": "owner", "target": "planned", "source": {"field": "owner"}, "domain": ["bus", "bus"]}),
     ("encoding.domain[1]='bus'", "duplicates")),
    (lambda: _resolve(scales={}), ("Theme scale 'owner'", "slots=None", "nonempty palette")),
    (lambda: _resolve(scales={"owner": {"slots": {"other": "bus"}}}),
     ("does not exactly cover", "missing keys=[\"'bus'\"]", "extra keys=[\"'other'\"]")),
    (lambda: _resolve(scales={"owner": {"slots": {"bus": "absent"}}}),
     ("domain value 'bus'", "missing Scheme category 'absent'")),
    (lambda: _resolve(scales={"owner": {"slots": {"bus": 3}}}),
     ("domain value 'bus'", "slot=3", "string Scheme category")),
])
def test_scale_mapping_errors_name_the_invalid_operand_and_expected_form(call, needles):
    _mapping_error(call, *needles)


def test_theme_slot_failures_use_escaped_theme_pointer_and_keep_both_key_sets():
    with pytest.raises(ColorScaleError) as caught:
        resolve_color_scale(
            {"scale": "ignored", "target": "planned", "source": {"field": "owner"}, "domain": ["bus"]},
            {"ignored": {"slots": {"other": "bus"}}}, {"bus": "#112233"},
        )
    error = caught.value
    assert error.code == "E_PRESENTATION_SCALE_MAPPING"
    assert error.source_ref == "/body/colorScales/ignored/slots"
    assert "missing keys=[\"'bus'\"]" in error.detail
    assert "extra keys=[\"'other'\"]" in error.detail


def test_theme_scale_identifier_is_rfc6901_escaped():
    with pytest.raises(ColorScaleError) as caught:
        resolve_color_scale(
            {"scale": "a/b~c", "target": "planned", "source": {"field": "owner"}, "domain": ["bus"]},
            {}, {"bus": "#112233"},
        )
    assert caught.value.source_ref == "/body/colorScales/a~1b~0c/slots"


def test_scheme_category_shape_error_keeps_scheme_owned_code_and_pointer():
    with pytest.raises(ColorScaleError) as caught:
        resolve_color_scale(
            {"scale": "owner", "target": "planned", "source": {"field": "owner"}, "domain": ["bus"]},
            {"owner": {"slots": {"bus": "bad/category"}}}, {"bad/category": 17},
        )
    assert caught.value.code == "E_PRESENTATION_SCALE_MAPPING"
    assert caught.value.source_ref == "/body/categories/bad~1category"


def test_color_scheme_ingress_keeps_its_existing_schema_code_and_pointer():
    from tests.support import synthetic_review as sr

    scheme = sr.bundle("control-room-dark")["scheme"]
    scheme["body"]["categories"]["series-1"] = 17
    with pytest.raises(ColorSchemeError) as caught:
        resolve_color_scheme(scheme, content_identity="synthetic-scheme")
    assert caught.value.diagnostic_id == "E_SCHEME_SCHEMA"
    assert caught.value.source_ref == "/body/categories"


def test_encoding_pointer_is_runtime_provenance_not_scale_identity():
    default = _scale()
    same_default = resolve_color_scale(
        {"scale": "owner", "target": "planned", "source": {"field": "owner"}, "domain": ["bus", "payload"]},
        {"owner": {"slots": {"bus": "bus", "payload": "payload"}}},
        {"bus": "#112233", "payload": "#445566"}, source_ref="/body/grouping/tint",
    )
    assert default == same_default
    assert "encoding_source_ref" not in repr(default)
    grouped = resolve_color_scale(
        {"scale": "owner", "target": "planned", "source": {"field": "owner"}, "domain": ["bus"]},
        {"owner": {"slots": {"bus": "bus"}}}, {"bus": "#112233"},
        source_ref="/body/grouping/tint",
    )
    with pytest.raises(ColorScaleError) as caught:
        grouped.color_for("group-a", {"owner": "other"})
    assert caught.value.code == "E_PRESENTATION_SCALE_VALUE"
    assert caught.value.source_ref == "/body/grouping/tint"
