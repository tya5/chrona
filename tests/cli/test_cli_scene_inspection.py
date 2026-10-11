"""Real CLI inspection siblings preserve artifacts, results and write guards."""
import json
import sys
from types import SimpleNamespace

import pytest

import chrona.app.cli as cli
from chrona.presentation.scene.serialization import SceneSerializationError


def test_real_draft_cli_writes_readable_scene_without_changing_svg_or_stdout(tmp_path, monkeypatch, capsys):
    source = tmp_path / "project.yaml"
    source.write_text(
        "version: timeline/v0.7\nproject: {id: inspection, title: Inspection}\n"
        "objects:\n  work: {type: task, title: Work, schedule: {mode: fixed-span, "
        "start: '2027-01-04', end: '2027-01-20'}}\nrelations: []\n",
        encoding="utf-8",
    )
    output, inspected, scene = (tmp_path / name for name in ("plain.svg", "inspected.svg", "scene.json"))
    monkeypatch.setattr(sys, "argv", ["chrona", "render", str(source), "-o", str(output)])
    cli.main()
    plain_result = capsys.readouterr()
    canonical = []
    original = cli.serialize_scene

    def capture(completed):
        encoded = original(completed)
        canonical.append(encoded)
        return encoded

    monkeypatch.setattr(cli, "serialize_scene", capture)
    monkeypatch.setattr(sys, "argv", ["chrona", "render", str(source), "-o", str(inspected),
                                     "--emit-scene", str(scene)])
    cli.main()

    assert capsys.readouterr() == plain_result
    assert inspected.read_bytes() == output.read_bytes()
    [canonical_bytes] = canonical
    readable = scene.read_bytes()
    assert json.loads(readable) == json.loads(canonical_bytes)
    assert len(canonical_bytes.split(b"\n")) == 2
    primitives = [p for surface in json.loads(readable)["surfaces"] for p in surface["primitives"]]
    assert len(primitives) > 1
    for primitive in primitives:
        encoded = json.dumps(primitive, ensure_ascii=False, separators=(",", ":")).encode()
        assert sum(line.strip().removesuffix(b",") == encoded for line in readable.split(b"\n")) == 1


def test_serialization_failure_still_precedes_every_output_write(tmp_path, monkeypatch):
    output, scene = tmp_path / "out.svg", tmp_path / "scene.json"

    def reject(_scene):
        raise SceneSerializationError("E_SCENE_SERIALIZATION: invalid completed Scene")

    monkeypatch.setattr(cli, "serialize_scene", reject)
    with pytest.raises(cli.CliFailure, match="E_SCENE_SERIALIZATION"):
        cli._write_render_outputs(SimpleNamespace(scene=object()),
                                  SimpleNamespace(output=str(output), emit_scene=str(scene)))
    assert not output.exists() and not scene.exists()


def test_existing_inspection_sibling_is_refused_before_serialization_or_writes(tmp_path, monkeypatch):
    output, scene = tmp_path / "out.svg", tmp_path / "scene.json"
    scene.write_bytes(b"existing")

    def unexpected(_scene):
        raise AssertionError("an existing sibling must be refused first")

    monkeypatch.setattr(cli, "serialize_scene", unexpected)
    with pytest.raises(cli.CliFailure, match="E_SCENE_OUTPUT_EXISTS"):
        cli._write_render_outputs(SimpleNamespace(scene=object()),
                                  SimpleNamespace(output=str(output), emit_scene=str(scene)))
    assert not output.exists() and scene.read_bytes() == b"existing"
