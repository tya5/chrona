"""All bundled View/Layout closures preserve a three-level source path (#1701)."""
from __future__ import annotations

from datetime import date
import json
from xml.etree import ElementTree

import pytest
import yaml

from chrona.resources import builtin_preset_library_resource, builtin_preset_source_root
from chrona.presentation.scene.serialization import scene_document
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from tests.support import synthetic_review as sr


_PRESETS = tuple(item["id"] for item in yaml.safe_load(
    builtin_preset_library_resource().read_bytes())["entries"])
_LEVEL_TITLES = ("Atlas", "Borealis", "Curie")
_SVG = "chrona-output/visual/v0.6-svg"
_PNG = "chrona-output/visual/v0.6-png"
_PRESET_ENTRIES = yaml.safe_load(builtin_preset_library_resource().read_bytes())["entries"]


def _three_level_project(*, bound_role: bool = False, include_context: bool = True) -> dict:
    objects = {
        "atlas": {"type": "group", "title": _LEVEL_TITLES[0],
                  "schedule": {"mode": "rollup"}},
        "borealis": {"type": "group", "title": _LEVEL_TITLES[1], "parent": "atlas",
                     "schedule": {"mode": "rollup"}},
        "curie": {**sr.span("curie", date(2027, 1, 4), 8, owner="team-a",
                             title=_LEVEL_TITLES[2]), "parent": "borealis"},
    }
    if include_context:
        # Widen the selected timeline so the hierarchy member has a real inline
        # label budget; this is unrelated context, not part of its path.
        objects["context"] = sr.span("context", date(2027, 2, 1), 2,
                                    owner="team-a", title="Context")
    project = sr.project(objects, responsible_field_role=bound_role)
    assert ("responsible" in project.get("fieldRoles", {})) is bound_role
    return project


def _visible_text(surface) -> list[str]:
    return [primitive.text for primitive in surface.primitives
            if primitive.kind == "Text" and primitive.text]


def test_all_effective_presets_declare_path_except_the_lossless_default_route():
    for entry in _PRESET_ENTRIES:
        member = entry["members"]["view"]
        root = builtin_preset_source_root(member["sourceRoot"])
        view = yaml.safe_load(root.joinpath(member["sourcePath"]).read_bytes())["body"]
        labels = view["visibility"]["labels"]
        columns = view.get("tableColumns", ())
        if entry["id"] == "chrona-default-draft":
            assert view["grouping"] == {"by": "hierarchy", "depth": "all", "rollup": "header"}
            assert view["hierarchyColumn"] == "Task"
            assert "path" not in labels.get("content", ())
            assert any(column["id"] == "Task" and column["source"] == "title" for column in columns)
            continue

        assert "path" in labels.get("content", ()), entry["id"]
        if view.get("rows", {}).get("mode") != "lanes":
            assert any(column.get("source") == "path" for column in columns), entry["id"]


def _assert_names_once_per_full_path(texts: list[str], preset: str) -> None:
    expected = " / ".join(_LEVEL_TITLES)
    complete_paths = [text for text in texts if expected.casefold() in text.casefold()]
    for text in complete_paths:
        assert all(text.casefold().count(title.casefold()) == 1 for title in _LEVEL_TITLES), (preset, text)


@pytest.mark.parametrize("preset", _PRESETS)
def test_every_preset_renders_each_ancestor_name_to_scene_svg_and_native_png(tmp_path, preset):
    project_path = sr._write(tmp_path / "project.yaml", _three_level_project())
    actual_path = sr._write(tmp_path / "actual.yaml", {
        "version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "synthetic-observations",
        "body": {"asOf": "2027-01-01", "observations": []},
    })
    svg = render_draft(DraftRenderRequest(
        project=project_path, actual=actual_path, target_kind="svg", preset=preset, visual_profile=_SVG,
    )).rendered
    png = render_draft(DraftRenderRequest(
        project=project_path, actual=actual_path, target_kind="png", preset=preset, visual_profile=_PNG,
    )).rendered

    svg_text = _visible_text(svg.surface)
    png_text = _visible_text(png.surface)
    svg_adapter_text = ["".join(node.itertext()) for node in ElementTree.fromstring(svg.artifact.content).iter()
                        if node.tag.endswith("text") and "".join(node.itertext()).strip()]
    (tmp_path / f"{preset}.svg").write_bytes(svg.artifact.content)
    (tmp_path / f"{preset}.png").write_bytes(png.artifact.content)
    (tmp_path / f"{preset}.scene.json").write_text(
        json.dumps(scene_document(png.scene), ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8")
    for labels in (svg_text, svg_adapter_text, png_text):
        assert all(any(title.casefold() in text.casefold() for text in labels)
                   for title in _LEVEL_TITLES), (preset, labels, svg.surface.diagnostics)
        _assert_names_once_per_full_path(labels, preset)

    assert svg.artifact.content.lstrip().startswith(b"<svg"), preset
    assert png.artifact.content.startswith(b"\x89PNG\r\n\x1a\n"), preset


def test_bound_responsible_role_also_preserves_the_selected_paths_in_native_svg(tmp_path):
    project_path = sr._write(tmp_path / "project.yaml", _three_level_project(bound_role=True))
    rendered = render_draft(DraftRenderRequest(
        project=project_path, target_kind="svg", preset="mission-light", visual_profile=_SVG,
    )).rendered
    texts = [node.text or "" for node in ElementTree.fromstring(rendered.artifact.content).iter()
             if node.text and node.text.strip()]
    assert all(any(title.casefold() in text.casefold() for text in texts)
               for title in _LEVEL_TITLES), (texts, rendered.surface.diagnostics)


def test_single_full_window_member_keeps_the_existing_pointed_suppression(tmp_path):
    project_path = sr._write(tmp_path / "project.yaml",
                             _three_level_project(include_context=False))
    rendered = render_draft(DraftRenderRequest(
        project=project_path, target_kind="svg", preset="mission-light", visual_profile=_SVG,
    )).rendered
    svg_text = [node.text or "" for node in ElementTree.fromstring(rendered.artifact.content).iter()
                if node.text and node.text.strip()]
    assert not any(" / ".join(_LEVEL_TITLES) in text for text in svg_text)
    assert any(code.startswith("W_LAYOUT_LABEL_SUPPRESSED:member-label:")
               and ":curie" in code for code in rendered.surface.diagnostics)
