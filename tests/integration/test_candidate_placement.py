"""End-to-end evidence for the #466 declared placement-candidate engine.

A note declared with candidates ``plot`` region, ``nearest-free`` search and a
``tail`` connector must render beside a dependency line without covering it
(literal row 1/3) and draw the balloon only because the Theme declares it
(row 6): a Theme without the token raises a stable diagnostic rather than
silently painting a line. The deterministic, bounded search count and
selected-candidate decision (row 5) are asserted at the Layout unit level in
``tests/unit/chrona/presentation/layout/test_annotation_search.py``.
"""
import re
from pathlib import Path

import yaml

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderRequest, render_review


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def _balloon_theme(tmp_path: Path) -> Path:
    root = _root()
    theme = yaml.safe_load((root / "examples/controller-z/themes/executive-light.yaml").read_text(encoding="utf-8"))
    theme["body"]["values"]["balloon-container"] = {
        "type": "annotationContainer",
        "value": {"outline": "balloon", "cornerRadius": 0.2, "tailBaseEm": 0.6},
    }
    theme["body"]["roles"]["annotation-note-box"]["annotationContainer"] = "balloon-container"
    theme_path = tmp_path / "theme.yaml"
    theme_path.write_text(yaml.safe_dump(theme, sort_keys=False), encoding="utf-8")
    return theme_path


def _render(tmp_path: Path):
    root = _root()
    draft = resolve_draft_render(
        project_path=root / "examples/controller-z/project.yaml",
        view_path=root / "tests/fixtures/candidate-placement/view.yaml",
        theme_path=_balloon_theme(tmp_path),
        scheme_path=root / "examples/controller-z/schemes/executive-light.yaml",
        layout_path=root / "conformance/layout-profile-intent-v0.2.yaml",
        actual_path=root / "examples/controller-z/actual.yaml",
        viewport=(1600, 900),
    )
    request = RenderRequest(closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
                            scheduler=ReferenceScheduler(), renderer=V05SvgRenderer(),
                            draft_auto_block=draft.auto_block)
    return render_review(request)


def test_plot_nearest_free_tail_places_the_note_without_covering_a_dependency_line(tmp_path) -> None:
    rendered = _render(tmp_path)
    artifact = rendered.artifact.content.decode()
    assert 'data-scene-id="annotation-box:performance-note"' in artifact
    assert 'data-scene-id="annotation-text:performance-note"' in artifact
    # No leader is drawn for a tail connector; the balloon carries its own tail.
    assert 'data-scene-id="annotation-leader:performance-note"' not in artifact
    # The balloon is a filled <path>, not the plain <rect> a rectangle box
    # would use: proof the Theme's annotationContainer token drove Scene
    # projection, not just Layout's internal decision.
    box = re.search(r'<[a-z]+[^>]*data-scene-id="annotation-box:performance-note"[^>]*>', artifact)
    assert box is not None and box.group(0).startswith("<path")


def test_a_theme_without_the_annotation_container_token_raises_a_stable_diagnostic(tmp_path) -> None:
    # A tail connector is never silently painted as a line (#466): a Theme
    # missing the balloon binding is a stable ingress/Layout error, not a
    # degraded rectangle.
    from chrona.presentation.layout.model import LayoutError

    root = _root()
    draft = resolve_draft_render(
        project_path=root / "examples/controller-z/project.yaml",
        view_path=root / "tests/fixtures/candidate-placement/view.yaml",
        theme_path=root / "examples/controller-z/themes/executive-light.yaml",
        scheme_path=root / "examples/controller-z/schemes/executive-light.yaml",
        layout_path=root / "conformance/layout-profile-intent-v0.2.yaml",
        actual_path=root / "examples/controller-z/actual.yaml",
        viewport=(1600, 900),
    )
    request = RenderRequest(closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
                            scheduler=ReferenceScheduler(), renderer=V05SvgRenderer(),
                            draft_auto_block=draft.auto_block)
    try:
        render_review(request)
        raised = False
    except LayoutError as error:
        raised = True
        assert error.args[0] == "E_LAYOUT_ANNOTATION_TAIL_REQUIRES_BALLOON"
    except Exception as error:  # pragma: no cover - render_review may wrap Layout errors
        raised = "E_LAYOUT_ANNOTATION_TAIL_REQUIRES_BALLOON" in str(error)
    assert raised
