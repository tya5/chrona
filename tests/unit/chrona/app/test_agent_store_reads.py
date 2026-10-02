"""The two Store read tools of the agent tool core (#812): one test per row of the design's threat model.

``render_review`` runs on a copy of the packaged example corpus (``chrona init --example halcyon-1``: a Store that renders
in seconds and declares ``integrity: optional``); ``compare_baseline`` runs on the small Store of
``tests/support/store_workspace.py``. Every scenario goes through ``call_tool`` over a ``WorkspaceScope`` and no SDK.
The command line is the oracle for the result bytes, and the tree of the workspace is the oracle for "nothing was written".
"""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from chrona.app import agent_tools
from chrona.app.agent_tools import InvalidArgumentsError, call_tool, registry_document, tool_specs
from chrona.app.agent_workspace import WorkspaceScope
from chrona.usecases.local_authoring import initialize_project
from tests.support.store_workspace import PROJECT, StoreWorkspace, run_cli

OUTPUT = {spec.name: Draft202012Validator(spec.output_schema) for spec in tool_specs()}
CODES = lambda result: [row["code"] for row in result.structured["diagnostics"]]  # noqa: E731
CONTEXT_REFERENCE = {
    "id": "halcyon-1-01-mission-brief", "kind": "render-context",
    "store": {"provider": "local", "identity": "halcyon-1-example"},
    "address": "contexts/01-mission-brief.yaml", "revision": {"token": "example-v4"},
}
BAD_PATHS = ["../outside.yaml", "/etc/passwd", "ctx\\a.yaml", "C:/x.yaml", "con.yaml", "a/../../x.yaml", ".", "a//b.yaml"]


def call(root: Path, name: str, arguments: dict, **options):
    result = call_tool(WorkspaceScope(root), name, arguments, **options)
    assert not list(OUTPUT[name].iter_errors(result.structured)), result.structured
    return result


def tree(root: Path) -> dict[str, bytes]:
    """Every file below ``root`` by relative path: equal before and after means nothing was written."""
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


def link(target: Path, destination: Path) -> None:
    try:
        destination.symlink_to(target, target_is_directory=target.is_dir())
    except (OSError, NotImplementedError):
        pytest.skip("this OS cannot create a symlink")


# --- the example corpus: render_review --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def corpus_template(tmp_path_factory) -> Path:
    return initialize_project(tmp_path_factory.mktemp("template") / "halcyon", example="halcyon-1")


@dataclass
class Corpus:
    root: Path

    @property
    def config(self) -> Path:
        return self.root / ".chrona" / "store.yaml"

    @property
    def context_file(self) -> Path:
        return self.root / ".chrona" / "store" / "revision-example-v4" / "contexts" / "01-mission-brief.yaml"

    def reference(self, name: str = "ctx.yaml", **changes) -> str:
        (self.root / name).write_text(yaml.safe_dump({**CONTEXT_REFERENCE, **changes}), encoding="utf-8")
        return name

    def set_config(self, name: str = "store.yaml", **changes) -> str:
        document = yaml.safe_load(self.config.read_text(encoding="utf-8"))
        document["stores"][0].update(changes)
        (self.root / name).write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
        return name


@pytest.fixture
def corpus(corpus_template, tmp_path) -> Corpus:
    root = tmp_path / "ws"
    shutil.copytree(corpus_template, root)
    return Corpus(root)


def test_a_context_in_a_store_renders_the_command_lines_bytes(corpus, monkeypatch, capsys):
    reference = corpus.reference()

    result = call(corpus.root, "render_review", {"contextReference": reference})
    code, _ = run_cli(monkeypatch, capsys, corpus.root, "render-review", "--context-reference", reference,
                      "--store-config", ".chrona/store.yaml", "--output", "cli.svg")
    expected = (corpus.root / "cli.svg").read_bytes()

    assert code == 0 and result.structured["status"] == "ok" and not result.is_error
    [attachment] = result.attachments
    assert (attachment.kind, attachment.data) == ("svg", expected)
    assert attachment.uri == f"chrona://render/{result.structured['contentIdentity']}.svg"
    assert result.structured["contentIdentity"] == agent_tools._identity(expected)
    assert (result.structured["format"], result.structured["byteLength"], result.structured["inlined"]) == ("svg", len(expected), True)
    assert result.structured["warnings"] and all(row["severity"] in {"warning", "info"} for row in result.structured["warnings"])


