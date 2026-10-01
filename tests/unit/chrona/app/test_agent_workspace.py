"""Workspace scoping of the agent tools (#142, I142-S3): every path an agent names stays inside one root.

The syntax and containment verdicts come from the shared Store address guard, which decides by
``PurePosixPath`` and ``PureWindowsPath`` and never the host flavour, so the refusals mean the same on
every OS. The host-dependent vectors (a symlink, a FIFO) skip where the OS cannot create them.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from chrona.app.agent_workspace import MAX_INPUT_BYTES, WorkspaceScope
from chrona.usecases.failure_report import StableFailure, report_failure


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    (root / "plans").mkdir(parents=True)
    (root / "plans" / "project.yaml").write_text("a: 1\n", encoding="utf-8")
    return root


def refusal(scope: WorkspaceScope, value: object, pointer: str = "/project") -> StableFailure:
    with pytest.raises(StableFailure) as raised:
        scope.resolve_path(value, pointer)
    return raised.value


def test_a_file_inside_the_workspace_resolves_to_its_real_path(workspace):
    scope = WorkspaceScope(workspace)
    assert scope.resolve_path("plans/project.yaml", "/project") == (workspace / "plans" / "project.yaml").resolve()


@pytest.mark.parametrize("value", ["計画.yaml", "my plan.yaml", "plans/年次 計画.yaml"])
def test_non_ascii_and_spaced_file_names_are_accepted(workspace, value):
    target = workspace / value
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("a: 1\n", encoding="utf-8")
    assert WorkspaceScope(workspace).resolve_path(value, "/project") == target.resolve()


@pytest.mark.parametrize("value", [
    "../outside.yaml", "plans/../../outside.yaml", "plans/..", "..", ".", "./project.yaml",
    "/etc/passwd", "/plans/project.yaml", "//host/share/x.yaml",
    "C:/x.yaml", "C:x.yaml", "c:\\x.yaml", "\\\\server\\share\\x.yaml", "plans\\project.yaml", "a:b.yaml",
    "plans//project.yaml", "plans/", "a\x00b.yaml", "a\nb.yaml", "a\tb.yaml", "a\x7fb.yaml", "...", "plans/.../x.yaml",
    "", 7, None,
])
def test_a_syntactically_unsafe_path_is_refused_before_the_filesystem(workspace, value):
    failure = refusal(WorkspaceScope(workspace), value, "/actual")
    assert (failure.code, failure.component, failure.source_ref, failure.exit_code) == (
        "E_MCP_PATH_SYNTAX", "mcp", "/actual", 2)
    report = report_failure(failure)
    assert report.status == "failed"


@pytest.mark.parametrize("name", [
    "CON", "con", "CON.yaml", "con.txt.yaml", "PRN.yaml", "AUX", "NUL.yaml", "nul", "COM1.yaml", "com9", "LPT1", "lpt9.yaml",
    "COM\u00b9.yaml", "CONIN$", "con .yaml",
])
def test_a_windows_reserved_device_name_is_refused_on_every_os(workspace, name):
    scope = WorkspaceScope(workspace)
    for value in (name, f"plans/{name}"):
        failure = refusal(scope, value)
        assert failure.code == "E_MCP_PATH_SYNTAX" and "device" in failure.message


@pytest.mark.parametrize("name", ["console.yaml", "comet.yaml", "CONFIG.yaml", "COM10.yaml", "auxiliary.yaml", "nullable.yaml"])
def test_a_name_that_only_starts_like_a_device_is_accepted(workspace, name):
    (workspace / name).write_text("a: 1\n", encoding="utf-8")
    assert WorkspaceScope(workspace).resolve_path(name, "/project").name == name


def _symlink(link: Path, target: Path, directory: bool = False) -> None:
    try:
        link.symlink_to(target, target_is_directory=directory)
    except (OSError, NotImplementedError):
        pytest.skip("the OS refuses to create symbolic links here")


def test_a_symlinked_file_that_leaves_the_workspace_is_refused(workspace, tmp_path):
    outside = tmp_path / "outside.yaml"
    outside.write_text("secret: 1\n", encoding="utf-8")
    _symlink(workspace / "plans" / "link.yaml", outside)
    failure = refusal(WorkspaceScope(workspace), "plans/link.yaml")
    assert failure.code == "E_MCP_PATH_CONTAINMENT" and failure.source_ref == "/project"
    assert str(tmp_path) not in failure.message


def test_a_symlinked_directory_that_leaves_the_workspace_is_refused(workspace, tmp_path):
    (tmp_path / "elsewhere").mkdir()
    (tmp_path / "elsewhere" / "p.yaml").write_text("secret: 1\n", encoding="utf-8")
    _symlink(workspace / "escape", tmp_path / "elsewhere", directory=True)
    assert refusal(WorkspaceScope(workspace), "escape/p.yaml").code == "E_MCP_PATH_CONTAINMENT"


def test_a_symlink_that_stays_inside_the_workspace_is_followed(workspace):
    _symlink(workspace / "alias.yaml", workspace / "plans" / "project.yaml")
    scope = WorkspaceScope(workspace)
    assert scope.resolve_path("alias.yaml", "/project") == (workspace / "plans" / "project.yaml").resolve()


def test_a_symlinked_workspace_root_is_resolved_once(workspace, tmp_path):
    _symlink(tmp_path / "alias", workspace, directory=True)
    scope = WorkspaceScope(tmp_path / "alias")
    assert scope.resolve_path("plans/project.yaml", "/project") == (workspace / "plans" / "project.yaml").resolve()


@pytest.mark.parametrize("value", ["plans/absent.yaml", "plans", "absent/x.yaml"])
def test_a_missing_path_or_a_directory_is_an_input_error_like_the_cli(workspace, value):
    failure = refusal(WorkspaceScope(workspace), value)
    assert (failure.code, failure.exit_code) == ("E_INPUT_IO", 2)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFOs exist only on POSIX; the regular-file rule is the same check")
def test_a_fifo_is_never_opened(workspace):
    os.mkfifo(workspace / "pipe.yaml")
    assert refusal(WorkspaceScope(workspace), "pipe.yaml").code == "E_INPUT_IO"


def test_an_oversize_file_is_refused_and_the_limit_itself_is_accepted(workspace):
    (workspace / "limit.yaml").write_bytes(b"#" * MAX_INPUT_BYTES)
    (workspace / "over.yaml").write_bytes(b"#" * (MAX_INPUT_BYTES + 1))
    scope = WorkspaceScope(workspace)
    assert scope.resolve_path("limit.yaml", "/project").name == "limit.yaml"
    failure = refusal(scope, "over.yaml")
    assert (failure.code, failure.exit_code) == ("E_MCP_INPUT_TOO_LARGE", 2)


def test_a_filesystem_root_is_refused_as_a_workspace(tmp_path):
    with pytest.raises(StableFailure) as raised:
        WorkspaceScope(Path(tmp_path.anchor))
    assert (raised.value.code, raised.value.exit_code) == ("E_MCP_WORKSPACE_TOO_BROAD", 2)
    assert "--workspace" in raised.value.message


def test_a_workspace_that_is_not_a_directory_is_refused(tmp_path):
    (tmp_path / "file").write_text("x", encoding="utf-8")
    for candidate in (tmp_path / "absent", tmp_path / "file"):
        with pytest.raises(StableFailure) as raised:
            WorkspaceScope(candidate)
        assert raised.value.code == "E_INPUT_IO"


def test_a_relative_workspace_is_resolved_once_against_the_start_directory(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    scope = WorkspaceScope(".")
    monkeypatch.chdir(workspace.parent)
    assert scope.resolve_path("plans/project.yaml", "/project") == (workspace / "plans" / "project.yaml").resolve()


# --- the scrubber --------------------------------------------------------------------------------------------

def test_the_scrubber_removes_the_workspace_in_given_and_resolved_forms(workspace, tmp_path):
    scope = WorkspaceScope(workspace)
    resolved = workspace.resolve()
    for root in {str(workspace), workspace.as_posix(), str(resolved), resolved.as_posix()}:
        scrubbed = scope.scrub(f'cannot read "{root}{os.sep}plans{os.sep}project.yaml" in {root}')
        assert root not in scrubbed
        assert "plans" in scrubbed and "project.yaml" in scrubbed


def test_the_scrubber_keeps_a_relative_path_after_the_workspace_prefix(workspace):
    scope = WorkspaceScope(workspace)
    assert scope.scrub(f"in \"{workspace.resolve().as_posix()}/plans/project.yaml\", line 2") == 'in "plans/project.yaml", line 2'


def test_the_scrubber_replaces_other_host_paths(workspace, tmp_path):
    scope = WorkspaceScope(workspace)
    for text in [str(Path.cwd()), str(Path.home()), str(tmp_path), os.path.join(tempfile.gettempdir(), "x", "y.yaml")]:
        scrubbed = scope.scrub(f"failed at {text}")
        assert "<path>" in scrubbed and text not in scrubbed


@pytest.mark.parametrize("text", [
    r"C:\Users\someone\plans\p.yaml", "C:/Users/someone/p.yaml", r"\\fileserver\share\p.yaml",
    "/Users/someone/p.yaml", "/home/someone/p.yaml", "/private/var/folders/x/p.yaml", "/tmp/p.yaml", "/opt/chrona/x.py",
])
def test_the_scrubber_replaces_any_absolute_host_path_shape(workspace, text):
    scrubbed = WorkspaceScope(workspace).scrub(f"error in {text} at line 3")
    assert scrubbed == "error in <path> at line 3"


@pytest.mark.parametrize("text", [
    "/objects/design/schedule", "/", "/root/children/1", "plans/project.yaml", "end must follow start", "expected 5/7 items",
    "/objects/tmp/title", "/objects/home/title", "see /tmp2/x and /usrx/y", "a/Users/b", "/objects/var",
])
def test_the_scrubber_leaves_pointers_and_relative_paths_alone(workspace, text):
    assert WorkspaceScope(workspace).scrub(text) == text


def test_a_host_directory_matches_only_as_a_whole_path_even_inside_a_pointer(workspace, monkeypatch):
    # On Linux the temporary directory is /tmp, which is also an object id in a pointer.
    monkeypatch.setattr(tempfile, "gettempdir", lambda: "/tmp")
    scope = WorkspaceScope(workspace)
    assert scope.scrub("bad value at /objects/tmp/title") == "bad value at /objects/tmp/title"
    assert scope.scrub("cannot open /tmp/p.yaml now") == "cannot open <path> now"
    assert scope.scrub("cannot open /tmp2/p.yaml now") == "cannot open /tmp2/p.yaml now"


def test_a_relative_workspace_argument_does_not_erase_ordinary_words(workspace, monkeypatch):
    monkeypatch.chdir(workspace.parent)
    scope = WorkspaceScope(workspace.name)
    assert scope.scrub(f"the {workspace.name} plans in {workspace.name}") == f"the {workspace.name} plans in {workspace.name}"
    assert scope.scrub(workspace.resolve().as_posix() + "/plans/p.yaml") == "plans/p.yaml"


def test_a_filesystem_root_as_the_start_directory_does_not_mangle_messages(workspace, monkeypatch):
    monkeypatch.setattr(Path, "cwd", classmethod(lambda cls: Path(workspace.anchor)))
    scope = WorkspaceScope(workspace)
    assert scope.scrub("a/b and c/d") == "a/b and c/d"


def test_scrub_value_reaches_nested_strings_and_keeps_keys(workspace):
    scope = WorkspaceScope(workspace)
    home = str(Path.home())
    value = {"a": [f"x {home}", {"b": f"y {home}"}], "n": 3, home: "kept"}
    scrubbed = scope.scrub_value(value)
    assert home not in str(scrubbed["a"]) and scrubbed["n"] == 3 and scrubbed[home] == "kept"
