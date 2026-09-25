import importlib.util
from pathlib import Path
import subprocess
import sys


def _runner():
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    module_spec = importlib.util.spec_from_file_location("test_run_conformance_module", root / "conformance/run_conformance.py")
    assert module_spec and module_spec.loader
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    return module


def test_runner_reports_every_independent_failure_and_declared_skip():
    runner = _runner()
    calls = []
    outcomes = {("first",): 1, ("second",): 0}

    def execute(argv):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, outcomes[argv], stdout="out", stderr="err")

    ticks = iter((0.0, 0.01, 0.02, 0.04))
    results = runner.run_checks((
        runner.CheckSpec("first", ("first",)),
        runner.CheckSpec("second", ("second",)),
        runner.CheckSpec("dependent", ("dependent",), ("first",)),
    ), run_process=execute, clock=lambda: next(ticks))

    assert calls == [("first",), ("second",)]
    assert [(result.check_id, result.status) for result in results] == [
        ("first", "FAIL"), ("second", "PASS"), ("dependent", "SKIP"),
    ]
    assert results[-1].skip_reason == "prerequisite=first"
    report = runner.render_results(results)
    assert report.index("== first ==") < report.index("== second ==") < report.index("== dependent ==")
    assert "dependent | SKIP | 0ms | prerequisite=first" in report


def test_runner_bounds_captured_output_without_hiding_failure_status():
    runner = _runner()
    payload = "x" * (runner.OUTPUT_LIMIT + 10)

    result = runner.run_checks((runner.CheckSpec("large", ("large",)),),
                               run_process=lambda argv: subprocess.CompletedProcess(argv, 2, stdout=payload, stderr=""),
                               clock=iter((0.0, 0.01)).__next__)[0]

    assert result.status == "FAIL"
    assert "output truncated" in result.stdout
    assert len(result.stdout) < len(payload)


def test_scene_perceptibility_runs_once_after_generated_evidence_integrity():
    runner = _runner()
    ids = [item.check_id for item in runner.CHECKS]

    assert ids.count("scene-perceptibility") == 1
    assert ids.index("example-inventory") < ids.index("scene-perceptibility") < ids.index("diagnostic-inventory")


def test_literal_issue_acceptance_gate_runs_once_after_documented_commands():
    runner = _runner()
    ids = [item.check_id for item in runner.CHECKS]

    assert ids.count("literal-issue-acceptance") == 1
    assert ids.index("documented-commands") < ids.index("literal-issue-acceptance") < ids.index("core-conformance")


def test_runner_configures_aggregate_report_transport_as_utf8():
    runner = _runner()
    calls = []

    class Stream:
        def reconfigure(self, **kwargs):
            calls.append(kwargs)

    runner.configure_stdout(Stream())

    assert calls == [{"encoding": "utf-8"}]
