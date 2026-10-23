"""A finish-delta label is a member of its title's label packing, in key rows and ordinary rows (#1681)."""
from __future__ import annotations

from dataclasses import replace
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


def _key_row_request(tmp_path, *, folded_count=3):
    request = _request(tmp_path, placement="plot", folded=True, folded_count=folded_count, viewport="900xauto",
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


def test_key_row_zero_delta_omission_matches_title_only_packing_and_keeps_nonzero(tmp_path):
    def render_case(name, *, zero_actual, content, omit):
        case_dir = tmp_path / name
        case_dir.mkdir()
        # A single key-row subject also permits a title-only control under the
        # existing forecast-occurrence coverage contract.
        request = _key_row_request(case_dir, folded_count=1)
        view_path = Path(request.view)
        view = yaml.safe_load(view_path.read_text(encoding="utf-8"))
        labels = view["body"]["visibility"]["labels"]
        labels["content"] = list(content)
        labels["omitZeroDelta"] = omit
        _write(view_path, view)
        if zero_actual:
            actual_path = Path(request.actual)
            actual = yaml.safe_load(actual_path.read_text(encoding="utf-8"))
            for observation in actual["body"]["observations"]:
                observation["actual"]["start"] = "2026-01-05"
            _write(actual_path, actual)
        # Make a visible delta chip substantially taller than the mark/title lane. This makes
        # accidental measurement of an omitted +0d observable in the completed row geometry.
        theme_path = Path(request.theme) if request.theme else _compact_mark_theme(case_dir / "theme.yaml")
        theme = yaml.safe_load(theme_path.read_text(encoding="utf-8"))
        theme["body"]["values"]["delta-chip-min"] = {"type": "number", "value": 56.0}
        theme["body"]["roles"]["finish-delta-chip"] = {
            "backgroundTreatment": "fill", "chipPadding": "chip-padding",
            "chipMinBlockSize": "delta-chip-min",
        }
        theme["body"]["colorBindings"]["finish-delta-chip.fill"] = "text"
        _write(theme_path, theme)
        request = replace(request, theme=theme_path)
        return render_draft(request).rendered

    zero_omitted = render_case("zero-omitted", zero_actual=True,
                               content=("title", "finishDelta"), omit=True)
    zero_title_only = render_case("zero-title-only", zero_actual=True,
                                  content=("title",), omit=False)
    nonzero_omitted = render_case("nonzero-omitted", zero_actual=False,
                                  content=("title", "finishDelta"), omit=True)

    def geometry(rendered):
        return {item.scene_id: item.bounds for item in rendered.surface.primitives
                if item.scene_id.startswith(("planned:key-row:", "member-label:key-row:", "row-band:key-row"))}

    assert geometry(zero_omitted) == geometry(zero_title_only)
    assert not _texts(zero_omitted, "variance:key-row:")
    visible_nonzero = _texts(nonzero_omitted, "variance:key-row:")
    assert set(visible_nonzero) == {"variance:key-row:gate"}
    assert next(iter(visible_nonzero.values())).text == "+3d*"


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
