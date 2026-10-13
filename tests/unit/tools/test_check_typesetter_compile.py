"""The typesetter compile gate is deterministic under mocked native binaries."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tools import check_typesetter_compile as checker


def _matrix(tmp_path, monkeypatch, *, refusal=False, export_failure=None,
            compile_failure=None, missing_pdf=None, bad_typst_version=False,
            malformed_export=None, export_timeout=None, compile_timeout=None):
    monkeypatch.setattr(checker, "list_builtin_presets",
                        lambda: [{"id": "executive-light"}, {"id": "technical-print"}])
    calls = []

    environments = []

    def runner(command, *, cwd, capture_output, text, timeout, env=None):
        command = [str(item) for item in command]
        calls.append(command)
        if env is not None:
            environments.append(dict(env))
        if command[-1] == "--version":
            tool = Path(command[0]).name
            version = "9.9.9" if bad_typst_version and tool == "typst" else checker.TARGETS[
                "typst" if tool == "typst" else "tikz"]["version"]
            label = "typst" if tool == "typst" else "Tectonic"
            return subprocess.CompletedProcess(command, 0, f"{label} {version}\n", "")

        if "-m" in command and "chrona" in command:
            target = command[command.index("--format") + 1]
            preset = command[command.index("--preset") + 1] if "--preset" in command else None
            key = (target, preset or "default")
            if key == export_timeout:
                raise subprocess.TimeoutExpired(command, timeout)
            if key == malformed_export:
                return subprocess.CompletedProcess(command, 0, "not json", "")
            if key == export_failure:
                payload = {"status": "rejected", "diagnostics": [{"code": "E_NEW_REFUSAL",
                                                                    "message": "unsupported"}]}
                return subprocess.CompletedProcess(command, 1, json.dumps(payload), "")
            if refusal and preset == "technical-print":
                payload = {"status": "rejected", "diagnostics": [{
                    "code": "E_VISUAL_CAPABILITY_UNSUPPORTED",
                    "message": "pattern on axis-band-rect requires role axis-band",
                }]}
                return subprocess.CompletedProcess(command, 1, json.dumps(payload), "")
            source = Path(command[command.index("--output") + 1])
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("original exported source\n", encoding="utf-8")
            return subprocess.CompletedProcess(command, 0,
                                               json.dumps({"status": "ok", "diagnostics": [], "warnings": []}), "")

        target = "typst" if Path(command[0]).name == "typst" else "tikz"
        source = Path(command[-2] if target == "typst" else command[-1])
        preset = source.parent.name
        if (target, None if preset == "default" else preset) == compile_failure:
            return subprocess.CompletedProcess(command, 1, "", "compile failed")
        if (target, preset) == compile_timeout:
            raise subprocess.TimeoutExpired(command, timeout)
        if target == "typst":
            pdf = Path(command[-1])
        else:
            pdf = Path(command[command.index("--outdir") + 1]) / f"{source.stem}.pdf"
        if (target, None if preset == "default" else preset) != missing_pdf:
            pdf.parent.mkdir(parents=True, exist_ok=True)
            pdf.write_bytes(b"%PDF mock")
        return subprocess.CompletedProcess(command, 0, "compiled", "")

    report = checker.run_matrix(typst=Path("/tools/typst"), tectonic=Path("/tools/tectonic"),
                                output=tmp_path / "artifacts", project=tmp_path / "project.yaml",
                                actual=tmp_path / "actual.yaml", runner=runner)
    return report, calls, tmp_path / "artifacts", environments


def test_successful_matrix_retains_sources_pdfs_logs_and_report(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", "preserved-test-path")
    report, calls, out, environments = _matrix(tmp_path, monkeypatch)

    assert report["status"] == "complete"
    assert report["case_count"] == 6
    assert {case["status"] for case in report["cases"]} == {"compiled"}
    assert all(Path(case["source"]).is_file() and Path(case["pdf"]).is_file()
               for case in report["cases"])
    assert (out / "report.json").is_file()
    assert (out / "typst-version.log.stdout.log").read_text(encoding="utf-8").strip() == "typst 0.15.1"
    assert any("--font-path" in command and str(checker.ROOT / "src/chrona/resources/fonts") in command
               for command in calls)
    assert all("--actual" in command for command in calls if "-m" in command and "chrona" in command)
    config = out / "fontconfig" / "fonts.conf"
    assert config.is_file()
    assert str(checker.ROOT / "src/chrona/resources/fonts") in config.read_text(encoding="utf-8")
    assert len(environments) == 3
    assert all(environment["FONTCONFIG_FILE"] == str(config) for environment in environments)
    assert all(environment["PATH"] == "preserved-test-path" for environment in environments)


def test_technical_print_pattern_refusal_is_an_export_failure_until_exportable(tmp_path, monkeypatch):
    report, calls, _out, _envs = _matrix(tmp_path, monkeypatch, refusal=True)

    refused = [case for case in report["cases"] if case["preset"] == "technical-print"]
    assert report["status"] == "failed"
    assert len(refused) == 2 and all(case["status"] == "failed" for case in refused)
    assert all(case["error"]["type"] == "export_error" for case in refused)
    assert all(not Path(case["source"]).exists() and not Path(case["pdf"]).exists()
               for case in refused)
    assert sum("--output" in call for call in calls) == 6


def test_unexpected_refusal_and_compiler_error_are_typed_and_matrix_continues(tmp_path, monkeypatch):
    report, calls, _out, _envs = _matrix(tmp_path, monkeypatch,
                                  export_failure=("typst", "executive-light"),
                                  compile_failure=("tikz", "executive-light"))

    cases = {(case["target"], case["preset"]): case for case in report["cases"]}
    assert report["status"] == "failed"
    assert cases[("typst", "executive-light")]["error"]["type"] == "export_error"
    assert cases[("tikz", "executive-light")]["error"]["type"] == "compiler_error"
    assert len([call for call in calls if "-m" in call and "chrona" in call]) == 6
    assert cases[("tikz", "technical-print")]["status"] == "compiled"


def test_wrong_version_records_each_case_but_still_runs_the_other_engine(tmp_path, monkeypatch):
    report, _calls, _out, _envs = _matrix(tmp_path, monkeypatch, bad_typst_version=True)

    cases = [case for case in report["cases"] if case["target"] == "typst"]
    assert report["status"] == "failed"
    assert len(cases) == 3 and all(case["error"]["type"] == "version_error" for case in cases)
    assert sum(case["status"] == "compiled" for case in report["cases"]) == 3


def test_malformed_export_protocol_and_missing_pdf_are_not_reported_as_success(tmp_path, monkeypatch):
    report, _calls, _out, _envs = _matrix(tmp_path, monkeypatch,
                                  malformed_export=("typst", "executive-light"),
                                  missing_pdf=("tikz", "executive-light"))

    cases = {(case["target"], case["preset"]): case for case in report["cases"]}
    assert cases[("typst", "executive-light")]["error"]["type"] == "protocol_error"
    assert cases[("tikz", "executive-light")]["error"]["type"] == "missing_artifact"


def test_export_and_compile_timeouts_have_phase_specific_types(tmp_path, monkeypatch):
    report, _calls, _out, _envs = _matrix(tmp_path, monkeypatch,
                                  export_timeout=("typst", "default"),
                                  compile_timeout=("tikz", "default"))

    cases = {(case["target"], case["preset"] or "default"): case for case in report["cases"]}
    assert cases[("typst", "default")]["error"]["type"] == "export_timeout"
    assert cases[("tikz", "default")]["error"]["type"] == "compile_timeout"


def test_rerun_refuses_existing_sources_and_pdfs_instead_of_reusing_stale_evidence(tmp_path, monkeypatch):
    first, _calls, _out, _envs = _matrix(tmp_path, monkeypatch)
    assert first["status"] == "complete"

    second, calls, _out, _envs = _matrix(tmp_path, monkeypatch)

    assert second["status"] == "failed"
    assert all(case["error"]["type"] == "output_exists" for case in second["cases"])
    assert all("-m" not in call for call in calls)
    assert all("--outdir" not in call for call in calls)
