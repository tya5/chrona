"""The HALCYON board through the default draft and each catalogue preset, rendered once (#657).

Four rule checks used to be four tests that each rendered the same board and preset.
pytest-split places test items on shards one by one, so consumers of one render landed on
different machines and each rendered it again (measured on CI, run 36737037428: 6 of 7
preset keys rendered twice, one three times).  One item per render keeps every consumer on
the machine that renders it.  The checks are unchanged (`tests/support/preset_checks.py`);
every applicable check runs and every failure is reported by name.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tests.support import preset_checks as checks

ROOT = Path(__file__).resolve().parents[2]
HALCYON = "examples/halcyon-1/project.yaml"
HALCYON_ACTUAL = "examples/halcyon-1/actual.yaml"
PRESETS = [entry["id"] for entry in yaml.safe_load(
    (ROOT / "src/chrona/resources/presets/library.yaml").read_text(encoding="utf-8"))["entries"]
    if entry["id"] != "chrona-default-draft"]  # the bundled default is the "default" case; its bundle is editorial-readable-default (#1305)


def _applicable(name: str):
    """(rule name, check) pairs that apply to the default draft or one preset."""
    yield "distinct axis band", lambda scene: checks.check_distinct_axis_band(name, scene)
    if name == "default":
        return
    yield "bounded axis cells with centred labels", checks.check_bounded_axis_cells
    if name == "mission-light":
        yield "start-aligned month labels are inset", checks.check_start_aligned_month_labels
    if name == "print-mono":
        yield "print-mono separates slips and as-of in greyscale", checks.check_print_mono_greyscale


@pytest.mark.parametrize("name", ["default", *PRESETS])
def test_halcyon_render_satisfies_every_preset_rule(render_cache, name):
    scene = render_cache.render(HALCYON, HALCYON_ACTUAL, None if name == "default" else name).scene
    failures = []
    for rule, check in _applicable(name):
        try:
            check(scene)
        except AssertionError as error:
            failures.append(f"{rule}: {error}")
    assert not failures, "\n".join(failures)
