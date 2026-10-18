"""#1682: a profile field `default`, and a colour encoding that does not apply to objects whose profile lacks the field."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from chrona.resources import default_preset_resource, default_preset_root
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from chrona.usecases.render_review import RenderFailed, RenderRejected

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


OBJECTS = {"a": {"type": "work", "fields": {"risk": "high", "external": True}, **_span(0)},
           "b": {"type": "work", "fields": {"risk": "low"}, **_span(1)},
           "c": {"type": "checkpoint", **_span(2)}}


def test_a_boolean_default_encodes_objects_that_omit_the_field_and_the_non_declaring_object_keeps_base_paint(tmp_path):
    (tmp_path / "base").mkdir()
    (tmp_path / "enc").mkdir()
    base = _fills(_setup(tmp_path / "base", OBJECTS, _package(), None, []))
    fills = _fills(_setup(tmp_path / "enc", OBJECTS, _package(), "external", ["true", "false"]))
    assert fills["a"] == COLOURS["true"]
    assert fills["b"] == COLOURS["false"]  # absent -> declared default false
    assert fills.get("c") == base.get("c") and fills.get("c") not in COLOURS.values()  # profile lacks `external`: base paint


def test_a_declaring_object_without_value_or_default_is_still_refused(tmp_path):
    objects = {"a": {"type": "work", "fields": {"risk": "high"}, **_span(0)}, "b": {"type": "work", **_span(1)},
               "c": {"type": "checkpoint", **_span(2)}}
    request = _setup(tmp_path, objects, _package(risk_required=False, external_default=None), "risk", ["low", "high"])
    with pytest.raises(RenderFailed) as caught:
        render_draft(request)
    assert caught.value.args[0] == "E_PRESENTATION_SCALE_VALUE"


def test_the_non_declaring_object_alone_does_not_trigger_the_refusal(tmp_path):
    objects = {"a": {"type": "work", "fields": {"risk": "high"}, **_span(0)}, "c": {"type": "checkpoint", **_span(2)}}
    fills = _fills(_setup(tmp_path, objects, _package(risk_required=False, external_default=None), "risk", ["low", "high"]))
    assert fills["a"] == COLOURS["high"] and fills.get("c") not in COLOURS.values()


def test_a_default_must_be_a_value_of_the_declared_type(tmp_path):
    request = _setup(tmp_path, OBJECTS, _package(external_default="yes"), None, [])
    with pytest.raises(RenderRejected) as caught:
        render_draft(request)
    assert [d.id for d in caught.value.diagnostics] == ["E_PROFILE_PACKAGE_INVALID"]
