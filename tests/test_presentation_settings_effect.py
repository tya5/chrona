"""Every leaf of resolved Theme must reach the rendered surface.

Presentation is data and the renderer is its consumer, so a Theme field that is
schema-valid, validated and then silently ignored is indistinguishable from a
misconfiguration by the author. This walks the resolved Theme, perturbs one leaf
at a time, re-renders, and compares bytes.

`KNOWN_INERT` is the honest public inventory of fields that do not yet reach the
surface. The assertion is an exact set match in both directions: a newly dead
field fails, and so does a field that starts working while still listed, which
keeps the inventory from rotting.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re

import pytest
import yaml

from chrona.layout import resolve_layout_profile, solve_layout
from chrona.presentation_settings import PresentationSettingsError, resolve_presentation_settings
from chrona.review_svg import _surface_content_input, build_review_projection, render_table_timeline_svg
from chrona.scheduler import schedule
from chrona.validation import load_yaml, validate_project

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"

CAPABILITIES = {"sourceMetadata", "accessibleText", "semanticRoles", "marker",
                "tableSemantics", "hierarchicalAxis"}
SLOT_SOURCES = {"title", "table", "timeline", "summary", "legend"}

# Identity and provenance: perturbing these is a font-resolution test, not a paint test.
SKIP_KEYS = {"path", "contentIdentity", "revision", "family", "algorithm", "version", "fontFamily"}

ENUMS = {"shape": ["diamond", "circle", "square"]}

# Theme leaves that do not reach the surface today. Each entry is a defect, not a
# design decision; see the referenced issue before removing one.
KNOWN_INERT = {
    # Stroke geometry is never emitted; the axis dash is hardcoded to "3 4".
    "theme.strokes.axisMajor.width",
    "theme.strokes.axisMajor.dash.0",
    "theme.strokes.axisMajor.dash.1",
    "theme.strokes.axisMinor.width",
    "theme.strokes.dependency.width",
    "theme.strokes.frame.width",
    "theme.strokes.frame.color",
    "theme.strokes.groupSeparator.width",
    "theme.strokes.groupSeparator.color",
    "theme.strokes.rowRule.width",
    "theme.strokes.rowRule.color",
    # Only varianceBehind is painted, so ahead / on-track / unknown cannot be shown.
    "theme.paints.varianceAhead.color",
    "theme.paints.varianceOnTrack.color",
    "theme.paints.varianceUnknown.color",
    "theme.paints.groupBand.color",
    # facetPaints.groups works; the default fallback layer beneath it does not.
    "theme.facetPaints.default.planned.color",
    "theme.facetPaints.default.actual.color",
    "theme.facetPaints.default.baseline.color",
    "theme.facetPaints.default.variance.color",
    # The missing-actual hatch is drawn from hardcoded values.
    "theme.missingPattern.spacing",
    "theme.missingPattern.angle",
    "theme.missingPattern.width",
    "theme.missingPattern.height",
    "theme.missingPattern.stroke.color",
    "theme.missingPattern.stroke.width",
    # Annotation chrome.
    "theme.annotation.boxFill.color",
    "theme.annotation.boxStroke.color",
    "theme.annotation.leader.color",
    # Typography for roles the surface never types.
    "theme.typography.quarter.size",
    "theme.typography.quarter.letterSpacing",
    "theme.typography.quarter.lineHeight",
    "theme.typography.missingActual.size",
    "theme.typography.missingActual.weight",
    "theme.typography.missingActual.letterSpacing",
    "theme.typography.missingActual.lineHeight",
    "theme.typography.notes.size",
    "theme.typography.notes.weight",
    "theme.typography.notes.letterSpacing",
    "theme.typography.notes.lineHeight",
    "theme.typography.summaryHeader.size",
    "theme.typography.summaryHeader.letterSpacing",
    "theme.typography.summaryHeader.lineHeight",
    "theme.typography.summaryMetric.size",
    "theme.typography.summaryMetric.weight",
    "theme.typography.summaryMetric.letterSpacing",
    "theme.typography.summaryMetric.lineHeight",
    # Marks.
    "theme.point.shape",
    "theme.bar.radius",
    "theme.bar.minWidth",
    "theme.varianceMarkerWidth",
}


def _leaves(node, prefix=()):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in SKIP_KEYS:
                continue
            yield from _leaves(value, prefix + (key,))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _leaves(value, prefix + (index,))
    else:
        yield prefix, node


def _perturb(key, value):
    """Return a schema-plausible different value, or None to skip this leaf."""
    if isinstance(value, bool):
        return not value
    if isinstance(value, (int, float)):
        return round(value * 1.5 + 3, 2)
    if isinstance(value, str):
        if re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
            return "#FF00AA" if value.upper() != "#FF00AA" else "#00FFAA"
        options = [option for option in ENUMS.get(key, []) if option != value]
        return options[0] if options else None
    return None


def _assign(tree, path, value):
    node = tree
    for step in path[:-1]:
        node = node[step]
    node[path[-1]] = value


def _surface():
    """Everything the render needs that does not depend on the Theme under test."""
    project = load_yaml(EXAMPLES / "controller-z-silicon-bringup.yaml")
    assert not validate_project(project)
    result = schedule(project)
    assert result.ok
    view = load_yaml(EXAMPLES / "controller-z-executive-view.yaml")
    theme = load_yaml(EXAMPLES / "controller-z-executive-theme.yaml")
    profile = load_yaml(EXAMPLES / "controller-z-executive-layout.yaml")
    projection = build_review_projection(
        project, result.placements, view,
        load_yaml(EXAMPLES / "controller-z-actual.yaml"),
        load_yaml(EXAMPLES / "controller-z-review-style.yaml"), theme)
    manifest = resolve_layout_profile(profile, SLOT_SOURCES)
    assert not manifest.diagnostics
    return project, view, theme, profile, projection, solve_layout(profile, manifest)


def _render(context, settings_document):
    project, view, theme, profile, projection, slots = context
    settings = resolve_presentation_settings(settings_document)
    surface = _surface_content_input(projection, project, view, settings, None, projection.window[0])
    return render_table_timeline_svg(
        project["project"]["title"], projection, project, view, theme,
        CAPABILITIES, profile, slots, settings, surface)


@pytest.fixture(scope="module")
def baseline():
    context = _surface()
    document = yaml.safe_load((EXAMPLES / "controller-z-editorial-settings.yaml").read_text())
    return context, document, _render(context, deepcopy(document))


def test_every_theme_leaf_reaches_the_rendered_surface(baseline):
    context, document, reference = baseline
    inert = set()
    exercised = 0

    for path, value in _leaves(document.get("theme", {}), ("theme",)):
        key = path[-1] if isinstance(path[-1], str) else path[-2]
        replacement = _perturb(key, value)
        if replacement is None or replacement == value:
            continue
        candidate = deepcopy(document)
        _assign(candidate, path, replacement)
        try:
            rendered = _render(context, candidate)
        except (PresentationSettingsError, ValueError, KeyError):
            continue  # perturbation left the schema; not a finding
        exercised += 1
        if rendered == reference:
            inert.add(".".join(str(step) for step in path))

    assert exercised > 40, "perturbation exercised too few leaves to be meaningful"

    newly_inert = sorted(inert - KNOWN_INERT)
    now_live = sorted(KNOWN_INERT - inert)
    assert not newly_inert, (
        "Theme fields stopped reaching the rendered surface:\n  "
        + "\n  ".join(newly_inert))
    assert not now_live, (
        "Theme fields now reach the surface; remove them from KNOWN_INERT:\n  "
        + "\n  ".join(now_live))
