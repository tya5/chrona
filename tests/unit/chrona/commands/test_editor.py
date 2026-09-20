from chrona.commands.editor import EditorState, apply_command_result
from chrona.commands.view_commands import ViewCommandResult


def test_editor_applies_only_accepted_command_results_and_preserves_state_on_conflict():
    state = EditorState("view:1", {"body": {}})
    accepted = ViewCommandResult("accepted", {"body": {"annotations": []}}, (), "view:2")
    applied = apply_command_result(state, accepted)
    assert applied.status == "applied" and applied.revision == "view:2"
    conflict = apply_command_result(applied, ViewCommandResult("rejected", None, ("E_CONFLICT",)))
    assert conflict.status == "resync-required" and conflict.model == applied.model
