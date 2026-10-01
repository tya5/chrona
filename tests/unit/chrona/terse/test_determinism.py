"""The compile result is a pure function of the source bytes: no hash seed, locale or host influence (#148, design 8)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.support.terse_plans import FIXTURES

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = (
    "import sys\n"
    "from chrona.usecases.terse_compile import compile_plan\n"
    "result = compile_plan(open(sys.argv[1], 'rb').read())\n"
    "sys.stdout.buffer.write(result.yaml or b'REJECTED')\n"
)


def _compile_in_subprocess(plan: str, **env: str) -> bytes:
    environment = {**os.environ, **env, "PYTHONPATH": os.pathsep.join(filter(None, (str(ROOT / "src"), str(ROOT), os.environ.get("PYTHONPATH", ""))))}
    completed = subprocess.run([sys.executable, "-c", SCRIPT, str(FIXTURES / f"{plan}.chrona")], capture_output=True, env=environment,
                               cwd=ROOT, check=True, timeout=120)
    return completed.stdout


@pytest.mark.parametrize("plan", ["halcyon-1-core", "special-characters", "yaml-hazard-names", "calendars"])
def test_subprocess_output_equals_the_golden_bytes_under_other_hash_seeds_and_locales(plan):
    golden = (FIXTURES / f"{plan}.project.yaml").read_bytes()
    for env in ({"PYTHONHASHSEED": "1", "LC_ALL": "C"}, {"PYTHONHASHSEED": "4242", "LC_ALL": "C.UTF-8", "LANG": "ja_JP.UTF-8"},
                {"PYTHONHASHSEED": "random", "LC_ALL": "en_US.UTF-8", "TZ": "Pacific/Auckland"}):
        assert _compile_in_subprocess(plan, **env) == golden, env


def test_the_output_never_embeds_the_source_path_or_a_hash():
    text = _compile_in_subprocess("groups", PYTHONHASHSEED="7").decode("utf-8")
    assert "groups.chrona" not in text and str(ROOT) not in text and "sha256" not in text