def test_inline_none_carries_only_the_structured_result(corpus):
    reference = corpus.reference()

    result = call(corpus.root, "render_review", {"contextReference": reference, "inline": "none"})

    assert result.attachments == () and result.structured["inlined"] is False and result.structured["byteLength"] > 0


def test_a_render_is_deterministic(corpus):
    reference = corpus.reference()

    first = call(corpus.root, "render_review", {"contextReference": reference, "inline": "none"})
    second = call(corpus.root, "render_review", {"contextReference": reference, "inline": "none"})

    assert first.structured == second.structured


def test_the_render_writes_nothing_and_needs_no_write_flag(corpus):
    reference = corpus.reference()
    before = tree(corpus.root)

    for options in ({}, {"allow_write": False}, {"allow_write": True}):
        result = call(corpus.root, "render_review", {"contextReference": reference}, **options)
        assert result.structured["status"] == "ok"
    assert tree(corpus.root) == before


def test_an_explicit_store_config_is_used(corpus):
    reference = corpus.reference()
    document = yaml.safe_load(corpus.config.read_text(encoding="utf-8"))
    document["stores"][0]["root"] = "../.chrona/store"
    (corpus.root / "elsewhere").mkdir()
    (corpus.root / "elsewhere" / "store.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")

    result = call(corpus.root, "render_review", {"contextReference": reference, "storeConfig": "elsewhere/store.yaml", "inline": "none"})

    assert result.structured["status"] == "ok"


# --- integrity --------------------------------------------------------------------------------------------------

def test_tampered_bytes_behind_a_pinned_reference_are_refused(corpus):
    pinned = agent_tools._identity(corpus.context_file.read_bytes())
    reference = corpus.reference(contentIdentity=pinned)
    assert call(corpus.root, "render_review", {"contextReference": reference, "inline": "none"}).structured["status"] == "ok"

    corpus.context_file.write_bytes(corpus.context_file.read_bytes() + b"\n# tampered\n")
    result = call(corpus.root, "render_review", {"contextReference": reference})

    assert (result.structured["status"], CODES(result)) == ("rejected", ["E_CONTENT_IDENTITY"]) and not result.attachments


def test_a_store_that_requires_an_identity_refuses_an_unpinned_reference(corpus):
    reference = corpus.reference()
    config = corpus.set_config(integrity="required")

    result = call(corpus.root, "render_review", {"contextReference": reference, "storeConfig": config})

    assert (result.structured["status"], CODES(result)) == ("rejected", ["E_STORE_REFERENCE"]) and not result.attachments
    # The same reference through the example's own configuration (integrity: optional) renders: only the setting differs.
    assert call(corpus.root, "render_review", {"contextReference": reference, "inline": "none"}).structured["status"] == "ok"


@pytest.mark.parametrize("override", [
    "allowMissingContentIdentity", "requireContentIdentity", "integrity", "snapshotRoot", "storeIdentity", "storeRoot",
    "output", "format", "allowWrite",
])
def test_no_argument_lowers_integrity_names_a_root_or_an_output(corpus, override):
    reference = corpus.reference()
    for tool, arguments in (("render_review", {"contextReference": reference}),
                            ("compare_baseline", {"baselineReference": reference, "candidateReference": reference})):
        with pytest.raises(InvalidArgumentsError):
            call_tool(WorkspaceScope(corpus.root), tool, {**arguments, override: False})


def test_a_reference_naming_an_undeclared_store_is_refused(corpus):
    reference = corpus.reference(store={"provider": "local", "identity": "someone-elses"})

    result = call(corpus.root, "render_review", {"contextReference": reference})

    assert (result.structured["status"], CODES(result)) == ("failed", ["E_STORE_CONFIG_REQUIRED"])


