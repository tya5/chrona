"""Draft ingress freezes explicit authoring files before they enter rendering."""
from pathlib import Path

import pytest

from chrona.presentation.model.closure import ClosureError, resolve_draft_render


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def _paths(root: Path) -> dict[str, Path]:
    return {
        "project_path": root / "examples/controller-z/project.yaml",
        "view_path": root / "examples/controller-z/views/executive.yaml",
        "theme_path": root / "examples/controller-z/themes/executive-light.yaml",
        "scheme_path": root / "examples/controller-z/schemes/executive-light.yaml",
        "layout_path": root / "conformance/layout-profile-intent-v0.2.yaml",
    }


def test_draft_closure_accepts_optional_review_inputs():
    root = _root()
    draft = resolve_draft_render(
        **_paths(root), actual_path=root / "examples/controller-z/actual.yaml",
        detail_path=root / "examples/controller-z/profiles/review-detail.yaml",
    )
    assert draft.closure.actual_set is not None
    assert draft.closure.detail_profile is not None
    assert draft.closure.context.identity.revision == "draft"
    assert draft.asset_root.name == "resources"


def test_draft_closure_reports_the_invalid_resource_schema_pointer(tmp_path):
    invalid_view = tmp_path / "view.yaml"
    invalid_view.write_text("version: chrona/view/v0.8\nkind: view\nid: bad\nbody: {}\n", encoding="utf-8")
    with pytest.raises(ClosureError) as error:
        resolve_draft_render(**(_paths(_root()) | {"view_path": invalid_view}))
    assert error.value.diagnostic_id == "E_VIEW_SCHEMA"
    assert error.value.source_ref.startswith("/body")
