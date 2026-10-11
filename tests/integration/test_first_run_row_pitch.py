"""The default row pitch follows declared marks/padding and completed table text."""
from datetime import date
from xml.etree import ElementTree

import pytest
import yaml

from chrona.resources import builtin_preset_source_root
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from tests.support import synthetic_review as sr


@pytest.mark.parametrize("text_size, mark_size, padding, expected", [
    (14, 34, 8, 42), (40, 34, 8, 64), (14, 50, 12, 62),
])
def test_default_row_pitch_equals_the_documented_completed_requirement(tmp_path, text_size, mark_size, padding, expected):
    theme = yaml.safe_load(builtin_preset_source_root("presets/bundles/editorial-readable-default")
                           .joinpath("theme.yaml").read_text())
    values = theme["body"]["values"]
    values["size.body"]["value"] = text_size
    values["timeline-mark-size"]["value"] = mark_size
    values["timeline-row-padding"]["value"] = padding
    theme_path = tmp_path / "theme.yaml"
    theme_path.write_text(yaml.safe_dump(theme, sort_keys=False), encoding="utf-8")
    source = sr.project({"a": sr.span("a", date(2027, 1, 4), 20, title="A"),
                         "b": sr.span("b", date(2027, 2, 1), 20, title="B")})
    path = tmp_path / "project.yaml"
    path.write_text(yaml.safe_dump(source), encoding="utf-8")
    rendered = render_draft(DraftRenderRequest(project=path, theme=theme_path, target_kind="svg")).rendered
    assert len(rendered.surface.rows) == 2
    assert expected == max(mark_size + padding, text_size * 1.4 + padding)
    assert all(row.bounds[3] == pytest.approx(expected) for row in rendered.surface.rows)
    svg = ElementTree.fromstring(rendered.artifact.content)
    assert svg.tag.endswith("svg")
    cells = [item for item in rendered.surface.primitives if item.purpose == "table-cell"]
    assert cells
    svg_ids = {element.get("data-scene-id", element.get("id")) for element in svg.iter()}
    assert all(item.scene_id in svg_ids for item in cells)
