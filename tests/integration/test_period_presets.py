"""Every packaged Theme declares the named-period roles, and the band is a light filled highlight (#880 item 1, #911).

#582 left preset content to the presets lane: a View that selected a period under a packaged preset failed with
`E_THEME_ROLE_REQUIRED`, and the one HALCYON Theme that declared the roles painted the band in the canvas colour, darker than
the plot around it, so it read as a hole. Proven on a synthetic Project through each packaged Theme, so no corpus edit can
change what these tests prove.

#880 shipped an outline because a translucent fill could not be judged under a mark; #911 paints a translucent tint of a
scheme intent, now that a mark or label on a translucent host is judged on the host composited over the grounds beneath it
(#1013), so `--preset X --scheme Y` keeps working for every packaged scheme.
"""
from __future__ import annotations

import copy
from datetime import date
from pathlib import Path

import pytest
import yaml

from chrona.presentation.model.closure import ClosureError
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility
from chrona.presentation.scene.serialization import scene_document, validate_scene_document
from chrona.resources import builtin_preset_source_root
from tests.support import synthetic_review as sr

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
BUNDLES = ROOT / "src/chrona/resources/presets/bundles"
THEMES = sorted(path.parent.name for path in BUNDLES.glob("*/theme.yaml"))
STARTER_CATALOG = ROOT / "src/chrona/resources/icons/chrona-theme-starter-v2026-10-09.yaml"
INTENTS = {"surface", "surfaceRaised", "text", "textMuted", "accent", "positive", "negative", "warning", "neutral"}


def _parts(theme: str) -> dict:
    """The presentation resources a user gets with `theme`, with the editorial Theme variants on their own View."""
    if theme == "editorial":
        parts = sr.bundle("editorial")
        parts["view"] = yaml.safe_load(builtin_preset_source_root("presets/bundles/editorial")
                                       .joinpath("view-lanes.yaml").read_bytes())
    elif theme == "editorial-readable-default":
        parts = sr.bundle("editorial")
        root = builtin_preset_source_root("presets/bundles/editorial-readable-default")
        parts["view"] = yaml.safe_load(root.joinpath("view.yaml").read_bytes())
        parts["theme"] = yaml.safe_load(root.joinpath("theme.yaml").read_bytes())
    else:
        parts = sr.bundle(theme)
    parts["view"]["body"]["window"] = {"mode": "explicit", "start": "2026-01-01", "end": "2026-04-01"}
    parts["view"]["body"]["periods"] = [{"id": "launch", "label": {"placement": "top"}}]
    return parts


def _render(tmp_path: Path, theme: str):
    return _render_with(tmp_path, _parts(theme))


def _render_with(tmp_path: Path, parts: dict, *, period: bool = True):
    # Bars and a milestone lie on the band, so the gates read marks and closed days over it.
    source = sr.project({"a": sr.span("a", date(2026, 1, 5), 60), "b": sr.span("b", date(2026, 2, 10), 30, owner="b"),
                         "g": sr.point("g", date(2026, 2, 12))})
    if period:
        source["periods"] = {"launch": {"title": "Launch window", "start": "2026-02-01", "end": "2026-03-01"}}
    directory = tmp_path / "render"
    directory.mkdir()
    return sr.render(directory, source, presentation=parts, icon_catalogs=(STARTER_CATALOG,))


def _findings(rendered):
    document = scene_document(rendered.scene)
    validate_scene_document(document)
    return document, evaluate_scene_contrast(document)


def _body(theme: str) -> dict:
    return yaml.safe_load((BUNDLES / theme / "theme.yaml").read_bytes())["body"]



@pytest.mark.parametrize("theme", THEMES)
def test_every_packaged_theme_declares_the_period_roles_and_a_light_tint(theme):
    body = _body(theme)

    for role in ("period-label", "period-label-chip"):
        assert role in body["roles"] and f"{role}.fill" in body["colorBindings"], role
    band = body["roles"]["period-band"]
    assert band["backgroundTreatment"] == "fill" and "strokeWidth" not in band
    # A light tint: translucent enough to stay a highlight, opaque enough to read against the plot.
    assert 0.08 <= body["values"][band["opacity"]]["value"] <= 0.25
    assert "period-band.fill" in body["colorBindings"] and "period-band.stroke" not in body["colorBindings"]
    assert body["roles"]["period-label"]["contrastTreatment"] == "required"


