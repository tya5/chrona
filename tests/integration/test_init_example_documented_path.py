"""The documented `init --example` to `render-review` path, run as the guide writes it (#727).

The commands and the reference YAML are read from `docs/guides/first-project.md`, so the guide cannot drift from what runs.
Nothing here depends on the host OS: decisions come from the config data, exit status and diagnostic codes.
"""
import json
import re
import sys
from pathlib import Path

import pytest
import yaml

from chrona.app.cli import main
from chrona.operational.store_config import ConfiguredStoreReader, load_store_config
from chrona.usecases.local_authoring import initialize_project
from tools.check_documented_commands import discover

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
GUIDE = Path("docs/guides/first-project.md")
KEY = ("local", "halcyon-1-example")


def _documented(subcommand: str) -> tuple[str, ...]:
    commands = [c.tokens for c in discover(ROOT) if c.path == GUIDE and c.tokens[1] == subcommand and (subcommand != "init" or "--example" in c.tokens)]
    assert len(commands) == 1, commands
    return commands[0]


def _documented_reference() -> tuple[str, str]:
    text = (ROOT / GUIDE).read_text(encoding="utf-8")
    match = re.search(r"cat > (?P<path>\S+) <<'YAML'\n(?P<body>.*?)\nYAML\n", text, re.S)
    assert match is not None
    return match["path"], match["body"] + "\n"


def _run(monkeypatch, tokens: tuple[str, ...], extra: tuple[str, ...] = ()) -> None:
    monkeypatch.setattr(sys, "argv", [*tokens, *extra])
    main()


def _init_example_and_reference(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.chdir(tmp_path)
    _run(monkeypatch, _documented("init"))
    path, body = _documented_reference()
    (tmp_path / path).write_text(body, encoding="utf-8")
    return tmp_path / path


def _flag(tokens: tuple[str, ...], name: str) -> str:
    return tokens[tokens.index(name) + 1]


def test_documented_path_renders_an_example_context_with_the_init_store_config(tmp_path, monkeypatch):
    _init_example_and_reference(tmp_path, monkeypatch)
    render = _documented("render-review")
    assert "--allow-missing-content-identity" not in render  # the guide needs no opt-out flag for the example Store

    _run(monkeypatch, render)

    assert (tmp_path / _flag(render, "--output")).read_bytes().startswith(b"<svg")
    config_path = tmp_path / _flag(render, "--store-config")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert [entry["integrity"] for entry in config["stores"]] == ["optional"]  # written explicitly by init --example
    assert "ADR-0030" in config_path.read_text(encoding="utf-8")  # with the reason beside it
    assert load_store_config(str(config_path)).integrity == {KEY: "optional"}


def test_the_same_example_store_marked_required_refuses_the_unpinned_reference(tmp_path, monkeypatch, capsys):
    _init_example_and_reference(tmp_path, monkeypatch)
    render = _documented("render-review")
    config_path = tmp_path / _flag(render, "--store-config")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["stores"][0]["integrity"] = "required"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    capsys.readouterr()

    with pytest.raises(SystemExit) as refused:
        _run(monkeypatch, render)

    assert refused.value.code != 0
    assert "E_CONTENT_IDENTITY_REQUIRED" in capsys.readouterr().out
    assert not (tmp_path / _flag(render, "--output")).exists()
    # the per-call opt-out still works on a required Store
    _run(monkeypatch, render, ("--allow-missing-content-identity",))
    assert (tmp_path / _flag(render, "--output")).read_bytes().startswith(b"<svg")


def test_example_init_writes_optional_explicitly_and_minimal_init_writes_no_config(tmp_path):
    example = initialize_project(tmp_path / "example", example="halcyon-1")
    minimal = initialize_project(tmp_path / "minimal")

    config = example / ".chrona" / "store.yaml"
    assert yaml.safe_load(config.read_text(encoding="utf-8"))["stores"][0]["integrity"] == "optional"
    assert "ADR-0030" in config.read_text(encoding="utf-8")
    assert not (minimal / ".chrona" / "store.yaml").exists()  # no Store config, so nothing opts out of the required default


def test_a_store_config_that_omits_integrity_is_required(tmp_path):
    reader = ConfiguredStoreReader({"stores": [{"provider": "local", "identity": "s", "root": str(tmp_path)}]})

    assert reader.integrity == {("local", "s"): "required"}
    with pytest.raises(ValueError, match="E_CONTENT_IDENTITY_REQUIRED"):
        reader.read({"store": {"provider": "local", "identity": "s"}, "kind": "render-context", "address": "a.yaml", "revision": {"token": "r"}})


def test_render_review_needs_a_store_config_or_both_snapshot_flags(tmp_path, monkeypatch, capsys):
    reference = _init_example_and_reference(tmp_path, monkeypatch)
    capsys.readouterr()

    with pytest.raises(SystemExit):
        _run(monkeypatch, ("chrona", "render-review", "--context-reference", str(reference), "--output", str(tmp_path / "x.svg")))

    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["diagnostics"][0]["code"] == "E_COMMAND_SYNTAX"