@pytest.mark.parametrize("text", ["- 1\n- 2\n", "", "just text\n"])
def test_a_reference_that_is_not_a_mapping_is_a_typed_failure(corpus, text):
    (corpus.root / "odd.yaml").write_text(text, encoding="utf-8")

    result = call(corpus.root, "render_review", {"contextReference": "odd.yaml"})

    assert result.structured["status"] == "failed" and CODES(result) == ["E_STORE_CONFIG_REQUIRED"]


def test_a_file_that_is_not_yaml_is_a_typed_failure_with_no_host_path(corpus):
    (corpus.root / "broken.yaml").write_text("a: [unclosed\n", encoding="utf-8")

    result = call(corpus.root, "render_review", {"contextReference": "broken.yaml"})

    assert (result.structured["status"], CODES(result)) == ("failed", ["E_INPUT_YAML"])
    assert str(corpus.root) not in result.text() and "Traceback" not in result.text()


def test_a_store_configuration_that_does_not_satisfy_its_schema_is_typed(corpus):
    reference = corpus.reference()
    (corpus.root / "badcfg.yaml").write_text("stores: 3\n", encoding="utf-8")

    result = call(corpus.root, "render_review", {"contextReference": reference, "storeConfig": "badcfg.yaml"})

    assert result.structured["status"] != "ok" and CODES(result) == ["E_OPERATIONAL_SCHEMA"]


def test_a_missing_input_is_a_typed_failure(corpus):
    result = call(corpus.root, "render_review", {"contextReference": "nope.yaml"})

    assert (result.structured["status"], CODES(result)) == ("failed", ["E_INPUT_IO"])
    assert result.structured["diagnostics"][0]["sourceRef"] == "/contextReference"


# --- path escapes, symlinks and the Store roots -----------------------------------------------------------------

@pytest.mark.parametrize("argument", ["contextReference", "storeConfig"])
@pytest.mark.parametrize("bad", BAD_PATHS)
def test_a_path_escape_in_a_render_input_is_refused_before_anything_is_read(corpus, argument, bad):
    arguments = {"contextReference": corpus.reference(), argument: bad}
    before = tree(corpus.root)

    result = call(corpus.root, "render_review", arguments)

    assert result.structured["status"] == "failed" and CODES(result) == ["E_MCP_PATH_SYNTAX"], bad
    assert result.structured["diagnostics"][0]["sourceRef"] == f"/{argument}"
    assert tree(corpus.root) == before


@pytest.mark.parametrize("argument", ["contextReference", "storeConfig"])
def test_a_symlink_leaving_the_workspace_is_refused_for_render_review(corpus, tmp_path, argument):
    reference = corpus.reference()
    outside = tmp_path / "outside.yaml"  # a valid copy of the real input, so only its location is wrong
    outside.write_bytes((corpus.config if argument == "storeConfig" else corpus.root / reference).read_bytes())
    link(outside, corpus.root / "linked.yaml")

    result = call(corpus.root, "render_review", {"contextReference": reference, argument: "linked.yaml"})

    assert result.structured["status"] == "failed" and CODES(result) == ["E_MCP_PATH_CONTAINMENT"]
    assert result.structured["diagnostics"][0]["sourceRef"] == f"/{argument}"


@pytest.mark.parametrize("shape", ["absolute", "dotdot", "symlink"])
def test_a_store_root_outside_the_workspace_is_refused_although_it_would_render(corpus, tmp_path, shape):
    outside = tmp_path / "outside-store"
    shutil.copytree(corpus.root / ".chrona" / "store", outside)
    if shape == "symlink":
        link(outside, corpus.root / "linked-store")
    root = {"absolute": str(outside), "dotdot": "../outside-store", "symlink": "linked-store"}[shape]
    reference = corpus.reference()
    config = corpus.set_config(root=root)
    before = tree(outside)

    result = call(corpus.root, "render_review", {"contextReference": reference, "storeConfig": config})

    assert result.structured["status"] == "failed" and CODES(result) == ["E_MCP_PATH_CONTAINMENT"]
    assert result.structured["diagnostics"][0]["sourceRef"] == "/storeConfig" and not result.attachments
    assert tree(outside) == before


