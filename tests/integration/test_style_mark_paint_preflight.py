"""Style-selected mark paint requirements are checked before Layout sizing."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from chrona.presentation.contracts.resources import ClosureIdentity, parse_contract
from chrona.presentation.layout import surface_count_closure, surface_render_plan
from chrona.presentation.model.semantic_registry import semantic_binding
from chrona.presentation.model.style_rules import StyleEvaluationError
from chrona.usecases import render_review as render_review_usecase
from tests.support import synthetic_review as sr


_ORIGINAL_COMPOSE = surface_count_closure.compose_surface_layout
_ORIGINAL_NORMALIZE = render_review_usecase.normalize_v05_surface_content
_ENCODED_COLOR = "#28c7b8"


def _style(rules):
    resource = {"version": "chrona/style/v0.2", "kind": "style", "id": "mark-paint-preflight",
                "body": {"rules": list(rules)}}
    return parse_contract(
        ClosureIdentity("style", "mark-paint-preflight", "test-v1", "sha256:" + "0" * 64), resource,
    ).rules


def _parts(*, stroke_only_point=False):
    parts = sr.bundle()
    body = parts["theme"]["body"]
    body["values"]["style-mark-height"] = {"type": "number", "value": 0.8}
    body["values"]["style-mark-offset"] = {"type": "number", "value": 0.1}
    role = {
        **body["roles"]["planned"],
        "markHeight": "style-mark-height",
        "markOffset": "style-mark-offset",
    }
    if stroke_only_point:
        body["values"]["style-mark-symbol"] = {
            "type": "symbol",
            "value": {
                "shape": "glyph",
                "viewBox": [100, 100],
                "parts": [{
                    "d": "M 10 10 L 90 90",
                    "paint": "stroke",
                }],
            },
        }
        role["symbol"] = "style-mark-symbol"
    body["roles"]["style-plan-no-fill"] = role
    body["colorBindings"].pop("style-plan-no-fill.fill", None)
    body["colorBindings"]["style-plan-no-fill.stroke"] = body["colorBindings"]["planned.stroke"]
    return parts


def _encoding():
    return {
        "id": "planned-fill",
        "when": {"semantic": "planned"},
        "then": {"encode": {
            "channel": "fill",
            "source": {"field": "owner"},
            "scale": "style-owner-fill",
            "domain": "firstAppearance",
        }},
    }


def _render(tmp_path, monkeypatch, *, source, parts, rules):
    captured = []

    def compose(request, **kwargs):
        result = _ORIGINAL_COMPOSE(request, **kwargs)
        captured.append(result)
        return result

    def normalize(*args, **kwargs):
        kwargs["style_rules"] = rules
        kwargs.setdefault("gate_declared", "gate" in parts["theme"]["body"]["roles"])
        return _ORIGINAL_NORMALIZE(*args, **kwargs)

    monkeypatch.setattr(surface_count_closure, "compose_surface_layout", compose)
    monkeypatch.setattr(render_review_usecase, "normalize_v05_surface_content", normalize)
    directory = Path(tmp_path)
    directory.mkdir(parents=True, exist_ok=True)
    rendered = sr.render(directory, source, presentation=parts)
    assert captured
    return rendered, captured[-1]


def test_selected_span_role_without_fill_requires_matching_style_encoding(tmp_path, monkeypatch):
    parts = _parts()
    theme = parts["theme"]["body"]
    theme["colorScales"] = {"style-owner-fill": {"slots": {"bus": "style-owner-fill"}}}
    parts["scheme"]["body"]["categories"]["style-owner-fill"] = _ENCODED_COLOR
    source = sr.project({"task": sr.span("task", date(2026, 1, 5), 10, owner="bus")})
    rules = _style((
        {"id": "role-without-fill", "when": {"semantic": "planned"},
         "then": {"role": "style-plan-no-fill"}},
        _encoding(),
    ))

    rendered, _ = _render(tmp_path, monkeypatch, source=source, parts=parts, rules=rules)
    binding = semantic_binding("planned")
    selected = [item for item in rendered.surface.primitives
                if item.source_ref == "task" and item.purpose == binding.purpose]
    assert selected
    assert all(item.theme_role == "style-plan-no-fill" for item in selected)
    assert all(item.paint.fill == _ENCODED_COLOR for item in selected)


def test_selected_span_role_without_fill_or_encoding_fails_before_layout_sizing(tmp_path, monkeypatch):
    parts = _parts()
    source = sr.project({"task": sr.span("task", date(2026, 1, 5), 10, owner="bus")})
    rules = _style(({
        "id": "role-without-fill",
        "when": {"semantic": "planned"},
        "then": {"role": "style-plan-no-fill"},
    },))
    measured = []
    original = surface_render_plan.surface_source_inputs

    def capture_sources(*args, **kwargs):
        measured.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(surface_render_plan, "surface_source_inputs", capture_sources)
    with pytest.raises(StyleEvaluationError) as caught:
        _render(tmp_path, monkeypatch, source=source, parts=parts, rules=rules)

    assert caught.value.diagnostic_id == "E_STYLE_ROLE_INCOMPATIBLE"
    assert caught.value.source_ref == "/body/rules/0/then/role"
    assert not measured


def test_selected_point_stroke_glyph_needs_no_role_fill_without_gate_theme_role(tmp_path, monkeypatch):
    parts = _parts(stroke_only_point=True)
    source = sr.project({"checkpoint": sr.point("checkpoint", date(2026, 1, 5), owner="bus")})
    rules = _style(({
        "id": "point-role-with-stroke-glyph",
        "when": {"semantic": "planned"},
        "then": {"role": "style-plan-no-fill"},
    },))

    rendered, _ = _render(tmp_path, monkeypatch, source=source, parts=parts, rules=rules)
    assert "gate" not in parts["theme"]["body"]["roles"]
    binding = semantic_binding("planned")
    glyphs = [item for item in rendered.surface.primitives
              if item.source_ref == "checkpoint" and item.purpose == binding.purpose]
    assert len(glyphs) == 1
    glyph = glyphs[0]
    assert glyph.theme_role == "style-plan-no-fill"
    assert glyph.paint.fill is None
    assert glyph.paint.stroke is not None
