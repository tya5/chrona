"""Two-Theme lane membership and icon handoff regression for #467 B3."""
from pathlib import Path

import yaml

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderRequest, render_review


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def _theme_variant(source: Path, destination: Path, *, family: str, size: int,
                   icon_scale: int, symbol: str, stroke_width: int) -> Path:
    theme = yaml.safe_load(source.read_text(encoding="utf-8"))
    values = theme["body"]["values"]
    values["editorial"]["value"] = family
    values["text-size"]["value"] = size
    values["icon-scale"]["value"] = icon_scale
    values["milestone-symbol"]["value"]["shape"] = symbol
    values["stroke-width"]["value"] = stroke_width
    # The lane summary uses numeric typography; the source Theme predates that
    # required role, so derive it from the same Theme text treatment.
    theme["body"]["roles"]["numeric"] = dict(theme["body"]["roles"]["text"])
    destination.write_text(yaml.safe_dump(theme, sort_keys=False), encoding="utf-8")
    return destination


def test_same_lane_view_under_two_themes_reaches_identical_scene_membership(tmp_path):
    root = _root()
    example = root / "examples/controller-z"
    view = yaml.safe_load((example / "views/icons.yaml").read_text(encoding="utf-8"))
    view["version"] = "chrona/view/v0.28"
    view_body = view["body"]
    view_body.pop("tableColumns", None)
    view_body["rows"] = {"mode": "lanes", "laneTable": {"label": "group", "count": True}}
    view_body["visibility"]["labels"] = {
        "placement": "plot", "content": ["title"], "side": "end", "overflow": "suppress",
    }
    # A global title icon is not lane-owned; member icons, when present, are
    # closed by the typed Layout-to-Scene inventory.
    view_body["visuals"] = [
        item for item in view_body["visuals"]
        if item.get("target", {}).get("kind") == "title" and item.get("side", "leading") == "leading"
    ]
    view_path = tmp_path / "same-lane-view.yaml"
    view_path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")
    theme_source = example / "themes/executive-light.yaml"
    themes = (
        _theme_variant(theme_source, tmp_path / "theme-a.yaml", family="Noto Sans", size=11,
                       icon_scale=1, symbol="diamond", stroke_width=1),
        _theme_variant(theme_source, tmp_path / "theme-b.yaml", family="Noto Sans Mono", size=13,
                       icon_scale=1.1, symbol="circle", stroke_width=3),
    )

    outputs = []
    for theme_path in themes:
        draft = resolve_draft_render(
            project_path=example / "project.yaml",
            view_path=view_path,
            theme_path=theme_path,
            scheme_path=example / "schemes/executive-light.yaml",
            layout_path=example / "layouts/executive-review.yaml",
            actual_path=example / "actual.yaml",
            viewport=(2800, 1200),
            visual_profile="chrona-output/visual/v0.7-svg",
            icon_catalog_paths=(example / "icons.yaml",),
        )
        request = RenderRequest(
            closure=draft.closure,
            snapshot_root=draft.asset_root,
            asset_root=draft.asset_root,
            scheduler=ReferenceScheduler(),
            renderer=V05SvgRenderer(),
            draft_auto_block=draft.auto_block,
        )
        outputs.append((draft.closure, render_review(request)))

    first_closure, first = outputs[0]
    second_closure, second = outputs[1]
    assert first_closure.project.identity == second_closure.project.identity
    assert first_closure.view.identity == second_closure.view.identity
    assert first_closure.resource("theme").content_identity != second_closure.resource("theme").content_identity

    first_members = {(item.row_id, item.member_id) for item in first.surface.lane_members}
    second_members = {(item.row_id, item.member_id) for item in second.surface.lane_members}
    assert first_members and first_members == second_members

    first_primitives = {item.scene_id: item for item in first.surface.primitives}
    second_primitives = {item.scene_id: item for item in second.surface.primitives}
    label_ids = {identifier for identifier in first_primitives if identifier.startswith("member-label:")}
    other_label_ids = {identifier for identifier in second_primitives if identifier.startswith("member-label:")}
    assert label_ids and label_ids == other_label_ids
    assert all(not any(item.startswith("W_LAYOUT_LABEL_SUPPRESSED:member-label:")
                       for item in output.scene.diagnostics) for output in (first, second))
    for identifier in label_ids:
        left, right = first_primitives[identifier], second_primitives[identifier]
        assert left.text == right.text
        assert left.text_layout.family != right.text_layout.family
        assert left.text_layout.font_size != right.text_layout.font_size
        assert left.text_layout.bounds[2] != right.text_layout.bounds[2]

    icon_ids = {identifier for identifier, item in first_primitives.items() if item.kind == "Icon"}
    assert icon_ids and icon_ids <= second_primitives.keys()
    assert "visual:title:leading" in icon_ids
    assert all(first_primitives[item].lane_row_id is None for item in icon_ids)
    assert any(first_primitives[item].bounds != second_primitives[item].bounds for item in icon_ids)

    planned_ids = {identifier for identifier, item in first_primitives.items() if item.purpose == "planned"}
    assert planned_ids and planned_ids <= second_primitives.keys()
    assert any(first_primitives[item].paint.stroke_width != second_primitives[item].paint.stroke_width
               for item in planned_ids)

    first_symbols = tuple(item.symbol.outline for item in first.surface.primitives if item.symbol is not None)
    second_symbols = tuple(item.symbol.outline for item in second.surface.primitives if item.symbol is not None)
    assert first_symbols != second_symbols
