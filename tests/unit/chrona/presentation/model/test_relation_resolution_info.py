"""Completed recovery facts retain identity without inflating fragment counts."""
import json
from types import SimpleNamespace

import pytest

from chrona.presentation.model.info_diagnostics import (
    RelationResolutionInfo, RelationResolutionStage as Stage, RelationResolutionSummary,
)
from chrona.usecases.draft_render import warning_payloads


def test_scene_and_adapter_preserve_critical_stage_and_summary():
    fact = RelationResolutionInfo("surface", "relation:a", Stage.STUB, True)
    summary = RelationResolutionSummary("surface", ((Stage.STUB, 1), (Stage.TEXT, 2)))
    assert json.loads(fact.scene_diagnostic().split(":", 1)[1]) == fact.payload()
    assert summary.payload() == {"surfaceId": "surface", "count": 3, "stages": {"stub": 1, "text": 2}}
    payloads = warning_payloads(SimpleNamespace(warning_records=(), info_diagnostics=(fact, summary)))
    assert len(payloads) == 2
    assert payloads[0]["critical"] is True
    assert payloads[0]["stage"] == "stub"
    assert payloads[1]["count"] == 3
    assert all(item["severity"] == "info" and item["message"] for item in payloads)


@pytest.mark.parametrize("args", (
    ("", "r", Stage.TEXT, True), (1, "r", Stage.TEXT, True),
    ("s", "", Stage.TEXT, True), ("s", 1, Stage.TEXT, True),
    ("s", "r", "text", True), ("s", "r", Stage.NORMAL, True),
    ("s", "r", Stage.TEXT, 1),
))
def test_invalid_resolution_info_is_rejected(args):
    with pytest.raises(ValueError, match="E_PRESENTATION_INFO_INVALID"):
        RelationResolutionInfo(*args)


@pytest.mark.parametrize("counts", (
    (), ((Stage.TEXT, 0),), ((Stage.TEXT, True),), ((Stage.NORMAL, 1),),
    (("text", 1),), ((Stage.TEXT, 1), (Stage.TEXT, 2)),
))
def test_invalid_summary_is_rejected(counts):
    with pytest.raises(ValueError, match="E_PRESENTATION_INFO_INVALID"):
        RelationResolutionSummary("s", counts)
