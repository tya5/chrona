"""#1789: an object with no value for the encoded field keeps base paint; `missing:` may name a domain value."""
from __future__ import annotations

import pytest
import yaml

from chrona.usecases.draft_render import render_draft
from chrona.usecases.render_review import RenderFailed

from test_profile_default_and_encoding import COLOURS, _fills, _package, _setup, _span

PACKAGE = _package(risk_required=False, external_default=None)
OBJECTS = {"a": {"type": "work", "fields": {"risk": "high"}, **_span(0)},
           "gate": {"type": "gate", "title": "Gate", "schedule": {"mode": "fixed-point", "at": "2026-03-20"}},
           "b": {"type": "work", **_span(2)}}  # declares risk but has none
COLOUR_VALUES = set(COLOURS.values())


def _encode(tmp_path, objects, domain=("low", "high"), **extra):
    request = _setup(tmp_path, objects, PACKAGE, "risk", list(domain))
    if extra:
        view = yaml.safe_load(request.view.read_text(encoding="utf-8"))
        view["body"]["colorEncoding"].update(extra)
        request.view.write_text(yaml.safe_dump(view), encoding="utf-8")
    return request


def test_absent_value_keeps_base_paint_for_typed_and_untyped_objects(tmp_path):
    fills = _fills(_encode(tmp_path, OBJECTS))
    assert fills["a"] == COLOURS["high"]
    assert fills.get("b") not in COLOUR_VALUES and fills.get("gate") not in COLOUR_VALUES


def test_null_value_keeps_base_paint(tmp_path):
    objects = {**OBJECTS, "b": {"type": "work", "fields": {"risk": None}, **_span(2)}}
    fills = _fills(_encode(tmp_path, objects))
    assert fills["a"] == COLOURS["high"] and fills.get("b") not in COLOUR_VALUES


def test_value_outside_the_domain_is_still_refused(tmp_path):
    # `a` has risk=high, which a scale over [low] does not cover (the profile itself admits it).
    with pytest.raises(RenderFailed) as caught:
        render_draft(_encode(tmp_path, OBJECTS, domain=("low",)))
    assert caught.value.args[0] == "E_PRESENTATION_SCALE_VALUE"


def test_missing_names_a_domain_value_for_absent_and_null(tmp_path):
    objects = {**OBJECTS, "c": {"type": "work", "fields": {"risk": None}, **_span(3)}}
    fills = _fills(_encode(tmp_path, objects, missing="low"))
    assert fills["a"] == COLOURS["high"]
    assert fills["b"] == fills["c"] == fills["gate"] == COLOURS["low"]


def test_missing_base_is_the_default_spelled_out(tmp_path):
    fills = _fills(_encode(tmp_path, OBJECTS, missing="base"))
    assert fills.get("b") not in COLOUR_VALUES


def test_missing_outside_the_domain_is_refused(tmp_path):
    with pytest.raises(RenderFailed) as caught:
        render_draft(_encode(tmp_path, OBJECTS, missing="unknown"))
    assert caught.value.args[0] == "E_PRESENTATION_SCALE_MAPPING"


def test_style_encode_follows_the_same_rule(tmp_path):
    request = _setup(tmp_path, OBJECTS, PACKAGE, None, [])
    theme = yaml.safe_load(request.theme.read_text(encoding="utf-8"))
    theme["body"]["colorScales"] = {"s": {"slots": {"low": "s-low", "high": "s-high"}}}
    request.theme.write_text(yaml.safe_dump(theme), encoding="utf-8")
    scheme = yaml.safe_load(request.scheme.read_text(encoding="utf-8"))
    scheme["body"]["categories"].update({"s-low": COLOURS["low"], "s-high": COLOURS["high"]})
    request.scheme.write_text(yaml.safe_dump(scheme), encoding="utf-8")

    def style(**extra):
        path = tmp_path / "style.yaml"
        path.write_text(yaml.safe_dump({"version": "chrona/style/v0.2", "kind": "style", "id": "s", "body": {"rules": [
            {"id": "r", "when": {"semantic": "planned"}, "then": {"encode": {
                "channel": "fill", "source": {"field": "risk"}, "scale": "s", "domain": ["low", "high"], **extra}}}]}}), encoding="utf-8")
        return path

    from dataclasses import replace
    base = _fills(replace(request, style=style()))
    assert base["a"] == COLOURS["high"] and base.get("b") not in COLOUR_VALUES and base.get("gate") not in COLOUR_VALUES
    assert _fills(replace(request, style=style(missing="low")))["gate"] == COLOURS["low"]
