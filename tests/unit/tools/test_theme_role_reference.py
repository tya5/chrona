"""The committed Theme-authoring reference equals what the vocabulary generates (#1827 row 1)."""
from __future__ import annotations

from dataclasses import replace
import subprocess
import sys

import pytest

from chrona.presentation.scene.capabilities import registered_role_contracts
from tools import theme_role_reference as reference
from tools.theme_role_reference import OUTPUT, ROOT, render


def test_committed_page_equals_the_generated_page():
    assert (ROOT / OUTPUT).read_bytes().decode("utf-8") == render(), (
        "run python tools/theme_role_reference.py to refresh skills/chrona/references/theme-roles.md")


def test_every_registered_role_and_unkeyed_legend_role_is_on_the_page():
    page = (ROOT / OUTPUT).read_text(encoding="utf-8")

    assert all(f"| `{role}` |" in page for role in registered_role_contracts())
    assert "`unkeyedLegendRoles`" in page and "`smallCapsScale`" in page and "`as-of.stroke`" in page


def test_a_new_role_or_property_changes_the_generated_page(monkeypatch):
    contracts = registered_role_contracts()
    committed = (ROOT / OUTPUT).read_text(encoding="utf-8")
    monkeypatch.setattr(reference, "registered_role_contracts", lambda: {**contracts, "brand-new-role": contracts["planned"]})
    assert render() != committed and "| `brand-new-role` |" in render()
    monkeypatch.setattr(reference, "registered_role_contracts", lambda: {
        **contracts, "planned": replace(contracts["planned"], properties=contracts["planned"].properties | {"smallCapsScale"})})
    assert render() != committed


def test_the_hand_written_claims_stop_generation_when_their_subject_disappears(monkeypatch):
    contracts = registered_role_contracts()
    monkeypatch.setattr(reference, "registered_role_contracts",
                        lambda: {name: value for name, value in contracts.items() if name != "as-of"})
    with pytest.raises(SystemExit, match="E_THEME_ROLE_REFERENCE_DRIFT"):
        render()


def test_check_mode_passes_for_the_committed_page_and_fails_for_a_stale_copy(tmp_path):
    run = lambda *argv: subprocess.run([sys.executable, str(ROOT / "tools/theme_role_reference.py"), *argv],
                                       capture_output=True, text=True, cwd=ROOT)
    assert run("--check").returncode == 0
    stale = tmp_path / "theme-roles.md"
    stale.write_text("stale\n", encoding="utf-8")
    result = run("--check", "--output", str(stale))
    assert result.returncode != 0 and "E_THEME_ROLE_REFERENCE_STALE" in result.stderr
