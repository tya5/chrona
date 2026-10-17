from dataclasses import FrozenInstanceError

import pytest

from chrona.presentation.model.field_roles import (
    FieldDescriptor,
    FieldRead,
    FieldRoleBindings,
)


def test_direct_and_role_alias_reads_share_exact_object_descriptor():
    bindings = FieldRoleBindings.from_project(
        {"fieldRoles": {"responsible": "owner"}},
        object_descriptors={
            "task-1": (FieldDescriptor("owner", "enum", enum_values=("team-a",)),),
        },
    )
    fields = {"owner": "team-a"}

    direct = bindings.read_result(fields, {"field": "owner"}, object_id="task-1")
    alias = bindings.read_result(fields, {"fieldRole": "responsible"}, object_id="task-1")

    assert direct == alias == FieldRead(
        "owner", True, "team-a", FieldDescriptor("owner", "enum", "one", ("team-a",))
    )
    assert bindings.read(fields, {"fieldRole": "responsible"}) == "team-a"


def test_descriptor_is_source_object_specific_even_for_reused_object_ids():
    primary = FieldRoleBindings.from_project(
        {"fieldRoles": {"risk": "severity"}},
        object_descriptors={
            "same-id": (FieldDescriptor("severity", "enum", enum_values=("high",)),),
        },
    )
    snapshot = FieldRoleBindings.from_project(
        {"fieldRoles": {"risk": "severity"}},
        object_descriptors={
            "same-id": (FieldDescriptor("severity", "string"),),
        },
    )

    primary_read = primary.read_result({"severity": "high"}, {"fieldRole": "risk"}, object_id="same-id")
    snapshot_read = snapshot.read_result({"severity": "high"}, {"fieldRole": "risk"}, object_id="same-id")

    assert primary_read.descriptor == FieldDescriptor("severity", "enum", enum_values=("high",))
    assert snapshot_read.descriptor == FieldDescriptor("severity", "string")


def test_descriptor_metadata_preserves_absent_null_false_and_zero():
    bindings = FieldRoleBindings(object_descriptors={
        "item": (
            FieldDescriptor("nullable", "string"),
            FieldDescriptor("enabled", "boolean"),
            FieldDescriptor("count", "integer"),
        ),
    })

    missing = bindings.read_result({}, {"field": "nullable"}, object_id="item")
    null = bindings.read_result({"nullable": None}, {"field": "nullable"}, object_id="item")
    false = bindings.read_result({"enabled": False}, {"field": "enabled"}, object_id="item")
    zero = bindings.read_result({"count": 0}, {"field": "count"}, object_id="item")

    assert missing == FieldRead("nullable", False, None, FieldDescriptor("nullable", "string"))
    assert null == FieldRead("nullable", True, None, FieldDescriptor("nullable", "string"))
    assert false == FieldRead("enabled", True, False, FieldDescriptor("enabled", "boolean"))
    assert zero == FieldRead("count", True, 0, FieldDescriptor("count", "integer"))


def test_descriptor_constructor_detaches_mutable_input_and_is_immutable():
    enum_values = ["low", "high"]
    descriptor = FieldDescriptor("risk", "enum", enum_values=enum_values)
    descriptors = [descriptor]
    object_descriptors = {"item": descriptors}
    role_map = {"riskRole": "risk"}
    bindings = FieldRoleBindings.from_project(
        {"fieldRoles": role_map}, object_descriptors=object_descriptors
    )

    enum_values.append("critical")
    descriptors.clear()
    object_descriptors["item"] = ()
    role_map["riskRole"] = "other"

    assert descriptor.enum_values == ("low", "high")
    assert bindings.descriptor_for("item", "risk") == descriptor
    assert bindings.field_for("riskRole") == "risk"
    with pytest.raises(FrozenInstanceError):
        descriptor.kind = "string"
    with pytest.raises(FrozenInstanceError):
        bindings.object_descriptors = ()
    with pytest.raises(TypeError):
        bindings._descriptor_lookup["other"] = {}


@pytest.mark.parametrize(
    "object_descriptors",
    [
        (("item", (FieldDescriptor("risk", "string"),)),
         ("item", (FieldDescriptor("other", "string"),))),
        (("item", (FieldDescriptor("risk", "string"),
                    FieldDescriptor("risk", "enum"))),),
    ],
)
def test_duplicate_descriptor_identity_is_rejected(object_descriptors):
    with pytest.raises(ValueError, match="duplicate"):
        FieldRoleBindings(object_descriptors=object_descriptors)


def test_legacy_bindings_without_object_metadata_keep_opaque_read_contract():
    bindings = FieldRoleBindings.from_project({"fieldRoles": {"risk": "risk"}})

    assert bindings.read_result({"risk": 0}, {"fieldRole": "risk"}, object_id="item") == FieldRead(
        "risk", True, 0, None
    )
    assert bindings.read({"risk": 0}, {"fieldRole": "risk"}) == 0
