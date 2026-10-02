"""The real server over real stdio (#142, I142-S4): a child process started as `python -m chrona mcp`.

Needs the optional ``chrona[mcp]`` extra; without it the module is skipped with that reason (the CI lane that installs
the extra runs it). Two kinds of client talk to the child: the SDK client (``stdio_client`` and ``ClientSession``,
which work on every ``mcp`` 2.x release) for the four tools, and a hand-written JSON-RPC client over explicit pipes,
which proves that standard output carries protocol frames only and that the server ends when its input does.

Process handling is portable: ``subprocess`` with explicit pipes and a reader thread (no ``select`` on a pipe, no
signals), and the child is always killed in a ``finally``; the SDK client shuts its own child down.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

import pytest

pytest.importorskip("mcp.server", reason="the optional chrona[mcp] extra is not installed")

import anyio  # noqa: E402  (an SDK dependency, present whenever the extra is)
from mcp import ClientSession, StdioServerParameters, types  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402
from mcp.shared.exceptions import MCPError  # noqa: E402

from chrona.app.agent_tools import registry_document  # noqa: E402
from chrona.app.cli import main  # noqa: E402
from tests.support.store_workspace import StoreWorkspace  # noqa: E402

REPO = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
LAUNCH = (REPO / "skills" / "chrona" / "examples" / "launch.yaml").read_text(encoding="utf-8")
CYCLE = """\
version: timeline/v0.7
project: {id: cyc, title: Cycle}
objects:
  a: {type: task, title: A, schedule: {mode: scheduled, amount: 3d}}
  b: {type: task, title: B, schedule: {mode: scheduled, amount: 3d}}
relations:
  - {id: r1, type: dependency, from: {object: a, endpoint: end}, to: {object: b, endpoint: start}, lag: 0d}
  - {id: r2, type: dependency, from: {object: b, endpoint: end}, to: {object: a, endpoint: start}, lag: 0d}
