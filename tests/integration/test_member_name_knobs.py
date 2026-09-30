"""End-to-end wiring of ``reviewSurface.memberNames`` (#573, I573-1) on lane and automatic rows."""
from pathlib import Path

import pytest
import yaml

from chrona.presentation.layout import surface_member_labels
from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderRequest, render_review


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def _layout(source: Path, destination: Path, *, distribution=None, member_names=None) -> Path:
    layout = yaml.safe_load(source.read_text(encoding="utf-8"))
    if distribution is not None:
        layout["reviewSurface"]["rowDistribution"] = distribution
    if member_names is not None:
        layout["reviewSurface"]["memberNames"] = member_names
    destination.write_text(yaml.safe_dump(layout, sort_keys=False), encoding="utf-8")
    return destination


def _lane_setup(tmp_path):
    example = _root() / "examples/controller-z"
    view = yaml.safe_load((example / "views/icons.yaml").read_text(encoding="utf-8"))
    view["version"] = "chrona/view/v0.28"
    body = view["body"]
    body.pop("tableColumns", None)
    body["rows"] = {"mode": "lanes", "laneTable": {"label": "group", "count": True}}
    body["visibility"]["labels"] = {"placement": "plot", "content": ["title"], "side": "end", "overflow": "suppress"}
    body["visuals"] = [item for item in body["visuals"]
                       if item.get("target", {}).get("kind") == "title" and item.get("side", "leading") == "leading"]
    view_path = tmp_path / "lane-view.yaml"
    view_path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")
    theme = yaml.safe_load((example / "themes/executive-light.yaml").read_text(encoding="utf-8"))
    # The lane summary needs the numeric role that this older Theme lacks.
    theme["body"]["roles"]["numeric"] = dict(theme["body"]["roles"]["text"])
    theme_path = tmp_path / "theme.yaml"
    theme_path.write_text(yaml.safe_dump(theme, sort_keys=False), encoding="utf-8")
    return dict(project_path=example / "project.yaml", view_path=view_path,
                theme_path=theme_path, scheme_path=example / "schemes/executive-light.yaml",
                actual_path=example / "actual.yaml", viewport=(2800, 1200),
                visual_profile="chrona-output/visual/v0.7-svg", icon_catalog_paths=(example / "icons.yaml",)
                ), example / "layouts/executive-review.yaml"


def _auto_setup(tmp_path):
    fixture = _root() / "tests/fixtures/multi-lane-milestones"
    view = yaml.safe_load((fixture / "view.yaml").read_text(encoding="utf-8"))
    view["body"]["visibility"]["labels"] = {
        "placement": "plot", "content": ["title"], "side": "auto", "overflow": "suppress"}
    view_path = tmp_path / "auto-view.yaml"
    view_path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")
    example = _root() / "examples/controller-z"
    return dict(project_path=fixture / "project.yaml", view_path=view_path,
                theme_path=example / "themes/executive-light.yaml", scheme_path=example / "schemes/executive-light.yaml",
                actual_path=fixture / "actual.yaml", viewport=(1600, 900)
                ), _root() / "conformance/layout-profile-intent-v0.2.yaml"


def _render(setup, layout_path, monkeypatch):
    calls = []
    original = surface_member_labels.place_member_name

    def spy(*args, **kwargs):
        calls.append((kwargs["maximum_end_gap"], kwargs["full_band"]))
        return original(*args, **kwargs)

    monkeypatch.setattr(surface_member_labels, "place_member_name", spy)
    draft = resolve_draft_render(layout_path=layout_path, **setup)
    rendered = render_review(RenderRequest(
        closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
        scheduler=ReferenceScheduler(), renderer=V05SvgRenderer(), draft_auto_block=draft.auto_block))
    labels = [item for item in rendered.surface.primitives if item.purpose == "member-label"]
    return calls, labels, rendered.artifact.content


def _font_size(labels):
    return labels[0].text_layout.font_size


@pytest.mark.parametrize("kind", ["lane", "auto"])
def test_default_and_explicit_defaults_render_identically(kind, tmp_path, monkeypatch):
    setup, base = _lane_setup(tmp_path) if kind == "lane" else _auto_setup(tmp_path)
    default_calls, labels, default_bytes = _render(setup, base, monkeypatch)
    assert labels and default_calls
    explicit = _layout(base, tmp_path / "explicit.yaml", member_names={"maxEndGapEm": 2})
    _, _, explicit_bytes = _render(setup, explicit, monkeypatch)
    assert explicit_bytes == default_bytes
    assert {gap for gap, _ in default_calls} == {2 * _font_size(labels)}


def test_max_end_gap_em_gives_two_bounds_on_lane_rows(tmp_path, monkeypatch):
    setup, base = _lane_setup(tmp_path)
    _, default_labels, _ = _render(setup, base, monkeypatch)
    font = _font_size(default_labels)
    bounds = {}
    for em in (0.5, 4):
        layout = _layout(base, tmp_path / f"em-{em}.yaml", member_names={"maxEndGapEm": em})
        calls, _, _ = _render(setup, layout, monkeypatch)
        bounds[em] = {gap for gap, _ in calls}
    assert bounds[0.5] == {0.5 * font} and bounds[4] == {4 * font}


def test_zero_end_gap_removes_end_placement(tmp_path, monkeypatch):
    setup, base = _lane_setup(tmp_path)
    _, default_labels, _ = _render(setup, base, monkeypatch)
    layout = _layout(base, tmp_path / "zero.yaml", member_names={"maxEndGapEm": 0})
    _, zero_labels, _ = _render(setup, layout, monkeypatch)
    assert len(zero_labels) < len(default_labels)


@pytest.mark.parametrize("kind,distribution,search,expected", [
    ("lane", "fill", None, True), ("lane", "pack", None, False),
    ("lane", "fill", "side-band", False), ("lane", "pack", "full-band", True),
    ("auto", "fill", None, False), ("auto", "pack", None, False),
    ("auto", "fill", "full-band", True), ("auto", "pack", "full-band", True), ("auto", "fill", "side-band", False),
])
def test_search_policy_is_independent_of_row_distribution_once_declared(
        kind, distribution, search, expected, tmp_path, monkeypatch):
    setup, base = _lane_setup(tmp_path) if kind == "lane" else _auto_setup(tmp_path)
    layout = _layout(base, tmp_path / "search.yaml", distribution=distribution,
                     member_names=None if search is None else {"search": search})
    calls, labels, _ = _render(setup, layout, monkeypatch)
    assert calls and {full for _, full in calls} == {expected}
