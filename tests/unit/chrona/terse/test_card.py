"""The one-page card (docs/guides/terse-plan.md) must teach plans that compile and schedule (#148)."""
from __future__ import annotations

from pathlib import Path

from chrona.scheduling.scheduler import schedule
from tools.check_documented_commands import discover_plans
from tests.support.terse_plans import compile_text

ROOT = Path(__file__).resolve().parents[4]
CARD = Path("docs/guides/terse-plan.md")


def test_every_plan_on_the_card_compiles_validates_and_schedules():
    plans = [plan for plan in discover_plans(ROOT) if plan.path == CARD]
    assert len(plans) >= 2
    for plan in plans:
        compiled = compile_text(plan.text)
        assert compiled.ok, [item.as_dict() for item in compiled.diagnostics]
        result = schedule(compiled.project)
        assert result.ok, [(item.id, item.path) for item in result.diagnostics]


def test_the_card_stays_one_page_and_names_the_loop():
    text = (ROOT / CARD).read_text(encoding="utf-8")
    assert len(text.splitlines()) <= 120
    for needle in ("chrona compile", "chrona validate", "chrona schedule", "sourceRange", "exclusive", "from DATE"):
        assert needle in text
