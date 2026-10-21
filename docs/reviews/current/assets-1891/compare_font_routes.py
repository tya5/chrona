"""Print the font notes of render_draft and render_workspace for the same preset (#1891 row 1).

Run: python -m pytest -s -o python_files=compare_font_routes.py docs/reviews/current/assets-1891/compare_font_routes.py
It reuses the fixtures of tests/integration/test_preset_font_sets.py: no CJK provider package, one installed CJK
face named "Hiragino Sans" (a renamed Noto Sans JP), as on a plain `pip install chrona` on a Mac.
"""
import pytest

from tests.integration.test_preset_font_sets import (  # noqa: F401  (fixtures)
    DECLARING, _skipped, _workspace_for, hiragino, no_provider, starter)
from chrona.presentation.fonts.installed import use_installed_fonts
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from chrona.usecases.guided_render import WorkspaceRenderRequest, render_workspace


@pytest.mark.parametrize("identifier", DECLARING)
def test_print_font_notes(starter, tmp_path, no_provider, hiragino, identifier):  # noqa: F811
    workspace = _workspace_for(tmp_path, identifier)
    with use_installed_fonts(hiragino):
        guided = render_workspace(WorkspaceRenderRequest(workspace, "svg"))
        draft = render_draft(DraftRenderRequest(project=starter / "project.yaml", actual=starter / "actual.yaml",
                                                target_kind="svg", preset=str(workspace.parent / "preset" / "preset.yaml")))
    one, two = _skipped(draft), _skipped(guided)
    print(f"\n[{identifier}] render_draft: {len(one)} W_FONT_FAMILY_SKIPPED notes; render_workspace: {len(two)}; identical lists: {one == two}")
    print("   first note:", one[0])
    assert one == two and any("role=font-set" in item for item in one)
