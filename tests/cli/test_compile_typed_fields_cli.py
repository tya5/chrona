"""Typed terse plans retain resource context through each command adapter."""
from __future__ import annotations

import json
import io
import sys
from pathlib import Path

import pytest
import yaml

from chrona.app import cli

PACKAGE = {
    "version": "chrona/profile/v0.3", "packageId": "demo-package",
    "requires": {"projectFormat": "timeline/v0.7"},
    "profiles": {"work": {"extends": "task", "fields": {
        "risk": {"type": "enum", "enumValues": ["low", "high"]},
    }}},
}
REVISION = "git:" + "0123456789abcdef" * 2 + "01234567"


def _write(root, package_name="package.yaml", risk="high"):
    (root / package_name).write_text(yaml.safe_dump(PACKAGE), encoding="utf-8")
    plan = root / "plan.chrona"
    plan.write_text(f'project demo extension demo-package "{package_name}" {REVISION}\n'
                    f'a "Build" task profile work 2026-11-02..2026-11-09 risk={risk}\n', encoding="utf-8")
    return plan


def _run(monkeypatch, capsys, *arguments):
    monkeypatch.setattr(sys, "argv", ["chrona", *map(str, arguments)])
    status = 0
    try:
        cli.main()
    except SystemExit as error:
        status = error.code or 0
    streams = capsys.readouterr()
    return status, streams.out, streams.err


def test_compile_output_uses_destination_directory_before_writing(tmp_path, monkeypatch, capsys):
    source = tmp_path / "source"
    source.mkdir()
    plan = _write(source)
    destination = tmp_path / "output"
    destination.mkdir()
    output = destination / "project.yaml"
    status, out, err = _run(monkeypatch, capsys, "compile", plan, "-o", output)
    assert status == 1 and not output.exists() and not err
    assert json.loads(out)["diagnostics"][0]["code"] == "E_EXTENSION_UNRESOLVED"
    (destination / "package.yaml").write_bytes((source / "package.yaml").read_bytes())
    assert _run(monkeypatch, capsys, "compile", plan, "-o", output) == (0, "", "")
    assert yaml.safe_load(output.read_bytes())["objects"]["a"]["fields"] == {"risk": "high"}


def test_compile_stdout_resolves_beside_source_not_cwd(tmp_path, monkeypatch, capsys):
    source = tmp_path / "source"
    source.mkdir()
    plan = _write(source)
    monkeypatch.chdir(tmp_path)
    status, out, err = _run(monkeypatch, capsys, "compile", plan)
    assert status == 0 and not err
    assert yaml.safe_load(out)["objects"]["a"]["fields"] == {"risk": "high"}


def test_compile_stdin_uses_cwd_without_output_and_destination_with_output(tmp_path, monkeypatch, capsys):
    plan = _write(tmp_path)
    data = plan.read_bytes()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(data), encoding="utf-8"))
    status, out, err = _run(monkeypatch, capsys, "compile", "-")
    assert status == 0 and not err and yaml.safe_load(out)["objects"]["a"]["type"] == "work"
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(data), encoding="utf-8"))
    status, out, err = _run(monkeypatch, capsys, "compile", "-", "-o", elsewhere / "project.yaml")
    assert status == 1 and not err and not (elsewhere / "project.yaml").exists()
    assert json.loads(out)["diagnostics"][0]["code"] == "E_EXTENSION_UNRESOLVED"


@pytest.mark.parametrize("command", ["validate", "schedule"])
def test_plan_checks_do_not_reopen_the_source_package(tmp_path, monkeypatch, capsys, command):
    plan = _write(tmp_path)
    original = Path.read_bytes
    reads = []

    def tracked(path):
        if path == tmp_path / "package.yaml":
            reads.append(path)
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", tracked)
    status, out, err = _run(monkeypatch, capsys, command, plan)
    assert status == 0 and not err and json.loads(out)["status"] == "ok"
    assert len(reads) == 1


@pytest.mark.parametrize("render_fails", [False, True])
@pytest.mark.parametrize("package_name", ["package.yaml", "project.yaml"])
def test_render_stages_acquired_bytes_and_cleans_up(tmp_path, monkeypatch, capsys, render_fails, package_name):
    plan = _write(tmp_path, package_name)
    original = cli._compile_plan_argument
    expected = (tmp_path / package_name).read_bytes()
    observed = []

    def compile_then_mutate(path):
        result = original(path)
        (tmp_path / package_name).write_bytes(b"not the validated package")
        return result

    def inspect_render(args):
        project = Path(args.project)
        observed.append(project.parent)
        assert project.name != package_name
        assert (project.parent / package_name).read_bytes() == expected
        assert yaml.safe_load(project.read_bytes())["objects"]["a"]["type"] == "work"
        if render_fails:
            raise RuntimeError("synthetic adapter failure")

    monkeypatch.setattr(cli, "_compile_plan_argument", compile_then_mutate)
    monkeypatch.setattr(cli, "_run_draft_render", inspect_render)
    _run(monkeypatch, capsys, "render", plan, "-o", tmp_path / "out.svg")
    assert len(observed) == 1 and not observed[0].exists()


def test_typed_compile_rejection_leaves_stdout_empty(tmp_path, monkeypatch, capsys):
    plan = _write(tmp_path, risk="extreme")
    status, out, err = _run(monkeypatch, capsys, "compile", plan)
    assert status == 1 and out == ""
    diagnostic = json.loads(err)["diagnostics"][0]
    assert diagnostic["code"] == "E_PROFILE_FIELD_ENUM" and diagnostic["sourceRange"]["line"] == 2