"""
SESSION_SECONDS = 180


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    root.mkdir()
    (root / "launch.yaml").write_text(LAUNCH, encoding="utf-8")
    (root / "cycle.yaml").write_text(CYCLE, encoding="utf-8")
    (root / "計画 2026.yaml").write_text(LAUNCH, encoding="utf-8")
    (root / "broken.yaml").write_text("a: [\n", encoding="utf-8")
    return root


def child_environment() -> dict[str, str]:
    """What the child needs beyond the SDK's safe default: the import path of a source checkout, and UTF-8."""
    env = {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    for name in ("PYTHONPATH", "VIRTUAL_ENV"):
        if name in os.environ:
            env[name] = os.environ[name]
    return env


def server_parameters(workspace: Path, cwd: Path | None = None, allow_write: bool = False) -> StdioServerParameters:
    options = ["--allow-write"] if allow_write else []
    return StdioServerParameters(command=sys.executable, args=["-m", "chrona", "mcp", "--workspace", str(workspace), *options],
                                 env=child_environment(), cwd=cwd)


def session(workspace: Path, scenario, cwd: Path | None = None, allow_write: bool = False):
    """Run ``scenario(session)`` against a freshly started server process."""
    async def go():
        with anyio.fail_after(SESSION_SECONDS):
            async with stdio_client(server_parameters(workspace, cwd, allow_write)) as (read, write):
                async with ClientSession(read, write) as client:
                    init = await client.initialize()
                    return await scenario(client, init)

    return anyio.run(go)


def cli(monkeypatch, capsys, cwd: Path, *arguments: str) -> tuple[int, str]:
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(sys, "argv", ["chrona", *arguments])
    code = 0
    try:
        main()
    except SystemExit as error:
        code = error.code if isinstance(error.code, int) else 0
    return code, capsys.readouterr().out


def sha(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def test_the_tool_list_over_stdio_is_the_registry(workspace):
    async def scenario(client, init):
        return init, await client.list_tools()

    init, listed = session(workspace, scenario)
    assert init.server_info.name == "chrona" and "schedule_project" in init.instructions
    document = registry_document()["tools"]
    assert [tool.name for tool in listed.tools] == [tool["name"] for tool in document]
    for tool, expected in zip(listed.tools, document, strict=True):
        assert tool.input_schema == expected["inputSchema"] and tool.output_schema == expected["outputSchema"]


def test_the_four_tools_over_stdio_equal_the_command_line(workspace, tmp_path, monkeypatch, capsys):
    async def scenario(client, init):
        return {
            "validate": await client.call_tool("validate_project", {"project": "launch.yaml"}),
            "schedule": await client.call_tool("schedule_project", {"project": "launch.yaml"}),
            "svg": await client.call_tool("render_draft", {"project": "launch.yaml", "inline": "svg"}),
            "png": await client.call_tool("render_draft", {"project": "launch.yaml"}),
            "png_file": await client.call_tool("render_draft", {"project": "launch.yaml", "format": "png", "inline": "none"}),
            "presets": await client.call_tool("list_presets", {}),
            "unicode": await client.call_tool("validate_project", {"project": "計画 2026.yaml"}),
        }

    results = session(workspace, scenario, cwd=tmp_path)  # the server's working directory is not the workspace
    assert not any(result.is_error for result in results.values())

    rc, out = cli(monkeypatch, capsys, workspace, "schedule", "launch.yaml")
    expected = json.loads(out)
    got = results["schedule"].structured_content
    assert rc == 0 and got["placements"] == expected["placements"] and got["analysis"] == expected["analysis"]

    rc, out = cli(monkeypatch, capsys, workspace, "preset", "list")
    assert rc == 0 and results["presets"].structured_content["presets"] == json.loads(out)["presets"]

    assert results["validate"].structured_content["status"] == "ok"
    assert results["unicode"].structured_content["status"] == "ok"
    assert results["validate"].structured_content["projectIdentity"] == sha((workspace / "launch.yaml").read_bytes())

    assert cli(monkeypatch, capsys, workspace, "render", "launch.yaml", "--output", "out.svg")[0] == 0
    assert cli(monkeypatch, capsys, workspace, "render", "launch.yaml", "--output", "out.png")[0] == 0
    svg, png = (workspace / "out.svg").read_bytes(), (workspace / "out.png").read_bytes()

    block = results["svg"].content[1]
    assert isinstance(block, types.EmbeddedResource) and block.resource.text.encode("utf-8") == svg
    assert results["svg"].structured_content["contentIdentity"] == sha(svg)

    image = results["png"].content[1]
    assert isinstance(image, types.ImageContent) and base64.b64decode(image.data) == png
    assert results["png"].structured_content["contentIdentity"] == sha(svg)  # the default artifact is the SVG
    assert results["png_file"].structured_content["contentIdentity"] == sha(png)
    assert len(results["png_file"].content) == 1


def test_results_over_stdio_are_deterministic(workspace, tmp_path):
    async def scenario(client, init):
        texts = []
        for _ in range(2):
            for name, arguments in [("schedule_project", {"project": "launch.yaml"}),
                                    ("validate_project", {"project": "cycle.yaml"}),
                                    ("render_draft", {"project": "launch.yaml", "viewport": "300x300", "inline": "none"})]:
                texts.append((await client.call_tool(name, arguments)).content[0].text)
        return texts

    first = session(workspace, scenario)
    second = session(workspace, scenario, cwd=tmp_path)
    assert first[:3] == first[3:] == second[:3] == second[3:]
    assert str(workspace) not in "".join(first) and str(workspace.resolve()) not in "".join(first)


def test_status_and_error_flag_over_stdio(workspace):
    async def scenario(client, init):
        return [await client.call_tool("schedule_project", {"project": "cycle.yaml"}),
                await client.call_tool("validate_project", {"project": "../launch.yaml"}),
                await client.call_tool("validate_project", {"project": "/etc/passwd"}),
                await client.call_tool("validate_project", {"project": "missing.yaml"}),
                await client.call_tool("render_draft", {"project": "launch.yaml", "preset": "nope"}),
                await client.call_tool("validate_project", {"project": "cycle.yaml"})]

    cycle, escape, absolute, missing, preset, validated = session(workspace, scenario)
    assert (cycle.structured_content["status"], cycle.is_error) == ("rejected", False)
    assert {item["code"] for item in cycle.structured_content["diagnostics"]} == {"E_UNSUPPORTED_CYCLE"}
    assert validated.structured_content["status"] == "rejected" and not validated.is_error  # #780: validate names the cycle too
    assert validated.structured_content["diagnostics"] == cycle.structured_content["diagnostics"]
    for result, code in ((escape, "E_MCP_PATH_SYNTAX"), (absolute, "E_MCP_PATH_SYNTAX"), (missing, "E_INPUT_IO")):
        assert (result.structured_content["status"], result.is_error) == ("failed", True)
        assert result.structured_content["diagnostics"][0]["code"] == code
    assert (preset.structured_content["status"], preset.is_error) == ("rejected", False)
    assert preset.structured_content["diagnostics"][0]["code"] == "E_BUILTIN_PRESET_UNKNOWN"


def test_a_symlink_out_of_the_workspace_and_a_host_path_in_a_message_over_stdio(workspace, tmp_path):
    outside = tmp_path / "outside.yaml"
    outside.write_text(LAUNCH, encoding="utf-8")
    try:
        (workspace / "link.yaml").symlink_to(outside)
    except (OSError, NotImplementedError):
        link = False
    else:
        link = True

    async def scenario(client, init):
        escaped = await client.call_tool("validate_project", {"project": "link.yaml"}) if link else None
        return escaped, await client.call_tool("validate_project", {"project": "broken.yaml"})

    escaped, broken = session(workspace, scenario)
    if link:
        assert escaped.is_error and escaped.structured_content["diagnostics"][0]["code"] == "E_MCP_PATH_CONTAINMENT"
        assert str(tmp_path) not in escaped.content[0].text
    text = broken.content[0].text
    assert broken.structured_content["diagnostics"][0]["code"] == "E_INPUT_YAML" and broken.is_error
    # PyYAML names the file it was reading; the server removes the workspace from that text.
    assert 'in \\"broken.yaml\\"' in text
    assert str(workspace) not in text and str(workspace.resolve()) not in text and workspace.as_posix() not in text


def test_protocol_errors_and_resources_over_stdio(workspace):
    async def scenario(client, init):
        errors = []
        for name, arguments in [("apply_command", {}), ("validate_project", {}), ("render_draft", {"project": "launch.yaml", "format": "pdf"})]:
            with pytest.raises(MCPError) as raised:
                await client.call_tool(name, arguments)
            errors.append(raised.value.code)
        authoring = await client.read_resource("chrona://guide/authoring")
        diagnostics = await client.read_resource("chrona://guide/diagnostics")
        listed = await client.list_resources()
        return errors, authoring, diagnostics, listed

    errors, authoring, diagnostics, listed = session(workspace, scenario)
    assert errors == [types.INVALID_PARAMS] * 3
    assert [resource.uri for resource in listed.resources] == ["chrona://guide/authoring", "chrona://guide/diagnostics"]
    assert "chrona schedule" in authoring.contents[0].text and "E_UNSUPPORTED_CYCLE" in diagnostics.contents[0].text


# --- the Store command tools over stdio (#813) ---------------------------------------------------------------------

def test_without_allow_write_the_writer_is_refused_over_stdio_and_the_preview_works(tmp_path):
    work = StoreWorkspace(tmp_path / "ws")
    path = work.write_command("c1.yaml", work.intake("c1", work.batch("b1")))
    before = work.snapshot()

    async def scenario(client, init):
        return (await client.call_tool("apply_command", {"command": path}),
                await client.call_tool("check_command", {"command": path}), init.instructions)

    applied, checked, instructions = session(work.root, scenario)

    assert applied.is_error and [row["code"] for row in applied.structured_content["diagnostics"]] == ["E_MCP_WRITE_DISABLED"]
    assert not checked.is_error and checked.structured_content["status"] == "ok"
    assert "Writes are off" in instructions
    assert work.snapshot() == before


def test_with_allow_write_an_intake_and_a_capture_are_applied_and_equal_the_command_line(tmp_path, monkeypatch, capsys):
    tool_side, cli_side = StoreWorkspace(tmp_path / "tool"), StoreWorkspace(tmp_path / "cli")
    for side in (tool_side, cli_side):
        side.write_command("intake.yaml", side.intake("c1", side.batch("b1")))
        side.write_command("capture.yaml", side.capture("capture-1", "q2"))

    async def scenario(client, init):
        return {"instructions": init.instructions, "tools": await client.list_tools(),
                "intake": await client.call_tool("apply_command", {"command": "commands/intake.yaml"}),
                "replay": await client.call_tool("apply_command", {"command": "commands/intake.yaml"}),
                "capture": await client.call_tool("apply_command", {"command": "commands/capture.yaml"})}

    results = session(tool_side.root, scenario, cwd=tmp_path, allow_write=True)

    assert "Writes are on" in results["instructions"] and "no approval step" in results["instructions"]
    annotations = {tool.name: tool.annotations for tool in results["tools"].tools}
    assert (annotations["apply_command"].read_only_hint, annotations["apply_command"].destructive_hint) == (False, True)
    assert annotations["check_command"].read_only_hint is True
    for name in ("intake", "capture"):
        assert not results[name].is_error and results[name].structured_content["status"] == "ok"
    assert results["replay"].structured_content["automationResult"]["replayed"] is True

    for name in ("intake", "capture"):
        code, _ = cli(monkeypatch, capsys, cli_side.root, "command-apply", "--command", f"commands/{name}.yaml",
                      "--store-config", ".chrona/store.yaml", "--result", f"{name}.json")
        assert code == 0
        assert json.dumps(results[name].structured_content["automationResult"], sort_keys=True) == (
            cli_side.root / f"{name}.json").read_text(encoding="utf-8")
    assert tool_side.snapshot() == cli_side.snapshot() and tool_side.tip()["counter"] == 2


def test_stale_replayed_and_overwriting_commands_are_refused_over_stdio_and_nothing_is_overwritten(tmp_path):
    work = StoreWorkspace(tmp_path / "ws")
    first = work.write_command("c1.yaml", work.intake("c1", work.batch("b1")))
    stale = work.write_command("c2.yaml", work.intake("c2", work.batch("b2", finish="2026-05-05", key="43")))
    reuse = work.write_command("c1-other.yaml", work.intake("c1", work.batch("b3", finish="2026-06-06", key="44")))
    capture = work.write_command("cap1.yaml", work.capture("cap-1", "q2"))
    capture_again = work.write_command("cap2.yaml", work.capture("cap-2", "q2"))

    async def scenario(client, init):
        names = ("first", "stale", "reuse", "capture", "again")
        files = (first, stale, reuse, capture, capture_again)
        return {name: await client.call_tool("apply_command", {"command": path})
                for name, path in zip(names, files, strict=True)}

    results = session(work.root, scenario, allow_write=True)

    def code(name: str) -> list[str]:
        return [row["code"] for row in results[name].structured_content["diagnostics"]]

    assert results["first"].structured_content["status"] == "ok"
    assert (results["stale"].structured_content["status"], code("stale")) == ("rejected", ["E_AUTOMATION_TARGET_CLOSURE"])
    assert (results["reuse"].structured_content["status"], code("reuse")) == ("rejected", ["E_COMMAND_ID_REUSE"])
    assert results["capture"].structured_content["status"] == "ok"
    assert (results["again"].structured_content["status"], code("again")) == ("rejected", ["E_BASELINE_EXISTS"])
    assert not any(result.is_error for result in results.values())
    assert work.tip()["counter"] == 2  # only the first intake advanced the tip


def test_path_escapes_a_symlink_and_an_outside_store_are_refused_over_stdio(tmp_path):
    work = StoreWorkspace(tmp_path / "ws")
    path = work.write_command("c1.yaml", work.intake("c1", work.batch("b1")))
    outside = tmp_path / "outside-store"
    outside.mkdir()
    (work.root / "outside.yaml").write_text(yaml_store_config(str(outside)), encoding="utf-8")
    (tmp_path / "config-elsewhere.yaml").write_bytes(work.config.read_bytes())  # a valid configuration, in the wrong place
    try:
        (work.root / "linked.yaml").symlink_to(tmp_path / "config-elsewhere.yaml")
        linked = True
    except (OSError, NotImplementedError):
        linked = False
    before = work.snapshot()

    async def scenario(client, init):
        calls = [("../c1.yaml", None), ("/etc/passwd", None), (path, "../outside.yaml"), (path, "outside.yaml")]
        if linked:
            calls.append((path, "linked.yaml"))
        return [await client.call_tool("apply_command", {"command": command, **({"storeConfig": config} if config else {})})
                for command, config in calls]

    results = session(work.root, scenario, allow_write=True)

    codes = [result.structured_content["diagnostics"][0]["code"] for result in results]
    assert codes[:2] == ["E_MCP_PATH_SYNTAX"] * 2 and codes[2] == "E_MCP_PATH_SYNTAX"  # ".." is a syntax failure
    assert codes[3] == "E_MCP_PATH_CONTAINMENT" and (not linked or codes[4] == "E_MCP_PATH_CONTAINMENT")
    assert all(result.is_error for result in results)
    assert not list(outside.iterdir()) and work.snapshot() == before


def yaml_store_config(root: str) -> str:
    return ("version: chrona/store-config/v0.1\nstores:\n"
            f"  - {{provider: local, identity: test, root: {json.dumps(root)}, integrity: required}}\n")


# --- standard output carries protocol frames only, and the server ends with its input -----------------------------

class Child:
    """A server process with explicit pipes: lines of standard output arrive through a queue."""

    def __init__(self, workspace: Path):
        env = {**os.environ, **child_environment()}
        self.process = subprocess.Popen(
            [sys.executable, "-m", "chrona", "mcp", "--workspace", str(workspace)], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, cwd=workspace.parent)
        self.lines: queue.Queue[bytes | None] = queue.Queue()
        self.seen: list[bytes] = []
        self.stderr = bytearray()
        threading.Thread(target=self._pump_stdout, daemon=True).start()
        threading.Thread(target=self._pump_stderr, daemon=True).start()

    def _pump_stdout(self) -> None:
        for line in iter(self.process.stdout.readline, b""):
            self.lines.put(line)
        self.lines.put(None)

    def _pump_stderr(self) -> None:
        for chunk in iter(lambda: self.process.stderr.read(1024), b""):
            self.stderr.extend(chunk)

    def send(self, message: dict) -> None:
        self.process.stdin.write((json.dumps(message) + "\n").encode("utf-8"))
        self.process.stdin.flush()

    def receive(self) -> dict:
        line = self.lines.get(timeout=120)
        assert line is not None, "the server closed standard output early"
        self.seen.append(line)
        return json.loads(line.decode("utf-8"))

    def finish(self) -> int:
        """Close the input, expect the server to end by itself, and kill it if it does not."""
        try:
            self.process.stdin.close()
            return self.process.wait(timeout=30)
        finally:
            if self.process.poll() is None:
                self.process.kill()
                self.process.wait()


def test_standard_output_holds_only_json_rpc_frames_and_the_server_ends_with_its_input(workspace):
    child = Child(workspace)
    try:
        child.send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "e2e", "version": "0"}}})
        assert child.receive()["result"]["serverInfo"]["name"] == "chrona"
        child.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        child.send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        assert [tool["name"] for tool in child.receive()["result"]["tools"]] == [
            "validate_project", "schedule_project", "render_draft", "list_presets", "render_review", "compare_baseline",
            "check_command", "apply_command"]
        child.send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                    "params": {"name": "render_draft", "arguments": {"project": "launch.yaml"}}})
        reply = child.receive()
        assert reply["id"] == 3 and reply["result"]["isError"] is False
        assert [block["type"] for block in reply["result"]["content"]] == ["text", "image"]
        child.send({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "nope", "arguments": {}}})
        assert child.receive()["error"]["code"] == types.INVALID_PARAMS
        code = child.finish()
    finally:
        if child.process.poll() is None:
            child.process.kill()
            child.process.wait()
    assert code == 0
    assert child.lines.get(timeout=30) is None  # the stream ended
    for line in child.seen:
        frame = json.loads(line.decode("utf-8"))
        assert frame["jsonrpc"] == "2.0" and ("result" in frame or "error" in frame or "method" in frame)
        assert line.endswith(b"\n") and b"\r\r" not in line
    assert b"Traceback" not in bytes(child.stderr)


