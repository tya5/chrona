"""Actual CLI terminal feedback is a side channel, not artifact authority."""
import errno
import json
import os
import subprocess
import sys
import threading

import pytest


PROJECT = """version: timeline/v0.7
project: {id: feedback, title: Feedback}
objects:
  a: {type: task, title: A, schedule: {mode: fixed-span, start: '2027-01-04', end: '2027-01-05'}}
  b: {type: task, title: B, schedule: {mode: fixed-span, start: '2027-01-06', end: '2027-01-07'}}
relations:
  - id: ab
    type: dependency
    lag: 0d
    from: {object: a, endpoint: end}
    to: {object: b, endpoint: start}
"""


def _command(project, output, *flags, legacy=False):
    program = "from chrona.app import cli; "
    if legacy:
        program += "cli._draft_render_progress = lambda enabled: None; "
    program += "cli.main()"
    return [sys.executable, "-c", program, "render", str(project), "-o", str(output), *flags]


@pytest.fixture
def project(tmp_path):
    source = tmp_path / "project.yaml"
    source.write_text(PROJECT, encoding="utf-8")
    return source


def _assert_phases(stderr):
    text = stderr.decode()
    assert "chrona: schedule" in text
    assert "chrona: layout" in text
    assert "chrona: routing [route-label-reserved] 0/1" in text
    assert "chrona: routing [route-label-reserved] 1/1" in text
    assert "chrona: output" in text


def test_nonterminal_matches_unobserved_cli_and_explicit_progress_keeps_stdout_and_svg(project, tmp_path):
    legacy, quiet, verbose = [tmp_path / f"{name}.svg" for name in ("legacy", "quiet", "verbose")]
    baseline = subprocess.run(_command(project, legacy, legacy=True), capture_output=True, check=True)
    plain = subprocess.run(_command(project, quiet), capture_output=True, check=True)
    observed = subprocess.run(_command(project, verbose, "--progress"), capture_output=True, check=True)
    assert plain.stdout == baseline.stdout == observed.stdout
    assert plain.stderr == baseline.stderr == b""
    assert json.loads(plain.stdout)["status"] == "ok"
    assert legacy.read_bytes() == quiet.read_bytes() == verbose.read_bytes()
    _assert_phases(observed.stderr)


@pytest.mark.skipif(os.name != "posix", reason="real POSIX pseudo-terminal; quiet/explicit tests run everywhere")
def test_terminal_stderr_enables_progress_without_a_flag(project, tmp_path):
    import pty
    import select

    master, slave = pty.openpty()
    chunks = []
    errors = []
    finished = threading.Event()

    def drain():
        while True:
            if not select.select([master], [], [], 0.1)[0]:
                if finished.is_set():
                    break
                continue
            try:
                chunk = os.read(master, 4096)
            except OSError as error:
                if error.errno != errno.EIO:
                    errors.append(error)
                break
            if not chunk:
                break
            chunks.append(chunk)

    # Drain while the slave remains open: macOS discards unread PTY bytes
    # when the last slave descriptor closes.
    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    try:
        with os.fdopen(slave, "wb") as sink:
            try:
                result = subprocess.run(_command(project, tmp_path / "tty.svg"), stdout=subprocess.PIPE,
                                        stderr=sink, check=True)
            finally:
                # Keep the parent slave open until every pending byte is read.
                finished.set()
                reader.join()
    finally:
        os.close(master)
    assert not errors
    assert json.loads(result.stdout)["status"] == "ok"
    _assert_phases(b"".join(chunks))


def test_render_help_declares_progress_flag():
    result = subprocess.run([sys.executable, "-c", "from chrona.app.cli import main; main()",
                             "render", "--help"], capture_output=True, check=True)
    assert b"--progress" in result.stdout
    assert b"stderr" in result.stdout
    assert b"--relations" in result.stdout


