from copy import deepcopy
from datetime import date
from types import SimpleNamespace

import pytest

from chrona.presentation_scene import build_presentation_scene
from chrona.presentation_settings import builtin_bases


def item():
    return SimpleNamespace(object_id="a", source_type="span", planned={"start": date(2026, 1, 1), "end": date(2026, 1, 10)}, actual={"start": date(2026, 1, 2), "finish": date(2026, 1, 12)})


def test_scene_joins_axis_ticks_and_marks_without_svg_geometry():
    settings = builtin_bases()["executive-v0.2"]
    scene = build_presentation_scene("Roadmap", [item()], (date(2026, 1, 1), date(2026, 2, 1)), settings)
    assert [mark.facet for mark in scene.marks] == ["planned", "actual", "finish-delta"]
    assert scene.axes[0].level == "month"
    assert scene.ticks[0].start == date(2026, 1, 1)


def test_scene_rejects_invalid_axis_order_before_adapter_use():
    settings = deepcopy(builtin_bases()["executive-v0.2"])
    settings["layout"]["axis"]["levels"] = ["month", "quarter"]
    with pytest.raises(ValueError, match="E_PRESENTATION_AXIS_INVALID"):
        build_presentation_scene("Roadmap", [item()], (date(2026, 1, 1), date(2026, 2, 1)), settings)