def test_the_workspace_itself_is_not_a_valid_store_root(corpus):
    reference = corpus.reference()
    config = corpus.set_config(root=".")  # the configuration is in the workspace root, so the root is the workspace

    result = call(corpus.root, "render_review", {"contextReference": reference, "storeConfig": config})

    assert CODES(result) == ["E_MCP_PATH_CONTAINMENT"]


def test_an_address_inside_the_store_that_links_out_of_the_store_is_refused(corpus):
    reference = corpus.reference()
    copy = corpus.root / "elsewhere.yaml"
    copy.write_bytes(corpus.context_file.read_bytes())
    corpus.context_file.unlink()
    link(copy, corpus.context_file)

    result = call(corpus.root, "render_review", {"contextReference": reference})

    assert result.structured["status"] != "ok" and "E_STORE_REFERENCE" in result.text() and not result.attachments


# --- caps -------------------------------------------------------------------------------------------------------

def test_an_inline_svg_over_the_cap_is_a_typed_failure_and_inline_none_still_works(corpus, monkeypatch):
    reference = corpus.reference()
    monkeypatch.setattr(agent_tools, "MAX_INLINE_SVG_BYTES", 1000)

    large = call(corpus.root, "render_review", {"contextReference": reference})
    small = call(corpus.root, "render_review", {"contextReference": reference, "inline": "none"})

    assert (large.structured["status"], CODES(large), large.is_error) == ("failed", ["E_MCP_RESULT_TOO_LARGE"], True)
    assert "inline 'none'" in large.structured["diagnostics"][0]["message"] and not large.attachments
    assert small.structured["status"] == "ok"


class _Artifact:
    def __init__(self, content: bytes, media_type: str):
        self.content, self.media_type = content, media_type


def _stub_render(monkeypatch, kind: str, artifact: _Artifact):
    class Target:
        pass

    closure = Target()
    closure.context = Target()
    closure.context.target = Target()
    closure.context.target.kind = kind
    monkeypatch.setattr(agent_tools, "resolve_context_closure", lambda reference, reader: closure)
    rendered = Target()
    rendered.artifact = artifact
    monkeypatch.setattr(agent_tools, "render_context_closure", lambda closure_, root: rendered)
    monkeypatch.setattr(agent_tools, "warning_payloads", lambda value: [])


def test_a_png_target_is_an_image_and_a_pdf_target_is_not_inlined(corpus, monkeypatch):
    reference = corpus.reference()
    _stub_render(monkeypatch, "png", _Artifact(b"\x89PNG-bytes", "image/png"))
    png = call(corpus.root, "render_review", {"contextReference": reference})
    _stub_render(monkeypatch, "pdf", _Artifact(b"%PDF-bytes", "application/pdf"))
    pdf = call(corpus.root, "render_review", {"contextReference": reference})

    assert [(item.kind, item.media_type, item.data) for item in png.attachments] == [("image", "image/png", b"\x89PNG-bytes")]
    assert (png.structured["format"], png.structured["inlined"]) == ("png", True)
    assert pdf.attachments == () and (pdf.structured["format"], pdf.structured["inlined"]) == ("pdf", False)
    assert pdf.structured["contentIdentity"] == agent_tools._identity(b"%PDF-bytes") and pdf.structured["byteLength"] == 10


def test_an_inline_png_over_the_cap_is_a_typed_failure(corpus, monkeypatch):
    reference = corpus.reference()
    _stub_render(monkeypatch, "png", _Artifact(b"x" * 100, "image/png"))
    monkeypatch.setattr(agent_tools, "MAX_INLINE_PNG_BYTES", 10)

    result = call(corpus.root, "render_review", {"contextReference": reference})

    assert (result.structured["status"], CODES(result)) == ("failed", ["E_MCP_RESULT_TOO_LARGE"]) and not result.attachments


# --- compare_baseline -------------------------------------------------------------------------------------------

@pytest.fixture
def work(tmp_path) -> StoreWorkspace:
    return StoreWorkspace(tmp_path / "ws")


def write_reference(work: StoreWorkspace, name: str, reference: dict) -> str:
    (work.root / name).write_text(yaml.safe_dump(reference), encoding="utf-8")
    return name