def test_relation_override_omits_primitives_without_suppression_or_route_search(project, tmp_path):
    scenes = {}
    reports = {}
    stderr = {}
    for name, flags in (("default", ()), ("semantic", ("--relations", "semantic")),
                        ("none", ("--relations", "none", "--progress"))):
        scene = tmp_path / f"{name}.scene.json"
        result = subprocess.run(_command(project, tmp_path / f"{name}.svg", "--emit-scene", str(scene), *flags),
                                capture_output=True, check=True)
        scenes[name] = json.loads(scene.read_bytes())
        reports[name] = json.loads(result.stdout)
        stderr[name] = result.stderr
    assert scenes["semantic"] == scenes["default"]
    primitives = lambda scene: [p for surface in scene["surfaces"] for p in surface["primitives"]]
    assert any(p["id"].startswith("relation:") for p in primitives(scenes["default"]))
    assert not any(p["id"].startswith("relation:") for p in primitives(scenes["none"]))
    assert not any(w["code"] == "W_LAYOUT_RELATION_SUPPRESSED" for w in reports["none"]["warnings"])
    assert b"0/0" in stderr["none"]
    assert b"0/1" not in stderr["none"]
    assert project.read_text() == PROJECT


@pytest.mark.parametrize("declaration", ["none", {"mode": "none", "overflow": "suppress"}])
def test_semantic_override_enables_an_authored_hidden_view_without_editing_it(project, tmp_path, declaration):
    import yaml
    from chrona.resources import default_preset_root

    document = yaml.safe_load((default_preset_root() / "bundles/editorial-readable-default/view.yaml").read_bytes())
    document["body"]["visibility"]["relations"] = declaration
    view = tmp_path / "view.yaml"
    view.write_text(yaml.safe_dump(document, sort_keys=False))
    authored = view.read_bytes()
    for mode in (None, "semantic"):
        scene = tmp_path / f"{mode}.json"
        flags = ("--relations", mode) if mode else ()
        subprocess.run(_command(project, tmp_path / f"{mode}.svg", "--view", str(view),
                                "--emit-scene", str(scene), *flags), capture_output=True, check=True)
        primitives = [p for surface in json.loads(scene.read_bytes())["surfaces"] for p in surface["primitives"]]
        assert any(p["id"].startswith("relation:") for p in primitives) == (mode == "semantic")
    assert view.read_bytes() == authored


@pytest.mark.parametrize("failure", [OSError("terminal unavailable"), ValueError("closed stream")])
def test_terminal_probe_failure_disables_only_feedback(monkeypatch, failure):
    from chrona.app import cli

    class FailedTerminal:
        def isatty(self):
            raise failure

    monkeypatch.setattr(cli.sys, "stderr", FailedTerminal())
    assert cli._draft_render_progress(False) is None


@pytest.mark.parametrize("row_count, exceeds_limit", [(2, False), (120, True)])
def test_actual_cli_default_reports_its_declared_limit_and_emitted_row_count(tmp_path, row_count, exceeds_limit):
    import yaml

    project = tmp_path / "tall.yaml"
    project.write_text(yaml.safe_dump({
        "version": "timeline/v0.7", "project": {"id": "tall", "title": "Tall review"},
        "objects": {f"t{i}": {"type": "task", "title": f"Task {i}", "schedule": {
            "mode": "fixed-span", "start": "2027-01-04", "end": "2027-01-18"}} for i in range(row_count)},
        "relations": [],
    }))
    scene = tmp_path / "tall.scene.json"
    result = subprocess.run(_command(project, tmp_path / "tall.svg", "--relations", "none",
                                    "--emit-scene", str(scene)), capture_output=True, check=True)
    report = json.loads(result.stdout)
    warnings = [w for w in report["warnings"] if w["code"] == "W_LAYOUT_AUTO_BLOCK_SIZE"]
    surface = json.loads(scene.read_bytes())["surfaces"][0]
    assert len(surface["rows"]) == row_count
    assert (surface["canvasBounds"]["blockSize"] > 3600) is exceeds_limit
    assert len(warnings) == int(exceeds_limit)
    if exceeds_limit:
        assert warnings[0]["maxBlockSize"] == 3600
        assert warnings[0]["actualBlockSize"] == surface["canvasBounds"]["blockSize"]
        assert warnings[0]["rowCount"] == row_count
    assert result.stderr == b""
