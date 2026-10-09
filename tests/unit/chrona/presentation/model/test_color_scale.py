import pytest

from chrona.presentation.model.color_scale import ColorScaleError, resolve_color_scale


def _scale():
    return resolve_color_scale(
        {"scale": "owner", "target": "planned", "source": {"field": "owner"}, "domain": ["bus", "payload"]},
        {"owner": {"slots": {"bus": "bus", "payload": "payload"}}},
        {"bus": "#112233", "payload": "#445566"},
    )


def test_scale_resolves_explicit_value_to_named_slot():
    assert _scale().color_for("bus-task", {"owner": "bus"}) == "#112233"


def test_scale_rejects_unknown_or_missing_selected_value():
    with pytest.raises(ColorScaleError, match="E_PRESENTATION_SCALE_VALUE:task:owner"):
        _scale().color_for("task", {"owner": "other"})
    with pytest.raises(ColorScaleError, match="E_PRESENTATION_SCALE_VALUE:task:owner"):
        _scale().color_for("task", {})


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
    (lambda: _resolve(scales={"owner": {"slots": {"bus": "bus"}}}, categories={"bus": 17}),
     ("Scheme category 'bus'", "color=17", "string color")),
])
def test_scale_mapping_errors_name_the_invalid_operand_and_expected_form(call, needles):
    _mapping_error(call, *needles)
