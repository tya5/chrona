"""Closure errors carry the value or file at fault in their detail (#829 S4)."""
from pathlib import Path

import pytest

from chrona.presentation.contracts import TypesetterIdentity
from chrona.presentation.model.closure import (
    ClosureError, _declared_child, _normalized_draft_source, _packaged_font_metrics, resolve_draft_render,
)
from chrona.usecases.diagnostic_messages import is_bare


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def _paths() -> dict[str, Path]:
    root = _root()
    return {
        "project_path": root / "examples/controller-z/project.yaml",
        "view_path": root / "examples/controller-z/views/executive.yaml",
        "theme_path": root / "examples/controller-z/themes/executive-light.yaml",
        "scheme_path": root / "examples/controller-z/schemes/executive-light.yaml",
        "layout_path": root / "conformance/layout-profile-intent-v0.2.yaml",
    }


def _say(call) -> str:
    with pytest.raises(ClosureError) as caught:
        call()
    detail = caught.value.detail or ""
    assert not is_bare(caught.value.diagnostic_id, detail), caught.value.diagnostic_id
    return detail


def test_an_incomplete_draft_names_the_files_it_lacks():
    paths = _paths()
    detail = _say(lambda: resolve_draft_render(project_path=paths["project_path"], view_path=paths["view_path"]))
    assert "theme" in detail and "color-scheme" in detail and "layout-profile" in detail and "view" not in detail.split(";")[0]


def test_a_typesetter_mismatch_names_the_target():
    assert "svg" in _say(lambda: resolve_draft_render(
        **_paths(), typesetter=TypesetterIdentity("typst", "0.13.1", "chrona-typst/v0.1")))
    assert "tikz" in _say(lambda: resolve_draft_render(**_paths(), target_kind="tikz"))


def test_an_icon_reference_without_a_colon_is_named():
    closure = resolve_draft_render(**_paths()).closure
    assert "'nocolon'" in _say(lambda: closure.icon_asset("nocolon"))


def test_a_preset_path_that_escapes_and_a_resource_without_an_id_are_named(tmp_path):
    assert "'../escape.yaml'" in _say(lambda: _declared_child(tmp_path, "../escape.yaml"))
    assert "view" in _say(lambda: _normalized_draft_source("view", {}))


def test_an_unusable_font_metrics_file_is_named(tmp_path):
    (tmp_path / "fonts").mkdir()
    (tmp_path / "fonts" / "default-font-metrics.yaml").write_text("- not a mapping\n")
    assert "default-font-metrics.yaml" in _say(lambda: _packaged_font_metrics(tmp_path))