def baseline_and_candidate(work: StoreWorkspace) -> dict[str, str]:
    """Capture ``project-r1`` as baseline ``q2`` through the engine, add a changed Project, and write both references."""
    captured = call(work.root, "apply_command", {"command": work.write_command("capture.yaml", work.capture("cap-1", "q2"))},
                    allow_write=True)
    assert captured.structured["status"] == "ok"
    changed = {**PROJECT, "objects": {**PROJECT["objects"], "gate": {
        "type": "milestone", "schedule": {"mode": "fixed-point", "at": "2026-02-01"}}}}
    candidate = work.write_resource("project-r2", "project.yaml", changed, "project", "p")
    return {"baselineReference": write_reference(work, "baseline.yaml", captured.structured["automationResult"]["resultTarget"]),
            "candidateReference": write_reference(work, "candidate.yaml", candidate)}


def test_a_baseline_is_compared_with_a_candidate_and_equals_the_command_lines_result(work, monkeypatch, capsys):
    arguments = baseline_and_candidate(work)

    result = call(work.root, "compare_baseline", arguments)
    code, _ = run_cli(monkeypatch, capsys, work.root, "baseline-compare", "--baseline-reference", arguments["baselineReference"],
                      "--candidate-reference", arguments["candidateReference"], "--store-config", ".chrona/store.yaml",
                      "--result", "result.json")

    assert code == 0 and result.structured["status"] == "ok" and not result.is_error
    automation = result.structured["automationResult"]
    assert automation["operation"] == "baseline-compare"
    assert automation["comparison"]["changes"] == [{"kind": "object", "id": "gate", "change": "added"}]
    assert automation["comparison"]["afterSchedule"]["gate"] == {"at": "2026-02-01"}  # a date travels as ISO text
    assert json.dumps(automation, sort_keys=True) == (work.root / "result.json").read_text(encoding="utf-8")


def test_the_comparison_writes_nothing_and_needs_no_write_flag(work):
    arguments = baseline_and_candidate(work)
    before = tree(work.root)

    for options in ({}, {"allow_write": False}):
        assert call(work.root, "compare_baseline", arguments, **options).structured["status"] == "ok"
    assert tree(work.root) == before


def test_a_reference_that_is_not_a_baseline_is_rejected_with_the_engines_result(work):
    arguments = baseline_and_candidate(work)
    arguments["baselineReference"] = arguments["candidateReference"]  # a project, not a snapshot-ref

    result = call(work.root, "compare_baseline", arguments)

    assert (result.structured["status"], CODES(result), result.is_error) == ("rejected", ["E_BASELINE_REFERENCE"], False)
    row = result.structured["diagnostics"][0]
    assert row["sourceRef"] == "/" and row["message"] == result.structured["automationResult"]["diagnostics"][0]["message"]


def test_a_baseline_whose_snapshot_is_missing_is_rejected(work):
    arguments = baseline_and_candidate(work)
    (work.store / "snapshots" / "q2.yaml").unlink()

    result = call(work.root, "compare_baseline", arguments)

    assert result.structured["status"] == "rejected" and CODES(result) == ["E_BASELINE_REFERENCE"]


def test_tampered_bytes_behind_the_candidate_are_refused(work):
    arguments = baseline_and_candidate(work)
    candidate = work.store / "revision-project-r2" / "project.yaml"
    candidate.write_bytes(candidate.read_bytes() + b"\n# tampered\n")

    result = call(work.root, "compare_baseline", arguments)

    assert (result.structured["status"], CODES(result)) == ("rejected", ["E_BASELINE_REFERENCE"])
    message = result.structured["diagnostics"][0]["message"]
    assert "contentIdentity" in message and "stored bytes" in message  # the engine's message names the mismatch
    assert "comparison" not in result.structured["automationResult"]


def test_a_required_store_refuses_an_unpinned_candidate(work):
    arguments = baseline_and_candidate(work)
    document = yaml.safe_load((work.root / arguments["candidateReference"]).read_text(encoding="utf-8"))
    del document["contentIdentity"]
    write_reference(work, "unpinned.yaml", document)

    result = call(work.root, "compare_baseline", {**arguments, "candidateReference": "unpinned.yaml"})

    assert (result.structured["status"], CODES(result)) == ("rejected", ["E_BASELINE_REFERENCE"])
    assert "has no contentIdentity" in result.structured["diagnostics"][0]["message"]


