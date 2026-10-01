"""#575: the frozen layout-profile fixtures stay valid against the live schema.

The engine tests read these copies instead of `examples/`, so an example edit
cannot move an engine assertion. A copy that the live schema or resolver
rejects must be migrated deliberately, and this guard is what says so.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from chrona.presentation.layout.profile import LAYOUT_VERSION, resolve_layout_profile
from chrona.resources import schema_validator

PROFILES = Path(__file__).parents[5] / "tests/fixtures/layout-profiles"
FIXTURES = sorted(PROFILES.glob("*.yaml"))
SOURCES = {"title", "table", "timeline", "timeline-axis", "legend", "notes"}


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_the_three_engine_profiles_are_frozen():
    assert [path.stem for path in FIXTURES] == ["briefing", "overlay-briefing", "print-portrait"]


@pytest.mark.parametrize("path", FIXTURES, ids=lambda path: path.stem)
def test_fixture_is_current_and_schema_valid(path):
    profile = _load(path)
    assert profile["version"] == LAYOUT_VERSION
    assert profile["id"] == path.stem
    assert not list(schema_validator("layout-profile-v0.10.schema.yaml").iter_errors(profile))


@pytest.mark.parametrize("path", FIXTURES, ids=lambda path: path.stem)
def test_fixture_resolves_with_only_its_declared_tokens(path):
    profile = _load(path)
    theme = {"body": {"values": {name: {"type": "number", "value": 16}
                                 for name in profile["requiredThemeTokens"]}}}
    resolved = resolve_layout_profile(profile, available_sources=SOURCES, theme=theme)
    assert resolved.profile_id == path.stem


def test_a_fixture_the_schema_rejects_fails_the_guard():
    profile = _load(FIXTURES[0])
    profile["unknownTopLevelKey"] = True
    assert list(schema_validator("layout-profile-v0.10.schema.yaml").iter_errors(profile))
