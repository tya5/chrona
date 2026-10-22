"""Semantic binding/override rules independent of projects, fonts and painted marks."""
from copy import deepcopy
from dataclasses import replace
from datetime import date

import pytest

from chrona.presentation.contracts import ClosureIdentity, parse_contract
from chrona.presentation.contracts.resources import ContractError, SchemaContractError
from chrona.presentation.contracts.view_defaults import merge_view_defaults
from chrona.presentation.model.projection import FoldedPointProjection, ReviewItem, ReviewProjection
from chrona.presentation.review.annotation_expansion import expand_annotations
from tests.support import synthetic_review as sr


POLICY = {"note": {"placement": {"side": "end", "alignment": "center"}}}
BINDINGS = [
    {"kind": "note", "temporalKind": "point", "purpose": "note", "facet": "planned", "endpoint": "at"},
    {"kind": "risk", "temporalKind": "span", "purpose": "note", "facet": "actual", "endpoint": "body"},
    {"kind": "note", "temporalKind": "span", "purpose": "note", "facet": "planned", "endpoint": "end"},
]


def view(*, bindings=BINDINGS, policy=POLICY, annotations=()):
    raw = sr.bundle()["view"]
    raw["body"]["annotations"] = deepcopy(list(annotations))
    if bindings is not None:
        raw["body"]["annotationBindings"] = deepcopy(bindings)
    if policy is not None:
        raw["body"]["annotationPlacement"] = deepcopy(policy)
    return parse_contract(ClosureIdentity("view", raw["id"], "r", "sha256:" + "a" * 64), raw).view


def item(identifier, shape="span", source="primary"):
    planned = {"at": date(2027, 1, 6)} if shape == "point" else {
        "start": date(2027, 1, 4), "end": date(2027, 1, 8)}
    return ReviewItem(identifier, identifier, shape, planned, None, None, (), source_kind=source)


def projection(*items, folded=()):
    return ReviewProjection(tuple(items), (date(2027, 1, 1), date(2027, 2, 1)), (), (),
                            folded_points=tuple(folded))


def note(identifier, kind="note"):
    return {"kind": kind, "text": f"Note for {identifier}", "anchor": {"object": identifier}}


def explicit(identifier="custom", reference="alpha", *, placement=True):
    value = {"id": identifier, "purpose": "note", "projectAnnotation": reference,
             "anchor": {"kind": "object", "id": "task", "facet": "planned", "endpoint": "end"}}
    if placement:
        value["placement"] = {"side": "start", "alignment": "end"}
    return value


def test_binding_then_key_order_preserves_project_text_and_anchor_without_mutation():
    notes = {"z-span": note("task"), "risk": note("task", "risk"),
             "gate": note("gate"), "a-span": note("task")}
    before = deepcopy(notes)
    result = expand_annotations(view(), notes, projection(item("task"), item("gate", "point")))
    assert [entry.value["id"] for entry in result] == ["gate-note", "risk-note", "a-span-note", "z-span-note"]
    assert [entry.value["anchor"]["endpoint"] for entry in result] == ["at", "body", "end", "end"]
    assert [entry.value["anchor"]["facet"] for entry in result] == ["planned", "actual", "planned", "planned"]
    assert notes == before
    assert all("text" not in entry.value for entry in result)
    assert [entry.anchor_source_ref for entry in result] == [
        "/annotations/gate/anchor", "/annotations/risk/anchor", "/annotations/a-span/anchor", "/annotations/z-span/anchor"]
    with pytest.raises(TypeError):
        result[0].value["anchor"]["id"] = "changed"


def test_project_mapping_order_cannot_change_expansion():
    notes = {"b": note("task"), "a": note("task")}
    projected = projection(item("task"))
    assert expand_annotations(view(), notes, projected) == expand_annotations(view(), dict(reversed(list(notes.items()))), projected)


def test_first_matching_binding_wins_without_duplicate_ghosts():
    bindings = [{**BINDINGS[2], "temporalKind": "any"}, BINDINGS[2]]
    current = item("task", source="combined")
    projected = projection(current, replace(current, source_kind="snapshot"))
    assert len(expand_annotations(view(bindings=bindings), {"a": note("task")}, projected)) == 1


def test_unselected_and_unknown_kind_notes_are_not_consumed():
    notes = {"outside": note("outside"), "unknown": note("task", "incident"), "shown": note("task")}
    result = expand_annotations(view(), notes, projection(item("task")))
    assert [entry.value["projectAnnotation"] for entry in result] == ["shown"]


def test_folded_points_are_selected_semantically():
    folded = FoldedPointProjection(item("gate", "point"), "group")
    result = expand_annotations(view(), {"a": note("gate")}, projection(folded=(folded,)))
    assert result[0].value["anchor"]["endpoint"] == "at"


def test_explicit_reference_overrides_automatic_and_keeps_original_order():
    declared = [explicit("second", "beta"), explicit("first", "alpha"), explicit("another", "alpha")]
    result = expand_annotations(view(annotations=declared),
                                {key: note("task") for key in ("alpha", "beta", "gamma")}, projection(item("task")))
    assert [entry.value["id"] for entry in result] == ["second", "first", "another", "gamma-note"]
    assert result[0].value["placement"] == {"side": "start", "alignment": "end"}
    assert result[0].anchor_source_ref == "/body/annotations/0/anchor"
    assert result[0].placement_source_ref == "/body/annotations/0/placement"
    assert replace(result[0], placement_source_ref="/body/annotationPlacement/note") == result[0]
    assert "placement_source_ref" not in repr(result[0])


