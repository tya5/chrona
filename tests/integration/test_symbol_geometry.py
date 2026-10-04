"""A point mark's symbol takes its own size and offset per role (#1066).

Synthetic Projects through the packaged `executive-light` bundle (planned bar and gate fill the 16 px track, actual
marks take 0.6 of it at offset 0.2); no test reads `examples/`.
"""
from __future__ import annotations

from datetime import date

import pytest

from chrona.presentation.layout.presentation import MarkBandFrame, MarkGeometry
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_marks import resolve_mark_geometries
from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView
from tests.support import synthetic_review as sr

ACTUAL = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed", "body": {
    "asOf": "2026-03-02", "observations": [
        {"id": "g", "sequence": 1, "projectObjectId": "gate", "actual": {"at": "2026-02-14"}},
        {"id": "b", "sequence": 1, "projectObjectId": "bar", "actual": {"start": "2026-02-03", "finish": "2026-02-20"}}]}}
ROW_MODES = pytest.mark.parametrize("rows", ["lanes", "automatic"])


def _theme_with(parts, tokens):
    """Declare `symbolHeight` / `symbolOffset` (role -> (height, offset)) on the Theme; None leaves one absent."""
    theme = parts["theme"]["body"]
    for role, (height, offset) in tokens.items():
        for name, value in (("symbolHeight", height), ("symbolOffset", offset)):
            if value is not None:
                token = f"sym-{role}-{name}"
                theme["values"][token] = {"type": "number", "value": value}
                theme["roles"][role][name] = token


def _render(tmp_path, tokens=None, rows="lanes"):
    tmp_path.mkdir(parents=True, exist_ok=True)
    source = sr.project({"gate": sr.point("gate", date(2026, 2, 13)), "bar": sr.span("bar", date(2026, 2, 2), 40)})
    parts = sr.bundle("executive-light")
    if rows == "automatic":
        parts["view"]["body"]["rows"] = {"mode": "automatic"}
    _theme_with(parts, tokens or {})
    rendered = sr.render(tmp_path, source, presentation=parts, actual=ACTUAL, viewport=(1600, None))
    found = {}
    for item in rendered.surface.primitives:
        if item.scene_id.startswith(("planned:", "actual:")):
            found[item.scene_id.split(":")[0] + ("-gate" if "gate" in item.scene_id else "-bar")] = item.bounds
    return found


def _gate_track(tmp_path, rows="lanes"):
    """The gate row's track (top, size): the planned gate fills it when no token is declared."""
    planned = _render(tmp_path / "plain", None, rows)["planned-gate"]
    return planned[1], planned[3]


@ROW_MODES
def test_without_the_tokens_the_actual_gate_is_as_large_as_the_planned_gate_and_on_it(tmp_path, rows):
    marks = _render(tmp_path, None, rows)  # the default rule (#1074): max(markHeight, planned symbol), centred
    planned, actual = marks["planned-gate"], marks["actual-gate"]
    assert actual[2:] == pytest.approx(planned[2:])  # A1: no smaller than the planned gate (here 16 px, not 9.6)
    assert actual[1] == pytest.approx(planned[1])  # centred on the planned symbol
    bar = marks["actual-bar"]  # A2: the actual bar keeps markHeight 0.6 at markOffset 0.2
    assert bar[3] == pytest.approx(0.6 * planned[3]) and bar[1] == pytest.approx(marks["planned-bar"][1] + 0.2 * planned[3])


def test_declaring_the_band_values_restores_the_old_actual_gate_exactly(tmp_path):
    marks = _render(tmp_path, {"actual": (0.6, 0.2)})  # symbolHeight = markHeight, symbolOffset = markOffset
    track_top, track = _gate_track(tmp_path)
    assert marks["actual-gate"][2:] == pytest.approx((9.6, 9.6))
    assert marks["actual-gate"][1] == pytest.approx(track_top + 0.2 * track)


def test_the_default_follows_a_planned_role_that_declares_its_own_symbol(tmp_path):
    marks = _render(tmp_path, {"planned": (0.8, 0.1)})  # planned gate 12.8 px at 0.1; the actual follows it
    assert marks["actual-gate"][3] == pytest.approx(marks["planned-gate"][3])
    assert marks["actual-gate"][1] == pytest.approx(marks["planned-gate"][1])


@ROW_MODES
def test_the_actual_symbol_takes_the_declared_size_and_offset_and_the_bar_keeps_its_band(tmp_path, rows):
    marks = _render(tmp_path / "declared", {"actual": (0.9, 0.05)}, rows)
    track_top, track = _gate_track(tmp_path, rows)
    symbol = marks["actual-gate"]
    assert symbol[2] == pytest.approx(0.9 * track) and symbol[3] == pytest.approx(0.9 * track)  # B1: size
    assert symbol[1] == pytest.approx(track_top + 0.05 * track)  # B1: offset
    plain = _render(tmp_path / "plain", None, rows)["actual-gate"]  # the date, so the centre, is unchanged
    assert symbol[0] + symbol[2] / 2 == pytest.approx(plain[0] + plain[2] / 2)
    bar = marks["actual-bar"]  # B2: the bar of the same role keeps markHeight 0.6 at markOffset 0.2
    bar_top = marks["planned-bar"][1]
    assert bar[3] == pytest.approx(0.6 * track) and bar[1] == pytest.approx(bar_top + 0.2 * track)


