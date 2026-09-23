from pathlib import Path

import pytest

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.model.design_summary import summarize_presentation
from tools.design_gallery import DesignGalleryError, validate_catalog


ROOT = Path(__file__).parents[3]


def _summary(_corpus: str, _slide: str):
    base = ROOT / "examples/controller-z"
    closure = resolve_draft_render(project_path=base / "project.yaml", view_path=base / "views/executive.yaml",
        theme_path=base / "themes/executive-light.yaml", scheme_path=base / "schemes/executive-light.yaml",
        layout_path=base / "layouts/executive-review.yaml", actual_path=base / "actual.yaml").closure
    return summarize_presentation(closure)


def _catalog():
    entry = {"corpus": "demo", "slide": "one", "narrative": {"title": "Executive"},
             "comparison": {"set": "demo-pair", "axis": "content"},
             "designAssertions": {"content": {"surface": "table-timeline"}},
             "target": {"kind": "svg", "capabilities": ["accessibleText"]},
             "accessibility": {"note": "Text labels remain semantic."}}
    return {"version": "chrona/design-gallery/v0.1", "entries": [{"id": "one", **entry}, {"id": "two", **entry}]}


def test_design_gallery_validates_documentary_claims_against_derived_evidence():
    assert validate_catalog(_catalog(), corpus={("demo", "one"): {}}, summary_for=_summary,
                            target_for=lambda *_: {"kind": "svg", "capabilities": ["accessibleText"]}) == 2


def test_design_gallery_cannot_accept_misleading_or_unpaired_claims():
    catalog = _catalog()
    catalog["entries"][0]["designAssertions"]["content"]["surface"] = "network"
    with pytest.raises(DesignGalleryError, match="E_DESIGN_GALLERY_ASSERTION_MISMATCH"):
        validate_catalog(catalog, corpus={("demo", "one"): {}}, summary_for=_summary,
                         target_for=lambda *_: {"kind": "svg", "capabilities": ["accessibleText"]})