@pytest.mark.parametrize("theme", THEMES)
def test_the_period_roles_bind_only_the_intents_every_color_scheme_has(theme):
    # A binding to a scheme category that a user's scheme lacks would break `--preset X --scheme Y` for every View,
    # so the packaged Themes bind the period roles to the closed set of intents.
    bound = {value for key, value in _body(theme)["colorBindings"].items() if key.startswith("period-")}

    assert bound and bound <= INTENTS, sorted(bound - INTENTS)


@pytest.mark.parametrize("theme", THEMES)
def test_a_view_that_selects_a_period_renders_under_every_packaged_theme(tmp_path, theme):
    rendered = _render(tmp_path, theme)

    (band,) = [item for item in rendered.surface.primitives if item.purpose == "period-band"]
    assert band.paint.fill and not band.paint.stroke and band.paint.opacity < 1
    assert [item.text for item in rendered.surface.primitives if item.purpose == "period-label"] == ["Launch window"]


@pytest.mark.parametrize("theme", THEMES)
def test_the_band_is_a_perceptible_highlight_and_the_label_is_legible(tmp_path, theme):
    document, findings = _findings(_render(tmp_path, theme))

    band = [item for item in findings if item.visual_role == "period-band"]
    assert band and {item.paint_channel for item in band} == {"fill"}
    assert all(item.severity == "info" and item.contrast_ratio >= 1.10 for item in band)
    (label,) = [item for item in findings if item.visual_role == "period-label"]
    assert label.severity == "info" and label.floor == 4.5
    assert [item for item in evaluate_scene_perceptibility(document) if item.severity == "error"] == []


@pytest.mark.parametrize("theme", THEMES)
def test_what_lies_on_the_band_is_judged_on_the_tinted_ground_and_passes(tmp_path, theme):
    # The band is translucent, so a mark, a closed day or the label on it is judged on the tint composited over the
    # ground beneath it (#1013): none may be refused, and the marks that lie on the band are in fact judged.
    _, findings = _findings(_render(tmp_path, theme))

    assert [(item.visual_role, item.code) for item in findings if item.severity == "error"] == []
    assert [(item.visual_role, item.code) for item in findings if item.severity == "warning" and (
        item.visual_role in {"period-band", "period-label"} or (item.ground_id or "").startswith("period-band"))] == []
    assert {item.visual_role for item in findings if (item.ground_id or "").startswith("period-band")} >= {"planned", "text"}


@pytest.mark.parametrize("theme", THEMES)
def test_the_band_is_a_tint_of_an_intent_that_is_not_the_canvas(tmp_path, theme):
    # A tint of the accent (or text) over the plot cannot be a hole: it differs from the canvas it lies on.
    rendered = _render(tmp_path, theme)
    (band,) = [item for item in rendered.surface.primitives if item.purpose == "period-band"]
    colors = _parts(theme)["scheme"]["body"]["colors"]

    assert band.paint.fill in {colors["accent"], colors["text"]}
    assert band.paint.fill != colors["surface"]


SCHEMES = sorted({"editorial" if theme.startswith("editorial") else theme for theme in THEMES})


def _outcome(tmp_path: Path, parts: dict, *, period: bool):
    """The render, or the diagnostic id that refuses this Theme with this scheme."""
    parts = {kind: copy.deepcopy(value) for kind, value in parts.items()}
    if not period:
        parts["view"]["body"].pop("periods")
    try:
        return _render_with(tmp_path, parts, period=period)
    except ClosureError as error:
        return error.diagnostic_id


@pytest.mark.parametrize("scheme", SCHEMES)
@pytest.mark.parametrize("theme", THEMES)
def test_a_filled_band_survives_every_packaged_scheme_override(tmp_path, theme, scheme):
    # `--preset X --scheme Y`: the band binds only closed intents, so selecting a period adds no incompatibility. A pair that
    # a scheme's own gates refuse for the plain View (a scale or label rule of that Theme) is refused identically with the
    # period and is not this role's; every other pair renders the period, painting that scheme's own colour, with no error.
    parts = _parts(theme)
    parts["scheme"] = _parts(scheme)["scheme"]
    (tmp_path / "plain").mkdir()
    plain = _outcome(tmp_path / "plain", parts, period=False)
    with_period = _outcome(tmp_path, parts, period=True)

    if isinstance(plain, str):
        assert with_period == plain
        return
    assert not isinstance(with_period, str), with_period
    (band,) = [item for item in with_period.surface.primitives if item.purpose == "period-band"]
    colors = parts["scheme"]["body"]["colors"]
    assert band.paint.fill in {colors["accent"], colors["text"]} and band.paint.opacity < 1
    document, findings = _findings(with_period)
    assert [item for item in findings if item.severity == "error"] == []
    assert [item for item in evaluate_scene_perceptibility(document) if item.severity == "error"] == []
