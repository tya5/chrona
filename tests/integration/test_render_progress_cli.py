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
    assert "chrona: routing [route-label-baseline] 0/1" in text
    assert "chrona: routing [route-label-baseline] 1/1" in text
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

    master, slave = pty.openpty()
    chunks = []
    errors = []

    def drain():
        while True:
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
            result = subprocess.run(_command(project, tmp_path / "tty.svg"), stdout=subprocess.PIPE,
                                    stderr=sink, check=True)
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


@pytest.mark.parametrize("failure", [OSError("terminal unavailable"), ValueError("closed stream")])
def test_terminal_probe_failure_disables_only_feedback(monkeypatch, failure):
    from chrona.app import cli

    class FailedTerminal:
        def isatty(self):
            raise failure

    monkeypatch.setattr(cli.sys, "stderr", FailedTerminal())
    assert cli._draft_render_progress(False) is None
