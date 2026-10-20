"""The network guide works from its own CSV/files in an empty workspace."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from xml.etree import ElementTree

from PIL import Image

from chrona.app.cli import main
from tools.check_documented_commands import discover, discover_files


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
GUIDE = Path("docs/guides/network-view.md")


def test_network_guide_csv_renders_real_svg_and_png_without_clone_resources(tmp_path, monkeypatch, capsys):
    files = [(name, text) for document, _, name, text in discover_files(ROOT) if document == GUIDE]
    assert {name for name, _ in files} == {"network-plan.csv", "network-view.yaml", "network-layout.yaml"}
    for name, text in files:
        (tmp_path / name).write_text(text, encoding="utf-8")
    commands = [item for item in discover(ROOT) if item.path == GUIDE]
    assert len(commands) == 3 and all(item.skip_reason is None for item in commands)
    monkeypatch.chdir(tmp_path)
    for command in commands:
        monkeypatch.setattr(sys, "argv", list(command.tokens))
        capsys.readouterr()
        try:
            main()
        except SystemExit as error:
            assert error.code in (None, 0), capsys.readouterr()
        response = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        assert response["status"] == "ok", response

    svg = ElementTree.parse(tmp_path / "network.svg")
    items = {node.attrib["data-scene-id"]: node for node in svg.iter() if "data-scene-id" in node.attrib}
    nodes = {key for key in items if key.startswith("network-node:")}
    assert nodes == {"network-node:design", "network-node:build", "network-node:test"}
    for object_id, label in (("design", "Design"), ("build", "Build"), ("test", "Test")):
        assert "".join(items[f"network-label:{object_id}"].itertext()) == label
    assert len([key for key in items if key.startswith("network-edge:")]) == 2
    with Image.open(tmp_path / "network.png") as image:
        assert image.size == (1200, 600)
        assert image.getbbox() is not None
