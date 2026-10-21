"""A group-header label stays inside the band drawn behind it, in Latin and in CJK text (#1629).

The sunday design draws each header band only as far as its text and never past the table. A label wider than
the table used to run past the band: unbounded, with the band clamped. It now gives way with an ellipsis, with
the same measurement for every script. Synthetic Project; no `examples/` input.
"""
from __future__ import annotations

import json
import sys
from datetime import date

import pytest
import yaml

from chrona.app.cli import main
from tests.support import synthetic_review as sr

LONG_LATIN = "Lena Petrovic-Smith of the Platform Engineering Group and the External Contractors Association"
LONG_CJK = "佐藤健太郎デザイン部門担当チームの皆さんと外部委託先"
SHORT_CJK = "佐藤"


def _scene(tmp_path, monkeypatch, capsys, owners):
    # A role-bound grouping lists headers in the Project's declared order (#1870); sorting keeps each owner's band
    # in the position this test was written for (the first band takes the first-group template).
    objects = {f"t{index}": sr.span(f"t{index}", date(2026, 11, 2 + 7 * index), 5, owner=owner, title=f"Task {index}")
               for index, owner in enumerate(sorted(owners))}
    project = sr.project(objects)
    project["entities"] = {owner: {"type": "team", "title": owner} for owner in owners}
    path = tmp_path / "project.yaml"
    path.write_text(yaml.safe_dump(project, allow_unicode=True), encoding="utf-8")
    scene = tmp_path / "scene.json"
    monkeypatch.setattr(sys, "argv", ["chrona", "render", str(path), "--preset", "sunday",
                                      "--output", str(tmp_path / "out.svg"), "--emit-scene", str(scene)])
    capsys.readouterr()
    main()
    return json.loads(scene.read_text(encoding="utf-8"))


def _primitives(node, found):
    if isinstance(node, dict):
        if node.get("id", "").startswith("group-header"):
            found[node["id"]] = node
        for value in node.values():
            _primitives(value, found)
    elif isinstance(node, list):
        for value in node:
            _primitives(value, found)
    return found


def _right(node):
    bounds = node["bounds"]
    return bounds["inline"] + bounds["inlineSize"]


@pytest.mark.parametrize("owner", [LONG_LATIN, LONG_CJK], ids=["latin", "cjk"])
def test_long_header_label_ellipsises_inside_its_band(tmp_path, monkeypatch, capsys, owner):
    found = _primitives(_scene(tmp_path, monkeypatch, capsys, [owner, "Ken"]), {})
    text, band = found[f"group-header:{owner}"], found[f"group-header-band:{owner}"]
    assert _right(text) <= _right(band) + 1e-6
    assert "…" in text["text"] and owner not in text["text"]


@pytest.mark.parametrize("owner", ["Ken", SHORT_CJK], ids=["latin", "cjk"])
def test_short_header_label_is_shown_whole_inside_its_band(tmp_path, monkeypatch, capsys, owner):
    found = _primitives(_scene(tmp_path, monkeypatch, capsys, [owner, LONG_LATIN]), {})
    text, band = found[f"group-header:{owner}"], found[f"group-header-band:{owner}"]
    assert _right(text) <= _right(band) + 1e-6
    assert owner.upper() in text["text"]