def test_explicit_missing_placement_inherits_whole_purpose_policy():
    parsed = view(annotations=[explicit(placement=False)])
    assert parsed.annotations[0]["placement"] == POLICY["note"]["placement"]
    expanded = expand_annotations(parsed, {}, projection(item("task")))
    assert expanded[0].placement_source_ref == "/body/annotationPlacement/note"


def test_automatic_annotation_retains_the_policy_source_not_a_fake_view_ordinal():
    expanded = expand_annotations(view(), {"alpha": note("task")}, projection(item("task")))
    assert expanded[0].placement_source_ref == "/body/annotationPlacement/note"


def test_explicit_candidate_policy_retains_its_authored_field_pointer():
    annotation = explicit(placement=False)
    annotation["candidates"] = [sr.candidate("plot", connector="none")]
    expanded = expand_annotations(view(annotations=[annotation]), {}, projection(item("task")))
    assert expanded[0].placement_source_ref == "/body/annotations/0/candidates"


def test_missing_placement_without_opt_in_remains_schema_invalid():
    with pytest.raises(SchemaContractError):
        view(bindings=None, policy=None, annotations=[explicit(placement=False)])


def test_explicit_missing_policy_is_a_typed_declared_source_failure():
    with pytest.raises(ContractError) as error:
        view(policy={}, annotations=[explicit(placement=False)])
    assert error.value.diagnostic_id == "E_PRESENTATION_ANNOTATION_POLICY_MISSING"
    assert error.value.source_ref == "/body/annotationPlacement/note"


def test_automatic_missing_policy_is_not_silently_skipped():
    with pytest.raises(ContractError) as error:
        expand_annotations(view(policy={}), {"alpha": note("task")}, projection(item("task")))
    assert error.value.diagnostic_id == "E_PRESENTATION_ANNOTATION_POLICY_MISSING"
    assert error.value.source_ref == "/body/annotationPlacement/note"


def test_generated_collision_lists_both_real_declared_sources():
    with pytest.raises(ContractError) as error:
        expand_annotations(view(annotations=[explicit("alpha-note", "beta")]),
                           {"alpha": note("task"), "beta": note("task")}, projection(item("task")))
    assert error.value.diagnostic_id == "E_PRESENTATION_ANNOTATION_IDENTITY"
    assert error.value.source_ref == "/annotations/alpha/anchor"
    assert "/body/annotations/0/anchor" in error.value.detail


def test_project_pointer_escapes_annotation_key():
    result = expand_annotations(view(), {"a/b~c": note("task")}, projection(item("task")))
    assert result[0].anchor_source_ref == "/annotations/a~1b~0c/anchor"


def test_policy_overlay_is_whole_member_including_explicit_empty_map():
    raw = sr.bundle()["view"]
    original = deepcopy(raw)
    offered = {"annotationPlacement": deepcopy(POLICY)}
    assert merge_view_defaults(raw, offered)["body"]["annotationPlacement"] == POLICY
    assert raw == original
    raw["body"]["annotationPlacement"] = {}
    assert merge_view_defaults(raw, offered)["body"]["annotationPlacement"] == {}
    assert offered == {"annotationPlacement": POLICY}


@pytest.mark.parametrize("field,value", [("temporalKind", "painted-point"), ("facet", "snapshot"),
                                        ("endpoint", "middle"), ("object", "task")])
def test_binding_vocabulary_is_closed(field, value):
    bad = {**BINDINGS[0], field: value}
    with pytest.raises(SchemaContractError):
        view(bindings=[bad])


def test_purpose_policy_reuses_candidate_and_legacy_exclusion():
    with pytest.raises(SchemaContractError):
        view(policy={"note": {"placement": POLICY["note"]["placement"], "candidates": []}})


@pytest.mark.parametrize("member,value", [("annotationBindings", BINDINGS), ("annotationPlacement", POLICY)])
def test_network_rejects_new_intent_instead_of_ignoring_it(member, value):
    raw = sr.bundle()["view"]
    body = raw["body"]
    body["surface"] = "dependency-network"
    body["rows"] = {"mode": "automatic"}
    body["visibility"]["labels"] = False
    for name in ("tableColumns", "hierarchyColumn", "backgroundDecoration", "axis", "markers", "periods",
                 "deadlines", "shading", "timePresentation", "annotations", "annotationPresentation"):
        body.pop(name, None)
    identity = ClosureIdentity("view", raw["id"], "r", "sha256:" + "a" * 64)
    parse_contract(identity, raw)  # positive control: no unrelated rejection.
    body[member] = deepcopy(value)
    with pytest.raises(SchemaContractError):
        parse_contract(identity, raw)


def test_undrawn_project_annotations_name_only_notes_on_a_drawn_target():
    from chrona.presentation.review.annotation_expansion import undrawn_project_annotations
    notes = {"b": note("gate", "risk"), "a": note("task"), "c": note("hidden"), "d": note("task")}
    shown = projection(item("task"), item("gate", "point"), item("hidden", source="context"))

    assert undrawn_project_annotations(notes, shown, ["d", "c", "b", "a", "missing"]) == (
        ("a", "note", "task", "span"), ("b", "risk", "gate", "point"), ("d", "note", "task", "span"))
