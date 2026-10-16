"""Render Context `fontMetrics.fontSet` expands to its packaged asset list (#1345)."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from chrona.presentation.contracts.font_sets import expand_font_set, font_set_ids
from chrona.presentation.contracts.resources import ClosureIdentity, parse_contract
from chrona.resources import safe_load

ROOT = Path(__file__).resolve().parents[5]
DEFAULTS = ROOT / "src/chrona/resources/fonts/default-font-metrics.yaml"
SEVEN = ROOT / "examples/halcyon-1/contexts/19-gallery-text-compression.yaml"
BASIC = ROOT / "tests/fixtures/aster-ssd/contexts/01-overview.yaml"


def _load(path: Path) -> dict:
    return safe_load(path.read_bytes())


def _with_set(value: dict, name: str) -> dict:
    result = deepcopy(value)
    metrics = result["body"]["environment"]["fontMetrics"]
    del metrics["assets"]
    metrics["fontSet"] = name
    return result


def _without_pins(value: dict) -> dict:
    """Authored asset lists carry no pins (#1567); the packaged set keeps its own identities."""
    result = deepcopy(value)
    for asset in result["body"]["environment"]["fontMetrics"].get("assets", ()):
        for role in ("metrics", "font"):
            if role in asset:
                asset[role].pop("contentIdentity", None)
    return result


def _identity(value: dict) -> ClosureIdentity:
    return ClosureIdentity("render-context", value["id"], "r1", "sha256:" + "a" * 64)


def test_default_set_is_the_packaged_default_assets() -> None:
    assert font_set_ids() == ("chrona.noto-sans", "chrona.noto-sans+jp")
    expanded = expand_font_set({"body": {"environment": {"fontMetrics": {"fontSet": "chrona.noto-sans"}}}})
    assert expanded["body"]["environment"]["fontMetrics"]["assets"] == _load(DEFAULTS)["assets"]


@pytest.mark.parametrize(("path", "name"), [(BASIC, "chrona.noto-sans"), (SEVEN, "chrona.noto-sans+jp")])
def test_set_context_equals_explicit_list_context(path: Path, name: str) -> None:
    explicit = _load(path)
    named = _without_pins(expand_font_set(_with_set(explicit, name)))
    explicit = _without_pins(explicit)
    assert parse_contract(_identity(named), named) == parse_contract(_identity(explicit), explicit)


def test_explicit_assets_stay_valid_and_unknown_set_is_rejected() -> None:
    explicit = _load(BASIC)
    assert parse_contract(_identity(explicit), explicit)
    bad = _with_set(explicit, "chrona.nope")
    with pytest.raises(Exception, match="expected one of"):
        parse_contract(_identity(bad), bad)


def test_both_or_neither_is_rejected() -> None:
    both = _load(BASIC)
    both["body"]["environment"]["fontMetrics"]["fontSet"] = "chrona.noto-sans"
    neither = _load(BASIC)
    del neither["body"]["environment"]["fontMetrics"]["assets"]
    for value in (both, neither):
        with pytest.raises(Exception):  # noqa: B017 - the schema's oneOf names the refusal
            parse_contract(_identity(value), value)
