from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path
import json
import os
import subprocess
import sys

import jsonschema
import yaml

from chrona.scheduling.scheduler import schedule
from chrona.core.validation import SCHEMA_PATH, validate_project


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def project(objects, relations=(), *, calendar=True):
    value = {
        "version": "timeline/v0.7",
        "project": {"id": "issue-remediation"},
        "objects": objects,
        "relations": list(relations),
    }
    if calendar:
        value["project"]["calendar"] = "standard"
        value["calendars"] = {"standard": {"working_days": ["mon", "tue", "wed", "thu", "fri"]}}
    return value


def fixed(start="2026-01-01", end="2026-01-02"):
    return {"type": "task", "schedule": {"mode": "fixed-span", "start": start, "end": end}}


def scheduled(amount="1d", **extra):
    return {"type": "task", "schedule": {"mode": "scheduled", "amount": amount, **extra}}


def relation(source, source_endpoint, target, target_endpoint, lag="0d"):
    return {"type": "dependency", "from": {"object": source, "endpoint": source_endpoint},
            "to": {"object": target, "endpoint": target_endpoint}, "lag": lag}


def test_endpoint_mode_mismatch_is_validation_diagnostic_not_exception():
    value = project(
        {"a": fixed(), "b": scheduled("1wd"), "c": scheduled("1wd")},
        [relation("a", "end", "b", "start"), relation("b", "at", "c", "start")],
    )
    diagnostics = validate_project(value)
    assert [item.id for item in diagnostics] == ["E_ENDPOINT_MODE_MISMATCH"]
    assert [item.id for item in schedule(value).diagnostics] == ["E_ENDPOINT_MODE_MISMATCH"]


def test_composite_workperiod_lag_uses_declared_calendar():
    value = project(
        {"a": fixed("2026-01-01", "2026-01-02"), "b": scheduled("1wd")},
        [relation("a", "end", "b", "start", "5wd 1mo")],
    )
    result = schedule(value)
    assert result.ok
    assert result.placements["b"]["start"] == date(2026, 2, 9)


def test_authoritative_start_anchor_rejects_opposite_endpoint_bound():
    value = project(
        {
            "a": fixed("2026-02-20", "2026-03-01"),
            "b": scheduled("5d", anchor={"start": "2026-01-05"}),
        },
        [relation("a", "end", "b", "end")],
    )
    result = schedule(value)
    assert [item.id for item in result.diagnostics] == ["E_CONTRADICTORY_BOUNDS"]
    assert "b" not in result.placements


def test_end_lower_bound_is_retreated_and_combined_with_start_bound():
    value = project(
        {
            "start-source": fixed("2026-02-19", "2026-02-20"),
            "end-source": fixed("2026-02-28", "2026-03-01"),
            "target": scheduled("5d"),
        },
        [
            relation("start-source", "end", "target", "start"),
            relation("end-source", "end", "target", "end"),
        ],
    )
    result = schedule(value)
    assert result.ok
    assert result.placements["target"] == {"start": date(2026, 2, 24), "end": date(2026, 3, 1)}


def test_empty_calendar_is_structurally_rejected():
    value = project({"a": scheduled("1wd", anchor={"start": "2026-01-05"})})
    value["calendars"]["standard"]["working_days"] = []
    assert [item.id for item in validate_project(value)] == ["E_SCHEMA"]
    assert [item.id for item in schedule(value).diagnostics] == ["E_SCHEMA"]


def test_non_working_explicit_workperiod_anchor_is_rejected():
    value = project({"a": scheduled("5wd", anchor={"start": "2026-01-04"})})
    result = schedule(value)
    assert [item.id for item in result.diagnostics] == ["E_NON_WORKING_ANCHOR"]


def test_placement_order_is_project_order_and_hash_seed_independent():
    example = ROOT / "examples" / "controller-z" / "project.yaml"
    direct = schedule(yaml.safe_load(example.read_text(encoding="utf-8")))
    expected_order = list(yaml.safe_load(example.read_text(encoding="utf-8"))["objects"])
    assert list(direct.placements) == expected_order

    command = [sys.executable, "-c", (
        "import json,yaml; from chrona.scheduling.scheduler import schedule; "
        f"p=yaml.safe_load(open({str(example)!r})); "
        "print(json.dumps(schedule(p).placements,default=str))"
    )]
    outputs = []
    for seed in ("1", "2", "3", "4", "5"):
        env = os.environ | {"PYTHONHASHSEED": seed, "PYTHONPATH": str(ROOT / "src")}
        outputs.append(subprocess.run(command, env=env, check=True, capture_output=True, text=True).stdout)
    assert len(set(outputs)) == 1


def test_legacy_v01_extension_string_remains_schema_readable_but_not_evaluable():
    value = project({"a": fixed()}, calendar=False)
    value["extensions"] = ["legacy-package"]
    schema = yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(value)
    assert [item.id for item in validate_project(value)] == ["E_PACKAGE_RESOLUTION_REQUIRED"]
