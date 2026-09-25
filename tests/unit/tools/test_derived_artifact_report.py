from pathlib import Path

from tools.derived_artifact_report import DIFF_CHARACTER_LIMIT, report_stale_artifact


def test_stale_report_names_output_diff_and_refresh_without_writing(tmp_path, capsys, monkeypatch):
    output = tmp_path / "docs/report.md"
    output.parent.mkdir()
    output.write_text("old\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")

    report_stale_artifact(output=output, generated="new\n", code="E_REPORT_STALE",
                          refresh_argv=("python", "tools/report.py"), root=tmp_path)

    assert output.read_text(encoding="utf-8") == "old\n"
    captured = capsys.readouterr().out
    assert "E_REPORT_STALE: docs/report.md" in captured
    assert "--- committed/docs/report.md" in captured
    assert "+++ generated/docs/report.md" in captured
    assert "::error file=docs/report.md::E_REPORT_STALE" in captured
    assert "-old" in captured and "+new" in captured
    assert '["python", "tools/report.py"]' in captured


def test_stale_report_caps_large_diff(tmp_path, capsys):
    output = tmp_path / "report.md"
    output.write_text("old\n" * 10_000, encoding="utf-8")

    report_stale_artifact(output=output, generated="new\n" * 10_000, code="E_REPORT_STALE",
                          refresh_argv=("python", "tools/report.py"), root=tmp_path)

    captured = capsys.readouterr().out
    assert "diff truncated" in captured
    assert len(captured) < DIFF_CHARACTER_LIMIT + 500
