"""Stub terminal text and optional member names share Layout reservations (#1763)."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from xml.etree import ElementTree

import pytest
import yaml

from chrona.presentation.scene.serialization import serialize_scene
from chrona.resources import default_preset_resource, default_preset_root
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from tests.support import synthetic_review as sr


def _write(path: Path, value) -> Path:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return path


def _layout(search: str, *, stub: bool = True) -> dict:
    preset = yaml.safe_load(default_preset_resource().read_bytes())
    path = default_preset_root() / preset["body"]["resources"]["layout"]["path"]
    layout = yaml.safe_load(path.read_bytes())
    layout.setdefault("relationRouting", {})["search"] = search
    if stub:
        layout["relationRouting"]["unroutable"] = "stub"
    return layout


def _render(project_path: Path, *, layout: dict | None = None,
            previous_scene: Path | None = None):
    layout_path = _write(project_path.parent / "layout.yaml", layout) if layout is not None else None
    return render_draft(DraftRenderRequest(
        project_path, "svg", layout=layout_path,
        previous_scene=previous_scene)).rendered


def _svg_bytes(rendered) -> bytes:
    content = rendered.artifact.content
    return content.encode() if isinstance(content, str) else content


def _svg_text_nodes(rendered) -> dict[str, str]:
    root = ElementTree.fromstring(_svg_bytes(rendered))
    return {node.attrib["data-scene-id"]: "".join(node.itertext())
            for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "text"
            and "data-scene-id" in node.attrib}


def _assert_text_boxes_do_not_overlap(rendered):
    texts = [item for item in rendered.surface.primitives if item.kind == "Text"]
    for index, text in enumerate(texts):
        x, y, width, height = text.bounds
        for other in texts[index + 1:]:
            ox, oy, owidth, oheight = other.bounds
            assert not (x < ox + owidth - 1e-6 and ox < x + width - 1e-6
                        and y < oy + oheight - 1e-6 and oy < y + height - 1e-6), (
                            text.scene_id, other.scene_id)


def _assert_stub_terminals_and_member_disposition(rendered, *, source_title: str, target_title: str,
                                                    member_id: str):
    text_nodes = _svg_text_nodes(rendered)
    terminal_texts = [item for item in rendered.surface.primitives
                      if item.kind == "Text" and item.text is not None
                      and (item.text.startswith("-> ") or item.text.endswith(" ->"))]
    assert {f"-> {target_title}", f"{source_title} ->"} <= set(item.text for item in terminal_texts)
    assert all(text_nodes.get(item.scene_id) == item.text for item in terminal_texts)

    member_labels = [item for item in rendered.surface.primitives
                     if item.kind == "Text" and item.purpose == "member-label"
                     and item.source_ref == member_id]
    suppression = [item for item in rendered.surface.diagnostics
                   if item.startswith("W_LAYOUT_LABEL_SUPPRESSED:member-label:")
                   and member_id in item]
    assert len(member_labels) <= 1
    assert bool(member_labels) != bool(suppression)
    if member_labels:
        label, = member_labels
        assert text_nodes.get(label.scene_id) == label.text


def _public_project_path(directory: Path) -> Path:
    source = Path(__file__).resolve().parents[1] / "fixtures" / "routing_revision" / "project-v1.yaml"
    target = directory / "project.yaml"
    target.write_bytes(source.read_bytes())
    return target


@pytest.mark.parametrize("search_policy", ("first-fit", "best"))
def test_public_launch_stub_recovery_keeps_terminal_text_and_member_name_disposition(
        tmp_path, search_policy):
    directory = tmp_path / search_policy
    directory.mkdir()
    project = _public_project_path(directory)
    baseline = _render(project)
    baseline_svg = directory / "baseline.svg"
    baseline_svg.write_bytes(_svg_bytes(baseline))
    previous = directory / "previous.scene.json"
    previous.write_bytes(serialize_scene(baseline.scene))

    recovered = _render(project, layout=_layout(search_policy), previous_scene=previous)
    recovered_svg = directory / "stub-recovery.svg"
    recovered_svg.write_bytes(_svg_bytes(recovered))
    _assert_stub_terminals_and_member_disposition(
        recovered, source_title="Finalize feature spec", target_title="Pricing and billing setup",
        member_id="spec")
    _assert_text_boxes_do_not_overlap(recovered)


def test_synthetic_stub_terminals_reserve_optional_member_labels(tmp_path):
    project = sr.with_calendar(sr.project({
        "source": sr.span("source", date(2027, 1, 4), 3, title="Synthetic source"),
        "target": sr.span("target", date(2027, 1, 18), 3, title="Synthetic target"),
    }, [{"id": "source-target", "type": "dependency", "lag": "0wd",
         "from": {"object": "source", "endpoint": "end"},
         "to": {"object": "target", "endpoint": "start"}}]))
    path = _write(tmp_path / "synthetic-project.yaml", project)
    rendered = _render(path, layout=_layout("first-fit"))

    _assert_stub_terminals_and_member_disposition(
        rendered, source_title="Synthetic source", target_title="Synthetic target", member_id="source")
    _assert_text_boxes_do_not_overlap(rendered)
