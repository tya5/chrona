"""M11-3 append-only accounting observations, isolated from Project scheduling."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CostResult:
    status: str
    diagnostics: tuple[str, ...]
    totals: tuple[dict[str, Any], ...] = ()


class MemoryCostObservationStore:
    def __init__(self, value: dict[str, Any]): self._value, self._revision = deepcopy(value), 0
    def read(self): return f"cost:{self._revision}", deepcopy(self._value)
    def write(self, revision: str, value: dict[str, Any]):
        if revision != f"cost:{self._revision}": return None
        self._revision += 1; self._value = deepcopy(value); return self.read()


def record_cost_observation(store: MemoryCostObservationStore, base_revision: str, observation: dict[str, Any]) -> CostResult:
    revision, current = store.read()
    if revision != base_revision: return CostResult("rejected", ("E_COMMAND_STALE_BASE_REVISION",))
    if any(item.get("id") == observation.get("id") for item in current.get("observations", [])): return CostResult("rejected", ("E_COST_DUPLICATE_ID",))
    if observation.get("rateUnit") == observation.get("quantityUnit") and "rate" in observation: return CostResult("rejected", ("E_COST_UNIT_MISMATCH",))
    candidate = deepcopy(current); candidate.setdefault("observations", []).append(deepcopy(observation))
    return CostResult("accepted", ()) if store.write(base_revision, candidate) else CostResult("rejected", ("E_COMMAND_STALE_BASE_REVISION",))


def aggregate_cost_observations(value: dict[str, Any]) -> CostResult:
    totals: dict[tuple[str, str], float] = {}
    for item in value.get("observations", []):
        if "rate" not in item: continue
        if item.get("rateUnit") == item.get("quantityUnit"): return CostResult("rejected", ("E_COST_UNIT_MISMATCH",))
        key = (item["quantityUnit"], item["rateUnit"]); totals[key] = totals.get(key, 0) + item["quantity"] * item["rate"]
    return CostResult("accepted", (), tuple({"quantityUnit": a, "rateUnit": b, "amount": n} for (a,b),n in sorted(totals.items())))
