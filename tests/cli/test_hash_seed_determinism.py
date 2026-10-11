"""A command whose JSON is deterministic by contract prints the same bytes under every hash seed (#789).

`analysis.totalFloat` used to follow set iteration, so `chrona schedule` printed a different key order per process.
Each case runs the real CLI in a subprocess under eight `PYTHONHASHSEED` values over the starter plan and HALCYON-1.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures"
CLI = FIXTURES / "cli_characterization"
SEEDS = tuple(range(8))
CASES = {
    "schedule-starter": ("schedule", str(CLI / "starter.yaml")),
    "schedule-halcyon-1": ("schedule", str(CLI / "halcyon-1" / "project.yaml")),
    "validate-starter": ("validate", str(CLI / "starter.yaml")),
    "validate-halcyon-1": ("validate", str(CLI / "halcyon-1" / "project.yaml")),
    "compile-derived-gates": ("compile", str(FIXTURES / "terse" / "derived-gates.chrona")),
    "compile-halcyon-1": ("compile", str(FIXTURES / "terse" / "halcyon-1-core.chrona")),
}


def _run(args: tuple[str, ...], seed: int) -> tuple[int, str, str]:
    env = {**os.environ, "PYTHONHASHSEED": str(seed)}
    done = subprocess.run([sys.executable, "-m", "chrona", *args], env=env, capture_output=True, text=True,
                          encoding="utf-8", check=False)
    return done.returncode, done.stdout, done.stderr


@pytest.mark.parametrize("case", sorted(CASES))
def test_the_command_prints_identical_bytes_under_eight_hash_seeds(case):
    outputs = {seed: _run(CASES[case], seed) for seed in SEEDS}
    assert outputs[0][0] == 0 and outputs[0][1], outputs[0]
    assert len({outputs[seed] for seed in SEEDS}) == 1, {seed: hash(value) for seed, value in outputs.items()}


@pytest.mark.parametrize("project", ["starter.yaml", "halcyon-1/project.yaml"])
def test_schedule_prints_total_float_in_project_object_order(project):
    """Spec 57: the canonical Project object order, the order `criticalObjectIds` already uses."""
    path = CLI / project
    code, out, _ = _run(("schedule", str(path)), seed=3)
    assert code == 0
    analysis = json.loads(out)["analysis"]
    import yaml
    objects = [name for name, item in yaml.safe_load(path.read_text(encoding="utf-8"))["objects"].items()
               if item["schedule"]["mode"] != "rollup"]
    assert list(analysis["totalFloat"]) == objects
    critical = set(analysis["criticalObjectIds"])
    assert analysis["criticalObjectIds"] == [name for name in objects if name in critical]
    assert all(analysis["totalFloat"][name]["value"] == 0 for name in critical)


_PROBE = """
import json, sys, yaml
from chrona.scheduling.scheduler import schedule
project = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
analysis = schedule(project).analysis
print(json.dumps({"float": list(analysis.total_float), "latest": list(analysis.latest_placements),
                  "finish": analysis.project_finish.isoformat()}))
"""


def test_every_mapping_of_the_analysis_follows_the_project_object_order_under_every_seed():
    """The scheduler orders `totalFloat` and `latest_placements` itself; no adapter has to sort them."""
    import yaml
    path = CLI / "halcyon-1" / "project.yaml"
    objects = [name for name, item in yaml.safe_load(path.read_text(encoding="utf-8"))["objects"].items()
               if item["schedule"]["mode"] != "rollup"]
    seen = set()
    for seed in SEEDS:
        done = subprocess.run([sys.executable, "-c", _PROBE, str(path)], capture_output=True, text=True, check=True,
                              env={**os.environ, "PYTHONHASHSEED": str(seed)})
        record = json.loads(done.stdout)
        assert record["float"] == objects and record["latest"] == objects, seed
        seen.add(record["finish"])
    assert len(seen) == 1
