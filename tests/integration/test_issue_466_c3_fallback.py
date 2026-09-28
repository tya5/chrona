"""The same HALCYON board can choose a declared rail after a crowded plot."""
from pathlib import Path

import yaml

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderRequest, render_review


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def test_crowded_halcyon_plot_selects_declared_rail_with_named_diagnostic(tmp_path, monkeypatch):
    import chrona.presentation.scene.v05_builder as builder

    example = ROOT / "examples/halcyon-1"
    view = yaml.safe_load((example / "views/02-programme-board.yaml").read_text(encoding="utf-8"))
    station = next(item for item in view["body"]["annotations"] if item["id"] == "station-note")
    view["body"]["annotations"] = [station]
    station["candidates"][0]["search"]["maxPositions"] = 1
    station["candidates"].append({
        "id": "rail-after-crowding",
        "region": {"kind": "slot", "source": "annotations"},
        "search": {"kind": "row-aligned"},
        "obstacles": {"classes": ["mark", "text", "label-visual", "dependency-route",
                                  "leader-route", "annotation-box", "port", "rule"]},
        "connector": {"kind": "leader"},
    })
    view_path = tmp_path / "crowded-view.yaml"
    view_path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")

    layout = yaml.safe_load((example / "layouts/wallboard.yaml").read_text(encoding="utf-8"))
    layout["requiredThemeTokens"] = sorted((*layout["requiredThemeTokens"], "crowded-rail-width"))
    layout["root"]["children"].append({
        "id": "annotations", "kind": "slot", "source": "annotations",
        "inlineSize": {"fixed": {"token": "crowded-rail-width"}}, "blockSize": "fill",
        "place": {"inline": "start", "block": "start", "safety": "safe"},
        "priority": "optional", "overflow": "visible-overflow",
    })
    layout_path = tmp_path / "crowded-layout.yaml"
    layout_path.write_text(yaml.safe_dump(layout, sort_keys=False), encoding="utf-8")

    theme = yaml.safe_load((example / "themes/wallboard.yaml").read_text(encoding="utf-8"))
    theme["body"]["values"]["crowded-rail-width"] = {"type": "number", "value": 900}
    theme_path = tmp_path / "crowded-theme.yaml"
    theme_path.write_text(yaml.safe_dump(theme, sort_keys=False), encoding="utf-8")

    draft = resolve_draft_render(
        project_path=example / "project.yaml", view_path=view_path,
        theme_path=theme_path,
        scheme_path=example / "schemes/control-room-dark.yaml",
        layout_path=layout_path, actual_path=example / "actual.yaml",
        viewport=(1920, 1080),
    )
    original = builder.compose_surface_layout
    compositions = []

    def capture(request):
        result = original(request)
        compositions.append(result)
        return result

    monkeypatch.setattr(builder, "compose_surface_layout", capture)
    rendered = render_review(RenderRequest(
        closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
        scheduler=ReferenceScheduler(), renderer=V05SvgRenderer(),
        draft_auto_block=draft.auto_block,
    ))
    decision = next(item for item in compositions[0].placement.decisions
                    if item.decision_id == "annotation:station-note")
    assert decision.selected_rung == "rail-after-crowding"
    assert decision.search_count > 1
    assert "W_LAYOUT_ANNOTATION_CANDIDATE_FALLBACK:station-note:rail-after-crowding" in rendered.scene.diagnostics
    assert b'data-scene-id="annotation-box:station-note"' in rendered.artifact.content
