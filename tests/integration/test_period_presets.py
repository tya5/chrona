"""Every packaged Theme declares the named-period roles, and the band reads as a highlight (#880 item 1).

#582 left preset content to the presets lane: a View that selected a period under a packaged preset failed with
`E_THEME_ROLE_REQUIRED`, and the one HALCYON Theme that declared the roles painted the band in the canvas colour, darker than
the plot around it, so it read as a hole. Proven on a synthetic Project through each packaged Theme, so no corpus edit can
change what these tests prove.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility
from chrona.presentation.scene.serialization import scene_document, validate_scene_document
from chrona.resources import builtin_preset_source_root
from tests.support import synthetic_review as sr

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
BUNDLES = ROOT / "src/chrona/resources/presets/bundles"
THEMES = sorted(path.parent.name for path in BUNDLES.glob("*/theme.yaml"))
STARTER_CATALOG = ROOT / "src/chrona/resources/icons/chrona-theme-starter-v2026-09-29.yaml"
# The band's edges are seen against the plot like the boundary of a control: far above the decoration floor of 1.10.
EDGE_FLOOR = 3.0
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
    # Bars and a milestone lie on the band, so the gates read marks and closed days over it.
    source = sr.project({"a": sr.span("a", date(2026, 1, 5), 60), "b": sr.span("b", date(2026, 2, 10), 30, owner="b"),
                         "g": sr.point("g", date(2026, 2, 12))})
    source["periods"] = {"launch": {"title": "Launch window", "start": "2026-02-01", "end": "2026-03-01"}}
    directory = tmp_path / "render"
    directory.mkdir()
    return sr.render(directory, source, presentation=_parts(theme), icon_catalogs=(STARTER_CATALOG,))


def _findings(rendered):
    document = scene_document(rendered.scene)
    validate_scene_document(document)
    return document, evaluate_scene_contrast(document)


def _body(theme: str) -> dict:
    return yaml.safe_load((BUNDLES / theme / "theme.yaml").read_bytes())["body"]


@pytest.mark.parametrize("theme", THEMES)
def test_every_packaged_theme_declares_the_period_roles_and_their_colours(theme):
    body = _body(theme)

    for role in ("period-label", "period-label-chip"):
        assert role in body["roles"] and f"{role}.fill" in body["colorBindings"], role
    band = body["roles"]["period-band"]
    assert band["backgroundTreatment"] == "outline"
    assert body["values"][band["strokeWidth"]]["value"] >= 2
    assert "period-band.stroke" in body["colorBindings"] and "period-band.fill" not in body["colorBindings"]
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
    assert band.paint.stroke and band.paint.stroke_width >= 2
    assert [item.text for item in rendered.surface.primitives if item.purpose == "period-label"] == ["Launch window"]


@pytest.mark.parametrize("theme", THEMES)
def test_the_band_passes_the_gates_as_a_highlight_and_the_label_is_legible(tmp_path, theme):
    document, findings = _findings(_render(tmp_path, theme))

    band = [item for item in findings if item.visual_role == "period-band"]
    assert band and {item.paint_channel for item in band} == {"stroke"}
    assert all(item.severity == "info" and item.contrast_ratio >= EDGE_FLOOR for item in band)
    (label,) = [item for item in findings if item.visual_role == "period-label"]
    assert label.severity == "info" and label.floor == 4.5
    assert [item for item in evaluate_scene_perceptibility(document) if item.severity == "error"] == []


@pytest.mark.parametrize("theme", THEMES)
def test_what_lies_on_the_band_is_still_gated_and_passes(tmp_path, theme):
    # The band is an outline, so marks and closed days inside it keep the ground they had: none may be refused for it.
    _, findings = _findings(_render(tmp_path, theme))

    assert [(item.visual_role, item.code) for item in findings
            if item.severity == "error" and (item.ground_id or "").startswith("period-band")] == []


@pytest.mark.parametrize("theme", THEMES)
def test_the_band_is_an_outline_in_a_colour_that_is_not_the_canvas(tmp_path, theme):
    # An outline cannot be a hole, however the plot is painted around it.
    rendered = _render(tmp_path, theme)
    (band,) = [item for item in rendered.surface.primitives if item.purpose == "period-band"]
    colors = _parts(theme)["scheme"]["body"]["colors"]

    assert not band.paint.fill
    assert band.paint.stroke in {colors["accent"], colors["text"]}
    assert band.paint.stroke != colors["surface"]
