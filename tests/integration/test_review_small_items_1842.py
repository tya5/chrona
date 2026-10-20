"""Small review-presentation items of #1842 row 4, each with a synthetic case the guides rely on."""
from __future__ import annotations

from importlib.util import find_spec
import json
from pathlib import Path
import re
import sys

import pytest

from chrona.app.cli import main

PROFILE = """version: chrona/profile/v0.3
packageId: ghost-demo
contentIdentity: sha256:0000000000000000000000000000000000000000000000000000000000000000
requires: {projectFormat: timeline/v0.7}
profiles:
  work:
    extends: task
    fields:
      team: {type: enum, enumValues: [x, y], required: true}
"""
HEAD = """version: timeline/v0.7
project: {id: ghost-demo, title: Ghost demo}
extensions:
- {packageId: ghost-demo, path: profile.yaml, revision: 'git:0123456789abcdef0123456789abcdef01234567'}
objects:
"""
ALPHA = "  a: {type: work, title: Alpha, fields: {team: x}, schedule: {mode: fixed-span, start: 2026-11-02, end: 2026-11-06}}\n"
BETA = "  b: {type: work, title: Beta, fields: {team: y}, schedule: {mode: fixed-span, start: 2026-11-09, end: 2026-11-13}}\n"
GONE = "  r: {type: work, title: Gone, fields: {team: x}, schedule: {mode: fixed-span, start: 2026-11-04, end: 2026-11-10}}\n"
ACTUAL = """version: chrona/actual-set/v0.3
kind: actual-set
id: ghost-actual
body:
  asOf: '2026-11-12'
  observations:
  - {id: a-1, sequence: 1, projectObjectId: a, actual: {start: '2026-11-02', openUntil: asOf, progress: 0.5}}
  - {id: b-1, sequence: 1, projectObjectId: b, actual: {start: '%s', openUntil: asOf, progress: 0.0}}
"""
VIEW = """version: chrona/view/v0.28
kind: view
id: ghost-view
body:
%s  surface: table-timeline
  rows: {mode: automatic}
  selection: {include: {types: [span, point]}}
  grouping: {by: field, field: team, missing: Unset, presentation: header}
  ordering: {by: plannedStart, direction: ascending, tieBreak: id}
  tableColumns:
  - {id: Task, header: {wording: column.task}, source: title, missing: em-dash, align: start, width: content, headerOrientation: horizontal}
  - {id: Delta, %sheader: {wording: column.finishDeltaBaseline}, source: {facet: finishDelta}, missing: blank, align: end, width: content, headerOrientation: horizontal}
  window: {mode: selected-planned, marginDays: 7}
  comparison: {baseline: snapshot, baselineMarks: ghost, actual: optional, observationSelection: latest, deltaUnit: working-days, facets: [planned, actual, finishDelta]}
  markers:
  - {kind: asOf, source: actual, label: {wording: marker.today}%s}
  visibility:
    labels: {placement: table, content: [title], side: end, overflow: suppress}
    relations: {mode: none, overflow: suppress}
    annotations: none
  axis:
    tiers:
    - {unit: week, every: 1, role: labels, label: {form: start-day-month, align: start, overflow: thin-with-record, orientation: horizontal}}
"""


def _run(monkeypatch, capsys, *tokens: str) -> dict:
    monkeypatch.setattr(sys, "argv", ["chrona", *tokens])
    capsys.readouterr()
    try:
        main()
    except SystemExit:
        pass
    return json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def _texts(svg: str) -> dict[str, list[tuple[float, float]]]:
    found: dict[str, list[tuple[float, float]]] = {}
    for attrs, body in re.findall(r"<text([^>]*)>(.*?)</text>", svg, flags=re.S):
        x, y = (float(re.search(rf'\b{axis}="([^"]*)"', attrs)[1]) for axis in ("x", "y"))
        found.setdefault(re.sub(r"<[^>]+>", "", body), []).append((x, y))
    return found


def _files(tmp_path: Path, *, view: str, plan: str = HEAD + ALPHA + BETA, baseline: str = HEAD + GONE + ALPHA + BETA,
           start_b: str = "2026-11-12") -> None:
    for name, text in (("profile.yaml", PROFILE), ("plan.yaml", plan), ("baseline.yaml", baseline),
                       ("actual.yaml", ACTUAL % start_b), ("view.yaml", view)):
        (tmp_path / name).write_text(text, encoding="utf-8")


