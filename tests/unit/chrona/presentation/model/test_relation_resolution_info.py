"""Completed recovery facts retain identity without inflating fragment counts."""
import json
from types import SimpleNamespace

import pytest

from chrona.presentation.model.info_diagnostics import (
    RelationResolutionInfo, RelationResolutionStage as Stage, RelationResolutionSummary,
    RelationPolicySupersession, CriticalRelationTemporalExcursion,
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


def test_policy_supersession_names_the_two_declared_members_in_every_adapter():
    fact = RelationPolicySupersession("s", "visible-overflow", "suppress")
    assert json.loads(fact.scene_diagnostic().split(":", 1)[1]) == fact.payload()
    payload, = warning_payloads(SimpleNamespace(warning_records=(), info_diagnostics=(fact,)))
    assert payload["code"] == "I_LAYOUT_RELATION_POLICY_SUPERSEDED"
    assert payload["viewMember"] == "visibility.relations.overflow"
    assert payload["layoutMember"] == "relationRouting.unroutable"
    assert payload["severity"] == "info"


def test_protected_temporal_excursion_is_typed_scene_cli_and_mcp_info():
    fact = CriticalRelationTemporalExcursion("table-timeline", "relation:edge-1",
                                             (10., 40.), (8., 40.))
    expected = {"surfaceId": "table-timeline", "relationId": "relation:edge-1",
                "allowedInline": [10., 40.], "actualInline": [8., 40.]}
    assert fact.code == "I_LAYOUT_CRITICAL_RELATION_TEMPORAL_EXCURSION"
    assert fact.payload() == expected
    assert json.loads(fact.scene_diagnostic().split(":", 1)[1]) == expected
    payload, = warning_payloads(SimpleNamespace(warning_records=(), info_diagnostics=(fact,)))
    assert {key: value for key, value in payload.items() if key != "message"} == {
        "code": fact.code, "severity": "info", **expected}
    assert "leaves its temporal inline hull" in payload["message"]


def test_temporal_excursion_survives_cli_emission_and_mcp_diagnostic_projection(tmp_path, capsys):
    from chrona.app.agent_tools import _warning
    from chrona.app.agent_workspace import WorkspaceScope
    from chrona.app.cli import _emit_render_result

    fact = CriticalRelationTemporalExcursion("table-timeline", "relation:edge-1",
                                             (10., 40.), (8., 40.))
    rendered = SimpleNamespace(warning_records=(), info_diagnostics=(fact,))
    _emit_render_result(rendered)
    emitted, = json.loads(capsys.readouterr().out)["warnings"]
    assert emitted["code"] == fact.code and emitted["severity"] == "info"
    assert emitted["allowedInline"] == [10., 40.] and emitted["actualInline"] == [8., 40.]
    projected = _warning(WorkspaceScope(tmp_path), emitted)
    assert projected["code"] == fact.code and projected["severity"] == "info"
    assert projected["detail"]["allowedInline"] == emitted["allowedInline"]
    assert projected["detail"]["actualInline"] == emitted["actualInline"]
    assert projected["detail"]["relationId"] == fact.relation_id


@pytest.mark.parametrize("args", (
    ("s", "r", (0., 1.), (0., 1.)),
    ("s", "r", (1., 0.), (2., 3.)),
    ("s", "r", (0., float("inf")), (0., 2.)),
    ("s", "r", (0., 2.), (True, 3.)),
    ("", "r", (0., 1.), (2., 3.)),
))
def test_invalid_or_nonexcursion_temporal_evidence_is_rejected(args):
    with pytest.raises(ValueError, match="E_PRESENTATION_INFO_INVALID"):
        CriticalRelationTemporalExcursion(*args)


@pytest.mark.parametrize("args", (("", "suppress", "relax"), ("s", "bad", "relax"),
                                  ("s", "suppress", "bad"), ("s", "suppress", "suppress")))
def test_invalid_or_agreeing_supersession_is_rejected(args):
    with pytest.raises(ValueError, match="E_PRESENTATION_INFO_INVALID"):
        RelationPolicySupersession(*args)