def test_the_planned_role_honours_the_tokens_too(tmp_path):
    marks = _render(tmp_path / "declared", {"planned": (0.5, 0.25)})
    track_top, track = _gate_track(tmp_path)
    assert marks["planned-gate"][3] == pytest.approx(0.5 * track)
    assert marks["planned-gate"][1] == pytest.approx(track_top + 0.25 * track)
    assert marks["planned-bar"][3] == pytest.approx(16.0)  # the planned bar keeps markHeight 1


def test_a_declared_height_and_an_absent_offset_follow_the_default_rule(tmp_path):
    smaller = _render(tmp_path / "s", {"actual": (0.4, None)})  # not taller than the band: markOffset stays
    larger = _render(tmp_path / "l", {"actual": (0.8, None)})  # taller than the band: centred on the planned symbol
    top, track = _gate_track(tmp_path)
    assert smaller["actual-gate"][3] == pytest.approx(0.4 * track)
    assert smaller["actual-gate"][1] == pytest.approx(top + 0.2 * track)
    assert larger["actual-gate"][3] == pytest.approx(0.8 * track)
    assert larger["actual-gate"][1] == pytest.approx(top + 0.1 * track)


def test_a_declared_offset_with_an_absent_height_takes_the_default_height(tmp_path):
    marks = _render(tmp_path, {"planned": (0.8, 0.0), "actual": (None, 0.15)})
    top, track = _gate_track(tmp_path / "base")
    assert marks["actual-gate"][3] == pytest.approx(0.8 * track)  # the planned symbol's height, the declared offset
    assert marks["actual-gate"][1] == pytest.approx(top + 0.15 * track)


def _tokens(role_bindings, values):
    return ThemeTokenView({"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
                           "body": {"values": values, "roles": role_bindings}})


def _role(**extra):
    return {"markHeight": "h", "markOffset": "o", "markPaintOrder": "p", "markCornerRadius": "r", **extra}


VALUES = {name: {"type": "number", "value": value} for name, value in
          {"h": 0.5, "o": 0.1, "p": 1, "r": 0, "sh": 0.8, "so": 0.15, "bad": 0.5}.items()}


def test_every_role_with_a_symbol_resolves_the_tokens_into_its_geometry():
    roles = {name: _role(symbolHeight="sh", symbolOffset="so")
             for name in ("planned", "actual", "snapshot", "scenario", "missing-actual")}
    geometries = resolve_mark_geometries(_tokens(roles, VALUES))
    for name in ("planned", "actual", "snapshot", "scenario"):
        assert geometries[name].symbol_extent == (0.15, 0.8)  # B3
        frame = MarkBandFrame(None, 100.0, 20.0, geometries)
        assert frame.symbol_bounds(name) == pytest.approx((103.0, 16.0))
        assert frame.role_bounds(name) == pytest.approx((102.0, 10.0))  # the band is untouched


def test_a_role_without_the_tokens_has_the_band_as_its_symbol():
    roles = {name: _role() for name in ("planned", "actual", "snapshot", "scenario", "missing-actual")}
    geometry = resolve_mark_geometries(_tokens(roles, VALUES))["actual"]
    assert geometry.symbol_extent == (0.1, 0.5)


def test_an_out_of_range_symbol_is_refused():
    with pytest.raises(LayoutError) as error:
        MarkGeometry(0.5, 0.1, 1, 0.0, symbol_height=0.9, symbol_offset=0.2)  # 0.2 + 0.9 > 1
    assert error.value.diagnostic_id == "E_LAYOUT_MARK_OVERFLOW"
    roles = {name: _role() for name in ("planned", "actual", "snapshot", "scenario", "missing-actual")}
    values = {**VALUES, "neg": {"type": "number", "value": -1}, "zero": {"type": "number", "value": 0}}
    roles["actual"]["symbolOffset"] = "neg"
    with pytest.raises(ThemeTokenError) as negative:
        resolve_mark_geometries(_tokens(roles, values))
    assert negative.value.args[0] == "E_THEME_TOKEN_TYPE" or "symbolOffset" in str(negative.value)
    roles["actual"] = _role(symbolHeight="zero")
    with pytest.raises(ThemeTokenError):
        resolve_mark_geometries(_tokens(roles, values))


def test_a_band_taller_than_the_planned_symbol_is_kept():
    roles = {name: _role() for name in ("planned", "actual", "snapshot", "scenario", "missing-actual")}
    values = {**VALUES, "tall": {"type": "number", "value": 0.9}, "short": {"type": "number", "value": 0.3}}
    roles["actual"]["markHeight"] = "tall"
    roles["planned"]["markHeight"] = "short"
    geometry = resolve_mark_geometries(_tokens(roles, values))["actual"]
    assert geometry.symbol_extent == (0.1, 0.9)  # the band's own values: nothing enlarged, nothing moved


def test_the_default_applies_to_the_actual_role_only():
    roles = {name: _role() for name in ("planned", "actual", "snapshot", "scenario", "missing-actual")}
    values = {**VALUES, "big": {"type": "number", "value": 0.8}, "small": {"type": "number", "value": 0.3}}
    roles["planned"]["markHeight"] = "big"
    roles["actual"]["markHeight"] = "small"
    roles["snapshot"]["markHeight"] = "small"
    geometries = resolve_mark_geometries(_tokens(roles, values))
    assert geometries["actual"].symbol_height == 0.8  # enlarged to the planned symbol
    assert geometries["snapshot"].symbol_extent == (0.1, 0.3)  # baseline ghosts keep their band
    assert geometries["scenario"].symbol_extent == (0.1, 0.5)
