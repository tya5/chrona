from chrona.view_commands import (MemoryViewStore, add_presentation_annotation, delete_presentation_annotation, edit_presentation_annotation, redo_view_command, undo_view_command)


def test_annotation_command_is_view_local_and_revision_bound():
    store = MemoryViewStore({"kind": "view", "id": "risk", "body": {}})
    base, before = store.read()
    annotation = {"id": "risk-1", "purpose": "callout", "anchor": {"kind": "object", "id": "firmware"}, "placement": {"side": "above", "alignment": "end"}, "text": "Risk"}
    result = add_presentation_annotation(store, base, annotation)
    assert result.status == "accepted"
    assert before["body"] == {}
    assert result.view["body"]["annotations"] == [annotation]
    assert add_presentation_annotation(store, base, annotation).diagnostics == ("E_CONFLICT",)


def test_annotation_edit_delete_and_undo_redo_are_view_revision_commands():
    store = MemoryViewStore({"kind": "view", "id": "risk", "body": {}})
    annotation = {"id": "risk-1", "purpose": "note", "anchor": {"kind": "object", "id": "firmware"}, "placement": {"side": "above", "alignment": "end"}, "text": "Risk"}
    base, _ = store.read()
    added = add_presentation_annotation(store, base, annotation, "add")
    edited_annotation = annotation | {"text": "Updated risk"}
    edited = edit_presentation_annotation(store, added.result_revision, "risk-1", edited_annotation, "edit")
    assert edited.view["body"]["annotations"] == [edited_annotation]
    undone = undo_view_command(store, edited.result_revision, "edit")
    assert undone.view["body"]["annotations"] == [annotation]
    redone = redo_view_command(store, undone.result_revision, "edit")
    assert redone.view["body"]["annotations"] == [edited_annotation]
    deleted = delete_presentation_annotation(store, redone.result_revision, "risk-1", "delete")
    assert deleted.view["body"]["annotations"] == []
    assert delete_presentation_annotation(store, deleted.result_revision, "missing").diagnostics == ("E_REFERENCE",)
