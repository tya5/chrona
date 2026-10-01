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


def server_parameters(workspace: Path, cwd: Path | None = None) -> StdioServerParameters:
    return StdioServerParameters(command=sys.executable, args=["-m", "chrona", "mcp", "--workspace", str(workspace)],
                                 env=child_environment(), cwd=cwd)


def session(workspace: Path, scenario, cwd: Path | None = None):
    """Run ``scenario(session)`` against a freshly started server process."""
    async def go():
        with anyio.fail_after(SESSION_SECONDS):
            async with stdio_client(server_parameters(workspace, cwd)) as (read, write):
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
            "validate_project", "schedule_project", "render_draft", "list_presets"]
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
