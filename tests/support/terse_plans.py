"""Shared helpers for the terse plan syntax tests (#148): fixtures, scheduling summaries, relation edges."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from chrona.core.validation import validate_project
from chrona.resources import safe_load
from chrona.scheduling.scheduler import schedule
from chrona.usecases.terse_compile import PlanCompilation, compile_plan

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "terse"


def compile_text(text: str, source: str | None = None) -> PlanCompilation:
    return compile_plan(text.encode("utf-8"), source)


def compile_fixture(name: str) -> PlanCompilation:
    return compile_plan((FIXTURES / name).read_bytes(), name)


def load_yaml_bytes(data: bytes) -> dict[str, Any]:
    return safe_load(data)


def schedule_summary(project: dict[str, Any]) -> dict[str, Any]:
    """Placements, critical set and driving edges as plain data, so two Projects compare through the scheduler."""
    assert validate_project(project) == []
    result = schedule(project)
    assert result.ok, [item.id for item in result.diagnostics]
    placements = {key: {k: v.isoformat() for k, v in value.items()} for key, value in result.placements.items()}
    return {"placements": placements, "critical": sorted(result.analysis.critical)}


def edges(project: dict[str, Any]) -> list[tuple]:
    """Dependency edges modulo relation ids, with the lag normalised to (value, calendar)."""
    found = []
    for relation in project.get("relations", []):
        lag = relation.get("lag", "0d")
        value, calendar = (lag["value"], lag.get("calendar")) if isinstance(lag, dict) else (lag, None)
        found.append((relation["from"]["object"], relation["from"]["endpoint"],
                      relation["to"]["object"], relation["to"]["endpoint"], value, calendar))
    return sorted(found, key=repr)