def test_a_filesystem_root_workspace_ends_the_command_before_serving(tmp_path):
    done = subprocess.run([sys.executable, "-m", "chrona", "mcp", "--workspace", str(Path(tmp_path.anchor))],
                          capture_output=True, text=True, encoding="utf-8", timeout=60, check=False, cwd=tmp_path,
                          stdin=subprocess.DEVNULL, env={**os.environ, **child_environment()})
    assert done.returncode == 2
    report = json.loads(done.stdout)
    assert report["status"] == "failed" and report["diagnostics"][0]["code"] == "E_MCP_WORKSPACE_TOO_BROAD"


# --- the Store read tools over stdio (#812) -----------------------------------------------------------------------

CONTEXT_REFERENCE = (
    "id: halcyon-1-01-mission-brief\nkind: render-context\nstore: {provider: local, identity: halcyon-1-example}\n"
    "address: contexts/01-mission-brief.yaml\nrevision: {token: example-v4}\n")


def tree(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


def corpus(tmp_path: Path) -> Path:
    from chrona.usecases.local_authoring import initialize_project

    root = initialize_project(tmp_path / "corpus", example="halcyon-1")
    (root / "ctx.yaml").write_text(CONTEXT_REFERENCE, encoding="utf-8")
    return root


def compare_workspace(tmp_path: Path) -> tuple[StoreWorkspace, dict[str, str]]:
    """A Store with a captured baseline ``q2`` of ``project-r1`` and a changed candidate Project; both references on disk."""
    import yaml

    from chrona.operational.resources import parse_command
    from chrona.operational.store_commands import open_store_reader, run_store_command
    from tests.support.store_workspace import PROJECT

    work = StoreWorkspace(tmp_path / "ws")
    captured = run_store_command("command-apply", parse_command(yaml.safe_dump(work.capture("cap-1", "q2"))),
                                 open_store_reader(work.config))
    assert captured["status"] == "accepted"
    changed = {**PROJECT, "objects": {**PROJECT["objects"], "gate": {
        "type": "milestone", "schedule": {"mode": "fixed-point", "at": "2026-02-01"}}}}
    candidate = work.write_resource("project-r2", "project.yaml", changed, "project", "p")
    (work.root / "baseline.yaml").write_text(yaml.safe_dump(captured["resultTarget"]), encoding="utf-8")
    (work.root / "candidate.yaml").write_text(yaml.safe_dump(candidate), encoding="utf-8")
    return work, {"baselineReference": "baseline.yaml", "candidateReference": "candidate.yaml"}


def test_render_review_over_stdio_equals_the_command_line_and_needs_no_write_flag(tmp_path, monkeypatch, capsys):
    root = corpus(tmp_path)
    before = tree(root)

    async def scenario(client, init):
        return {"inline": await client.call_tool("render_review", {"contextReference": "ctx.yaml"}),
                "none": await client.call_tool("render_review", {"contextReference": "ctx.yaml", "inline": "none"}),
                "tools": await client.list_tools(), "instructions": init.instructions}

    results = session(root, scenario, cwd=tmp_path)  # no --allow-write; the server's working directory is not the workspace
    after_tools = tree(root)
    code, _ = cli(monkeypatch, capsys, root, "render-review", "--context-reference", "ctx.yaml", "--store-config",
                  ".chrona/store.yaml", "--output", "cli.svg")
    expected = (root / "cli.svg").read_bytes()

    assert code == 0 and after_tools == before  # the tools wrote nothing
    inline, none = results["inline"], results["none"]
    assert not inline.is_error and inline.structured_content["status"] == "ok" and "Writes are off" in results["instructions"]
    assert [type(block) for block in inline.content] == [types.TextContent, types.EmbeddedResource]
    assert inline.content[1].resource.text.encode("utf-8") == expected
    assert inline.structured_content["contentIdentity"] == sha(expected) == none.structured_content["contentIdentity"]
    assert (inline.structured_content["byteLength"], inline.structured_content["format"]) == (len(expected), "svg")
    assert len(none.content) == 1 and none.structured_content["inlined"] is False
    annotations = {tool.name: tool.annotations for tool in results["tools"].tools}
    for name in ("render_review", "compare_baseline"):
        assert (annotations[name].read_only_hint, annotations[name].destructive_hint) == (True, False)


def test_compare_baseline_over_stdio_equals_the_command_line_and_writes_nothing(tmp_path, monkeypatch, capsys):
    work, arguments = compare_workspace(tmp_path)

    async def scenario(client, init):
        return {"ok": await client.call_tool("compare_baseline", arguments),
                "not_a_baseline": await client.call_tool("compare_baseline", {**arguments, "baselineReference": "candidate.yaml"})}

    before = tree(work.root)
    results = session(work.root, scenario, cwd=tmp_path)
    after = tree(work.root)
    code, _ = cli(monkeypatch, capsys, work.root, "baseline-compare", "--baseline-reference", "baseline.yaml",
                  "--candidate-reference", "candidate.yaml", "--store-config", ".chrona/store.yaml", "--result", "result.json")

    assert code == 0 and after == before
    ok = results["ok"]
    assert not ok.is_error and ok.structured_content["status"] == "ok"
    assert ok.structured_content["automationResult"]["comparison"]["changes"] == [{"kind": "object", "id": "gate", "change": "added"}]
    assert json.dumps(ok.structured_content["automationResult"], sort_keys=True) == (work.root / "result.json").read_text(encoding="utf-8")
    refused = results["not_a_baseline"]
    assert not refused.is_error and refused.structured_content["status"] == "rejected"
    assert [row["code"] for row in refused.structured_content["diagnostics"]] == ["E_BASELINE_REFERENCE"]


def test_store_escapes_a_symlink_and_tampered_bytes_are_refused_over_stdio_and_nothing_is_written(tmp_path):
    root = corpus(tmp_path)
    outside = tmp_path / "outside-store"
    import shutil

    shutil.copytree(root / ".chrona" / "store", outside)  # a Store that would render, in the wrong place
    (root / "outside.yaml").write_text(
        "version: chrona/store-config/v0.1\nstores:\n"
        f"  - {{provider: local, identity: halcyon-1-example, root: {json.dumps(str(outside))}, integrity: optional}}\n", encoding="utf-8")
    (tmp_path / "ctx-elsewhere.yaml").write_text(CONTEXT_REFERENCE, encoding="utf-8")
    try:
        (root / "linked.yaml").symlink_to(tmp_path / "ctx-elsewhere.yaml")
        linked = True
    except (OSError, NotImplementedError):
        linked = False
    pinned = root / "pinned.yaml"
    context_file = root / ".chrona" / "store" / "revision-example-v4" / "contexts" / "01-mission-brief.yaml"
    pinned.write_text(CONTEXT_REFERENCE + f"contentIdentity: {sha(context_file.read_bytes())}\n", encoding="utf-8")
    context_file.write_bytes(context_file.read_bytes() + b"\n# tampered\n")
    before, outside_before = tree(root), tree(outside)

    async def scenario(client, init):
        calls = [{"contextReference": "../ctx.yaml"}, {"contextReference": "/etc/passwd"},
                 {"contextReference": "ctx.yaml", "storeConfig": "outside.yaml"},
                 {"contextReference": "pinned.yaml"}]
        if linked:
            calls.append({"contextReference": "linked.yaml"})
        return [await client.call_tool("render_review", arguments) for arguments in calls]

    results = session(root, scenario)

    codes = [result.structured_content["diagnostics"][0]["code"] for result in results]
    assert codes[:2] == ["E_MCP_PATH_SYNTAX"] * 2 and codes[2] == "E_MCP_PATH_CONTAINMENT"
    assert codes[3] == "E_CONTENT_IDENTITY" and (not linked or codes[4] == "E_MCP_PATH_CONTAINMENT")
    assert [result.is_error for result in results][:3] == [True, True, True]
    assert not any(type(block) is types.EmbeddedResource for result in results for block in result.content)
    assert tree(root) == before and tree(outside) == outside_before
