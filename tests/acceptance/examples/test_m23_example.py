from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET

from chrona.presentation.presentation_settings import resolve_presentation_settings
from chrona.presentation.review_svg import (_surface_content_input, build_review_projection,
                               render_table_timeline_svg)
from chrona.scheduling.scheduler import schedule
from chrona.core.validation import load_yaml


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
EXAMPLES = ROOT / "examples" / "controller-z"
CAPABILITIES = {"sourceMetadata", "accessibleText", "semanticRoles", "marker",
                "tableSemantics", "hierarchicalAxis"}


def test_controller_z_m23_resources_reproduce_checked_in_svg_without_mutation():
    names = {
        "project": "project.yaml",
        "actual": "actual.yaml",
        "view": "shared/view.yaml",
        "style": "shared/style.yaml",
        "theme": "shared/theme.yaml",
        "profile": "shared/layout.yaml",
        "settings": "variants/review-detail/settings.yaml",
        "detail": "variants/review-detail/detail.yaml",
    }
    resources = {key: load_yaml(EXAMPLES / name) for key, name in names.items()}
    original = deepcopy(resources)
    settings = resolve_presentation_settings(resources["settings"])
    result = schedule(resources["project"])
    assert result.ok
    projection = build_review_projection(resources["project"], result.placements, resources["view"],
                                         resources["actual"], resources["style"], resources["theme"])
    content = _surface_content_input(projection, resources["project"], resources["view"], settings,
                                     detail_profile=resources["detail"])
    svg = render_table_timeline_svg(
        resources["project"]["project"]["title"], projection, resources["project"],
        resources["view"], resources["theme"], CAPABILITIES, resources["profile"],
        settings=settings, surface_content=content,
    )
    assert svg == (EXAMPLES / "variants/review-detail/expected.svg").read_text(encoding="utf-8")
    assert resources == original

    root = ET.fromstring(svg)
    purposes = [node.get("data-purpose") for node in root.iter()]
    assert purposes.count("group-detail-label") == 3
    assert purposes.count("group-detail-description") == 3
    assert purposes.count("observation-cell") == 6
    assert purposes.count("observation-source") == 2
    assert purposes.count("milestone-digest-entry") == 2
    sources = {node.get("data-source-ref") for node in root.iter()
               if node.get("data-purpose") == "observation-source"}
    assert sources == {"example-readiness", "example-release"}
