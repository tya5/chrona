"""The update-a-plan guide's statements about render output and the Δ finish unit match the product."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree

from chrona.app.cli import main
from tools.check_documented_commands import discover


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
GUIDE = Path("docs/guides/update-a-plan.md")


def _documented_file(name: str) -> str:
    text = (ROOT / GUIDE).read_text(encoding="utf-8")
    match = re.search(rf"<!-- chrona:doc-check file: {re.escape(name)} -->\s*```[^\n]*\n(?P<body>.*?)\n```",
                      text, re.DOTALL)
    assert match is not None, name
    return match["body"] + "\n"


def _render(monkeypatch, capsys, tokens: list[str]) -> dict:
    result, _, _ = _render_channels(monkeypatch, capsys, tokens)
    return result


def _render_channels(monkeypatch, capsys, tokens: list[str]) -> tuple[dict, str, str]:
    monkeypatch.setattr(sys, "argv", tokens)
    capsys.readouterr()
    main()
    captured = capsys.readouterr()
    return json.loads(captured.out.strip().splitlines()[-1]), captured.out, captured.err


def _guide_render(*, forecast: bool = False) -> list[str]:
    commands = [item.tokens for item in discover(ROOT) if item.path == GUIDE and item.tokens[1:2] == ("render",)]
    command = next((tokens for tokens in commands if ("--forecast" in tokens) is forecast), None)
    assert command is not None, f"the guide has a render command with forecast={forecast}"
    return list(command)


def _write_guide_files(tmp_path: Path) -> None:
    for name in ("update-baseline.yaml", "update-plan.yaml", "update-actual.yaml",
                 "update-actual-week2.yaml", "focus-window.yaml"):
        (tmp_path / name).write_text(_documented_file(name), encoding="utf-8")


def test_guide_says_render_replaces_an_existing_output_and_the_product_does(tmp_path, monkeypatch, capsys):
    prose = " ".join((ROOT / GUIDE).read_text(encoding="utf-8").split())
    assert "`render` replaces an existing `--output` file" in prose
    assert "refuses to replace" not in prose

    monkeypatch.chdir(tmp_path)
    _write_guide_files(tmp_path)
    tokens = _guide_render()
    output = Path(tokens[tokens.index("--output") + 1])
    output.write_text("old picture", encoding="utf-8")
    assert _render(monkeypatch, capsys, tokens)["status"] == "ok"
    assert output.read_bytes().startswith(b"<svg")


def test_guide_says_finish_delta_counts_working_days_and_the_product_does(tmp_path, monkeypatch, capsys):
    prose = " ".join((ROOT / GUIDE).read_text(encoding="utf-8").split())
    assert "in **working days** of the object's calendar" in prose
    assert "in calendar days" not in prose
    assert "`+2d` (Friday and Monday), not `+4d`" in prose

    monkeypatch.chdir(tmp_path)
    plan = ("version: timeline/v0.7\n"
            "project: {id: p, title: P, calendar: weekdays}\n"
            "calendars: {weekdays: {working_days: [mon, tue, wed, thu, fri]}}\n"
            "objects:\n"
            "  job: {type: task, title: Job, schedule: {mode: fixed-span, start: '2026-11-02', end: '2026-11-06'}}\n"
            "relations: []\n")
    actual = ("version: chrona/actual-set/v0.3\nkind: actual-set\nid: o\nbody:\n  asOf: '2026-11-12'\n"
              "  observations:\n    - {id: a, sequence: 1, projectObjectId: job, "
              "actual: {start: '2026-11-02', finish: '2026-11-10', progress: 1}}\n")
    (tmp_path / "plan.yaml").write_text(plan, encoding="utf-8")
    (tmp_path / "plan-nocal.yaml").write_text(
        plan.replace(", calendar: weekdays", "").replace("calendars: {weekdays: {working_days: [mon, tue, wed, thu, fri]}}\n", ""),
        encoding="utf-8")
    (tmp_path / "actual.yaml").write_text(actual, encoding="utf-8")

    def delta(project: str, out: str) -> str:
        result = _render(monkeypatch, capsys, ["chrona", "render", project, "--actual", "actual.yaml",
                                               "--preset", "target-b", "--output", out])
        assert result["status"] == "ok", result
        return " ".join(ElementTree.fromstring((tmp_path / out).read_bytes()).itertext())

    with_calendar = delta("plan.yaml", "cal.svg")
    assert "+2d" in with_calendar and "+4d" not in with_calendar
    without_calendar = delta("plan-nocal.yaml", "nocal.svg")
    assert "+4d" in without_calendar


def test_guide_forecast_command_shows_baseline_slip_and_keys_the_estimate(tmp_path, monkeypatch, capsys):
    prose = " ".join((ROOT / GUIDE).read_text(encoding="utf-8").split())
    assert "show slip against the original plan" in prose
    assert "`--forecast`" in prose
    assert "`Δ vs baseline` header names that reference" in prose
    assert "`Forecast (* estimated)` legend key" in prose
    assert "ordinary Actual comparison is against the current plan" in prose

    monkeypatch.chdir(tmp_path)
    _write_guide_files(tmp_path)
    tokens = _guide_render(forecast=True)
    assert "--forecast" in tokens
    assert tokens[tokens.index("--actual") + 1] == "update-actual-week2.yaml"
    assert tokens[tokens.index("--snapshot") + 1] == "update-baseline.yaml"
    assert _render(monkeypatch, capsys, tokens)["status"] == "ok"

    output = Path(tokens[tokens.index("--output") + 1])
    rendered_text = " ".join(ElementTree.fromstring(output.read_bytes()).itertext())
    rendered_text_folded = rendered_text.casefold()
    assert "δ vs baseline" in rendered_text_folded
    assert "forecast (* estimated)" in rendered_text_folded
    assert re.search(r"[+-]\d+d\*", rendered_text), rendered_text


def test_guide_places_render_warnings_in_stdout_json(tmp_path, monkeypatch, capsys):
    prose = " ".join((ROOT / GUIDE).read_text(encoding="utf-8").split())
    assert "final JSON result on standard" in prose
    assert "standard error" in prose

    monkeypatch.chdir(tmp_path)
    _write_guide_files(tmp_path)
    tokens = ["chrona", "render", "update-plan.yaml", "--actual", "update-actual.yaml",
              "--snapshot", "update-baseline.yaml", "--output", "default-no-ghost.svg"]
    result, stdout, _stderr = _render_channels(monkeypatch, capsys, tokens)
    assert result["status"] == "ok", result
    assert any(item["code"] == "W_SNAPSHOT_NOT_DRAWN" for item in result["warnings"]), result
    assert '"code": "W_SNAPSHOT_NOT_DRAWN"' in stdout


def test_guide_focus_window_uses_actual_asof_and_warns_for_hidden_relation(tmp_path, monkeypatch, capsys):
    prose = " ".join((ROOT / GUIDE).read_text(encoding="utf-8").split())
    assert "Focus a slide: hide finished work, show the next N weeks" in prose
    assert "Actual.asOf" in prose
    assert "Chrona does not substitute today's date" in prose
    assert "before: 1w, after: 6w, outside: omit" in prose
    assert "W_LAYOUT_RELATION_SUPPRESSED" in prose

    commands = [item.tokens for item in discover(ROOT)
                if item.path == GUIDE and item.tokens[1:2] == ("render",)
                and "--view" in item.tokens]
    assert len(commands) == 1
    tokens = list(commands[0])
    assert tokens[tokens.index("--view") + 1] == "focus-window.yaml"
    assert tokens[tokens.index("--actual") + 1] == "update-actual.yaml"
    assert tokens[tokens.index("--snapshot") + 1] == "update-baseline.yaml"

    monkeypatch.chdir(tmp_path)
    _write_guide_files(tmp_path)
    result, stdout, stderr = _render_channels(monkeypatch, capsys, tokens)
    assert result["status"] == "ok", result
    suppressed = [item for item in result["warnings"]
                  if item["code"] == "W_LAYOUT_RELATION_SUPPRESSED"]
    assert suppressed, result
    assert "launch-to-support" in json.dumps(suppressed)
    assert not stderr.strip()

    output = Path(tokens[tokens.index("--output") + 1])
    rendered_text = " ".join(ElementTree.fromstring(output.read_bytes()).itertext())
    assert "Build" in rendered_text and "Launch" in rendered_text
    assert "Design" not in rendered_text
    assert "Post-launch support" not in rendered_text