def _view(*, heading: str = "", fmt: str = "", marker_extra: str = "") -> str:
    return VIEW % (heading, fmt, marker_extra)


def test_removed_baseline_row_sits_in_its_own_group_not_under_the_last_one(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _files(tmp_path, view=_view())
    result = _run(monkeypatch, capsys, "render", "plan.yaml", "--snapshot", "baseline.yaml", "--view", "view.yaml",
                  "--preset", "mission-light", "--output", "out.svg")
    assert result["status"] == "ok"
    text = _texts((tmp_path / "out.svg").read_text(encoding="utf-8"))
    (_, alpha), (_, gone), (_, beta) = text["Alpha"][0], text["Gone (removed)"][0], text["Beta"][0]
    (_, header_x), (_, header_y) = text["x"][0], text["y"][0]
    # group x: header, Alpha, the removed Gone; then group y: header, Beta
    assert header_x < alpha < gone < header_y < beta


def test_delta_column_reads_sign_and_unit_with_format_signed_days(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _files(tmp_path, view=_view(fmt="format: signedDays, "))
    result = _run(monkeypatch, capsys, "render", "plan.yaml", "--snapshot", "baseline.yaml", "--actual", "actual.yaml",
                  "--forecast", "--view", "view.yaml", "--output", "out.svg")
    assert result["status"] == "ok"
    text = _texts((tmp_path / "out.svg").read_text(encoding="utf-8"))
    deltas = [value for value in text if re.fullmatch(r"[+-]\d+d\*", value)]
    assert len(deltas) == 2, sorted(text)  # one forecast delta per current task, each with sign, unit and the estimate mark


_PRESETS = [None, "target-b", "mission-light", "yuya"]  # None: the bundled default preset
_LOCALES = ["en-US", pytest.param("ja-JP", marks=pytest.mark.skipif(
    find_spec("chrona_fonts_noto_cjk") is None, reason="requires the optional local CJK font provider"))]


@pytest.mark.parametrize("locale", _LOCALES)
def test_marker_date_form_gives_every_preset_the_same_heading_as_of(tmp_path, monkeypatch, capsys, locale):
    monkeypatch.chdir(tmp_path)
    heading = "  heading: {title: '{project}', subtitle: 'as of {asOf}'}\n"
    seen = {}
    for preset in _PRESETS:
        _files(tmp_path, view=_view(heading=heading, marker_extra=", date: {form: day-month}"))
        name = preset or "default"
        result = _run(monkeypatch, capsys, "render", "plan.yaml", "--snapshot", "baseline.yaml", "--actual", "actual.yaml",
                      "--view", "view.yaml", *(("--preset", preset) if preset else ()), "--locale", locale,
                      "--output", f"{name}.svg")
        assert result["status"] == "ok", (name, result)
        text = _texts((tmp_path / f"{name}.svg").read_text(encoding="utf-8"))
        seen[name] = next(value for value in text if value.startswith("as of "))
    assert len(set(seen.values())) == 1, seen
    assert next(iter(seen.values())) == ("as of 12 Nov" if locale == "en-US" else "as of 11月12日")


def test_open_actual_that_starts_on_the_as_of_date_has_no_extent_and_says_so(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    def bars(start_b: str) -> tuple[int, list[str]]:
        _files(tmp_path, view=_view(), start_b=start_b)
        result = _run(monkeypatch, capsys, "render", "plan.yaml", "--snapshot", "baseline.yaml", "--actual", "actual.yaml",
                      "--view", "view.yaml", "--output", "out.svg")
        assert result["status"] == "ok"
        codes = [item["code"] for item in result["warnings"] if item["code"].startswith("W_LAYOUT_OPEN_ACTUAL")]
        return (tmp_path / "out.svg").read_text(encoding="utf-8").count('data-purpose="actual"'), codes

    # Alpha started 2026-11-02 and draws a bar to asOf 2026-11-12; Beta started on asOf itself: nothing to draw yet
    assert bars("2026-11-12") == (1, ["W_LAYOUT_OPEN_ACTUAL_INVALID"])
    # recorded from the day before, it has one day of extent and a bar
    assert bars("2026-11-11") == (2, [])
