"""The 32-line HALCYON-1 schedule core reproduces the example's schedule, compared through the scheduler (#148).

The PR-path test compares with a committed synthetic twin (a copy of the hand-written YAML); one `corpus` test
compares with the live example. Corpus output is evidence, never an oracle: a corpus edit is not "fixed" by
touching the fixture.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.support.terse_plans import FIXTURES, compile_fixture, edges, load_yaml_bytes, schedule_summary

LIVE = Path(__file__).resolve().parents[4] / "examples" / "halcyon-1" / "project.yaml"


def _compare(twin_bytes: bytes, *, extension_types: frozenset[str] = frozenset()) -> None:
    compiled = compile_fixture("halcyon-1-core.chrona")
    assert compiled.ok, [item.as_dict() for item in compiled.diagnostics]
    twin = load_yaml_bytes(twin_bytes)
    ours, theirs = schedule_summary(compiled.project), schedule_summary(twin)
    assert len(ours["placements"]) == 29 and len(edges(compiled.project)) == 24
    assert ours["placements"] == theirs["placements"]
    assert ours["critical"] == theirs["critical"] == []  # no zero-float driving path reaches project finish
    assert edges(compiled.project) == edges(twin)
    assert list(compiled.project["calendars"]) == list(twin["calendars"])
    assert compiled.project["calendars"] == twin["calendars"]
    assert compiled.project["project"] == {k: twin["project"][k] for k in compiled.project["project"]}
    for name, item in compiled.project["objects"].items():  # the schedule-and-structure subset matches object by object
        for key in ("type", "title", "parent", "calendar", "schedule"):
            if key == "type" and twin["objects"][name].get(key) in extension_types:
                continue  # a profile-package type (the live gates are typed PDR/CDR/PSR); the terse core keeps `gate`
            assert item.get(key) == twin["objects"][name].get(key), (name, key)


def test_halcyon_core_matches_its_synthetic_twin():
    _compare((FIXTURES / "halcyon-1-core.twin.yaml").read_bytes())


@pytest.mark.corpus
def test_halcyon_core_matches_the_live_example():
    live = load_yaml_bytes(LIVE.read_bytes())
    packages = [load_yaml_bytes((LIVE.parent / item["resource"]["address"]).read_bytes()) for item in live.get("extensions", ())]
    _compare(LIVE.read_bytes(), extension_types=frozenset(name for package in packages for name in package.get("profiles", {})))


def test_the_core_plan_is_the_32_line_worked_example_of_the_design():
    lines = [line for line in (FIXTURES / "halcyon-1-core.chrona").read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 32
