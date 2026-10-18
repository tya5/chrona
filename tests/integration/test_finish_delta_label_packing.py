"""A finish-delta label is a member of its title's label packing, in key rows and ordinary rows (#1681)."""
from __future__ import annotations

from itertools import combinations
from pathlib import Path

import yaml

from chrona.resources import builtin_preset_source_root, safe_load
from chrona.usecases.draft_render import render_draft
from tests.integration.test_forecast_occurrence_coverage import _parts, _project, _request, _write

KEY_ROW = {"mode": "automatic", "points": "key-row", "keyRow": {"title": "Milestones"}}


def _compact_mark_theme(path):
    """A mark lane shorter than a label, as in the compact looks where lane labels used to meet (#1681)."""
    root = builtin_preset_source_root("presets/bundles/technical-print")
    theme = safe_load(root.joinpath("theme.yaml").read_bytes())
    theme["body"]["values"]["timeline-mark-size"]["value"] = 14
    return _write(path, theme)


def _key_row_request(tmp_path):
    request = _request(tmp_path, placement="plot", folded=True, folded_count=3, viewport="900xauto",
                       theme_path=_compact_mark_theme(tmp_path / "theme.yaml"))
    view = yaml.safe_load(Path(request.view).read_text(encoding="utf-8"))
    body = view["body"]
    body["rows"] = dict(KEY_ROW)
    body["grouping"] = {"by": "none", "missing": "ungrouped"}
    _write(Path(request.view), view)
    # Milestones a working day apart, so their titles and deltas compete for the same stretch of the row.
    project_path = Path(request.project)
    project = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    for index, relation in enumerate(project["relations"]):
        relation["lag"] = f"{min(index, 1)}wd"
    _write(project_path, project)
    _write(Path(request.snapshot), project)
    return request


def _texts(rendered, prefix):
    return {item.scene_id: item for item in rendered.surface.primitives
            if item.kind == "Text" and item.scene_id.startswith(prefix)}


def _overlap(left, right):
    width = min(left[0] + left[2], right[0] + right[2]) - max(left[0], right[0])
    height = min(left[1] + left[3], right[1] + right[3]) - max(left[1], right[1])
    return width * height if width > 0 and height > 0 else 0.0


def test_key_row_forecast_deltas_on_adjacent_milestones_never_meet_a_title(tmp_path):
    rendered = render_draft(_key_row_request(tmp_path)).rendered

    titles = _texts(rendered, "member-label:key-row:")
    deltas = _texts(rendered, "variance:key-row:")
    assert set(titles) == {"member-label:key-row:gate", "member-label:key-row:gate-2",
                           "member-label:key-row:gate-3"}  # every milestone stays labelled
    assert len(deltas) == 3 and all(item.text.endswith("*") for item in deltas.values())
    placed = {**titles, **deltas}
    for (left_id, left), (right_id, right) in combinations(placed.items(), 2):
        assert _overlap(left.bounds, right.bounds) <= 1.0, (left_id, right_id)


def test_ordinary_row_delta_and_title_keep_the_label_gap(tmp_path):
    rendered = render_draft(_request(tmp_path, placement="plot")).rendered

    deltas = {item.source_ref: item for item in _texts(rendered, "variance:").values()}
    titles = {item.source_ref: item for item in _texts(rendered, "member-label:").values()}
    assert set(deltas) == set(titles) == {"a", "b"}
    for source, delta in deltas.items():
        mark = next(item for item in rendered.surface.primitives
                    if item.scene_id.startswith(f"planned:row:{source}") or item.scene_id == f"planned:{source}:{source}")
        declared_gap = delta.bounds[0] - (mark.bounds[0] + mark.bounds[2])
        title_gap = titles[source].bounds[0] - (delta.bounds[0] + delta.bounds[2])
        assert declared_gap > 0
        assert title_gap >= declared_gap - 1e-6, (source, title_gap, declared_gap)