@pytest.mark.parametrize("argument", ["baselineReference", "candidateReference", "storeConfig"])
@pytest.mark.parametrize("bad", BAD_PATHS)
def test_a_path_escape_in_a_compare_input_is_refused(work, argument, bad):
    arguments = {**baseline_and_candidate(work), argument: bad}
    before = tree(work.root)

    result = call(work.root, "compare_baseline", arguments)

    assert result.structured["status"] == "failed" and CODES(result) == ["E_MCP_PATH_SYNTAX"], bad
    assert tree(work.root) == before


@pytest.mark.parametrize("argument", ["baselineReference", "candidateReference", "storeConfig"])
def test_a_symlink_leaving_the_workspace_is_refused_for_compare_baseline(work, tmp_path, argument):
    arguments = baseline_and_candidate(work)
    source = work.config if argument == "storeConfig" else work.root / arguments[argument]
    outside = tmp_path / "outside.yaml"
    outside.write_bytes(source.read_bytes())
    link(outside, work.root / "linked.yaml")

    result = call(work.root, "compare_baseline", {**arguments, argument: "linked.yaml"})

    assert result.structured["status"] == "failed" and CODES(result) == ["E_MCP_PATH_CONTAINMENT"]
    assert result.structured["diagnostics"][0]["sourceRef"] == f"/{argument}"


@pytest.mark.parametrize("shape", ["absolute", "dotdot", "symlink"])
def test_a_store_root_outside_the_workspace_is_refused_for_compare_baseline(work, tmp_path, shape):
    arguments = baseline_and_candidate(work)
    outside = tmp_path / "outside-store"
    shutil.copytree(work.store, outside)
    if shape == "symlink":
        link(outside, work.root / "linked-store")
    root = {"absolute": str(outside), "dotdot": "../outside-store", "symlink": "linked-store"}[shape]
    (work.root / "outside.yaml").write_text(yaml.safe_dump({"version": "chrona/store-config/v0.1", "stores": [
        {"provider": "local", "identity": "test", "root": root}]}), encoding="utf-8")

    result = call(work.root, "compare_baseline", {**arguments, "storeConfig": "outside.yaml"})

    assert result.structured["status"] == "failed" and CODES(result) == ["E_MCP_PATH_CONTAINMENT"]
    assert result.structured["diagnostics"][0]["sourceRef"] == "/storeConfig"


def test_a_comparison_over_the_cap_is_a_typed_failure(work, monkeypatch):
    arguments = baseline_and_candidate(work)
    monkeypatch.setattr(agent_tools, "MAX_COMPARISON_BYTES", 100)

    result = call(work.root, "compare_baseline", arguments)

    assert (result.structured["status"], CODES(result), result.is_error) == ("failed", ["E_MCP_RESULT_TOO_LARGE"], True)
    assert "automationResult" not in result.structured


def test_no_comparison_result_carries_a_host_path(work):
    arguments = baseline_and_candidate(work)
    host = str(work.root.resolve())
    document = {"id": host + "/looks-like-a-path", "kind": "project", "store": {"provider": "local", "identity": "test"},
                "address": "project.yaml", "revision": {"token": "project-r2"}}
    arguments["baselineReference"] = write_reference(work, "hostile.yaml", document)

    result = call(work.root, "compare_baseline", arguments)

    assert result.structured["status"] == "rejected" and host not in result.text() and str(work.root) not in result.text()


# --- the registry -----------------------------------------------------------------------------------------------

def test_both_tools_are_read_only_and_listed_whatever_the_write_flag_is():
    specs = {spec.name: spec for spec in tool_specs()}
    document = {tool["name"]: tool for tool in registry_document()["tools"]}

    for name in ("render_review", "compare_baseline"):
        assert specs[name].mutating is False
        assert document[name]["annotations"] == {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True,
                                                 "openWorldHint": False}
        assert "read-only" in specs[name].description and "--allow-write" in specs[name].description
    assert registry_document()["toolSet"] == "chrona/agent-tools/v0.4"
