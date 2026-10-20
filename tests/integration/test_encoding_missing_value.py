"""#1789: an object with no value for the encoded field keeps base paint; `missing:` may name a domain value."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from chrona.resources import default_preset_resource, default_preset_root
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from chrona.usecases.render_review import RenderFailed


COLOURS = {"true": "#2e7d32", "false": "#c62828", "high": "#c62828", "low": "#2e7d32"}


def _package(risk_required=True, external_default=False):
    external = {"type": "boolean"} | ({"default": external_default} if external_default is not None else {})
    return {"version": "chrona/profile/v0.3", "packageId": "atlas-delivery", "requires": {"projectFormat": "timeline/v0.7"},
            "profiles": {
                "work": {"extends": "task", "fields": {"risk": {"type": "enum", "enumValues": ["low", "high"], "required": risk_required},
                                                       "external": external}},
                "checkpoint": {"extends": "task", "fields": {"owner": {"type": "string"}}}}}


def _span(index, **extra):
    return {"title": f"T{index}", "schedule": {"mode": "fixed-span", "start": f"2026-03-{2 + index * 7:02d}", "end": f"2026-03-{8 + index * 7:02d}"}, **extra}


def _setup(tmp_path: Path, objects, package, field, domain):
    (tmp_path / "ext").mkdir()
    (tmp_path / "ext" / "atlas.yaml").write_text(yaml.safe_dump(package), encoding="utf-8")
    project = {"version": "timeline/v0.7", "project": {"id": "atlas"},
               "extensions": [{"packageId": "atlas-delivery", "path": "ext/atlas.yaml", "revision": "git:" + "0123456789abcdef" * 2 + "01234567"}],
               "objects": objects}
    preset = yaml.safe_load(default_preset_resource().read_bytes())
    parts = {key: yaml.safe_load(default_preset_root().joinpath(d["path"]).read_bytes()) for key, d in preset["body"]["resources"].items()}
    if field is not None:
        parts["view"]["body"]["colorEncoding"] = {"scale": "s", "target": "planned", "source": {"field": field}, "domain": domain}
        parts["theme"]["body"]["colorScales"] = {"s": {"slots": {value: f"s-{value}" for value in domain}}}
        parts["colorScheme"]["body"]["categories"].update({f"s-{value}": COLOURS[value] for value in domain})
    paths = {}
    for key, value in parts.items():
        paths[key] = tmp_path / f"{key}.yaml"
        paths[key].write_text(yaml.safe_dump(value), encoding="utf-8")
    (tmp_path / "project.yaml").write_text(yaml.safe_dump(project), encoding="utf-8")
    return DraftRenderRequest(project=tmp_path / "project.yaml", target_kind="svg", view=paths["view"], theme=paths["theme"],
                              scheme=paths["colorScheme"], layout=paths["layout"], detail=paths["detailProfile"])


def _fills(request):
    rendered = render_draft(request).rendered
    return {p.scene_id.split(":")[1]: p.paint.fill for p in rendered.surface.primitives
            if p.scene_id.startswith("planned:") and getattr(p.paint, "fill", None)}


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
