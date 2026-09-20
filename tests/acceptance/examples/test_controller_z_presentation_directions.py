"""The two presentation directions preserve one Controller Z fact set."""
from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from chrona.presentation.model.settings import resolve_presentation_settings
from chrona.presentation.model.projection import build_review_projection
from chrona.presentation.review.svg import render_table_timeline_svg
from chrona.scheduling.scheduler import schedule
from chrona.core.validation import load_yaml


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
EXAMPLES = ROOT / "examples" / "controller-z"
CAPABILITIES = {"sourceMetadata", "accessibleText", "semanticRoles", "marker",
                "tableSemantics", "hierarchicalAxis"}
SHARED = {
    "project": "project.yaml",
    "actual": "actual.yaml",
    "view": "shared/view.yaml",
    "style": "shared/style.yaml",
    "theme": "shared/theme.yaml",
    "profile": "shared/layout.yaml",
}


def render_direction(name):
    resources = {key: load_yaml(EXAMPLES / filename) for key, filename in SHARED.items()}
    resources["settings"] = load_yaml(EXAMPLES / "variants" / name / "settings.yaml")
    original = deepcopy(resources)
    settings = resolve_presentation_settings(resources["settings"])
    result = schedule(resources["project"])
    assert result.ok, result.diagnostics
    projection = build_review_projection(
        resources["project"], result.placements, resources["view"], resources["actual"],
        resources["style"], resources["theme"],
    )
    svg = render_table_timeline_svg(
        resources["project"]["project"]["title"], projection, resources["project"],
        resources["view"], resources["theme"], CAPABILITIES, resources["profile"],
        settings=settings,
    )
    assert resources == original
    return settings, svg


@pytest.mark.parametrize(
    ("name", "colors"),
    [
        ("signal", {"planned": "#4A84E8", "actual": "#12A87F",
                    "variance": "#FF5C7A", "milestone": "#BE8730",
                    "rowShade": "#FFFFFF"}),
        ("studio", {"planned": "#1B63E8", "actual": "#0E8F6A",
                    "variance": "#D92D52", "milestone": "#B8701E",
                    "rowShade": "#0E1726"}),
    ],
)
def test_direction_reproduces_svg_and_obeys_theme_contract(name, colors):
    settings, svg = render_direction(name)
    assert svg == (EXAMPLES / "variants" / name / "expected.svg").read_text(encoding="utf-8")
    assert render_direction(name)[1] == svg

    nodes = list(ET.fromstring(svg).iter())
    assert not any(node.get("data-purpose") == "item-label" for node in nodes)
    for purpose in ("planned", "actual", "milestone"):
        marks = [node for node in nodes if node.get("data-purpose") == purpose]
        assert marks and {node.get("fill") for node in marks} == {colors[purpose]}
    swatches = {node.get("data-source-ref"): node for node in nodes
                if node.get("data-purpose") == "legend-swatch"}
    for role in ("planned", "actual", "variance", "milestone"):
        assert swatches[role].get("fill") == colors[role]

    shades = [node for node in nodes if node.get("data-purpose") == "row-shade"]
    assert shades and {(node.get("fill"), node.get("opacity")) for node in shades} == {
        (colors["rowShade"], "0.04")
    }
    assert settings["theme"]["paints"]["rowShade"]["opacity"] == 0.035
    assert settings["theme"]["facetPaints"]["default"]["planned"] == \
           settings["theme"]["paints"]["planned"]
    assert settings["theme"]["facetPaints"]["default"]["actual"] == \
           settings["theme"]["paints"]["actual"]
    assert settings["theme"]["facetPaints"]["default"]["variance"] == \
           settings["theme"]["paints"]["varianceBehind"]


def test_directions_preserve_the_same_semantic_marks():
    semantic_outputs = []
    for name in ("signal", "studio"):
        _, svg = render_direction(name)
        semantic_outputs.append([
            (node.get("data-purpose"), node.get("data-source-ref"))
            for node in ET.fromstring(svg).iter()
            if node.get("data-purpose")
        ])
    assert semantic_outputs[0] == semantic_outputs[1]
