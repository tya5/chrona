from types import SimpleNamespace

from chrona.presentation.model.field_roles import FieldDescriptor, FieldRoleBindings
from chrona.presentation.model.style_rules import StyleFieldFact, field_facts_for_item


def _item(fields, bindings, object_id="task-1"):
    return SimpleNamespace(object_id=object_id, fields=fields, field_bindings=bindings)


def test_direct_and_role_sources_share_one_typed_fact_with_source_local_alias():
    bindings = FieldRoleBindings.from_project(
        {"fieldRoles": {"responsible": "owner", "assignee": "owner"}},
        object_descriptors={"task-1": (FieldDescriptor("owner", "enum", enum_values=("A", "B")),)},
    )

    (fact,) = field_facts_for_item(_item({"owner": "A"}, bindings))

    assert fact == StyleFieldFact("owner", "enum", True, "A", "one", ("A", "B"),
                                  ("assignee", "responsible"))
    assert bindings.read_result({"owner": "A"}, {"field": fact.name}, object_id="task-1").value == fact.value
    assert bindings.read_result({"owner": "A"}, {"fieldRole": "responsible"},
                                object_id="task-1").field_name == fact.name


def test_same_object_id_uses_each_source_binding_descriptor():
    primary = FieldRoleBindings.from_project({}, object_descriptors={
        "task-1": (FieldDescriptor("risk", "enum", enum_values=("high",)),),
    })
    snapshot = FieldRoleBindings.from_project({}, object_descriptors={
        "task-1": (FieldDescriptor("risk", "string"),),
    })

    (primary_fact,) = field_facts_for_item(_item({"risk": "high"}, primary))
    (snapshot_fact,) = field_facts_for_item(_item({"risk": "high"}, snapshot))

    assert primary_fact.kind == "enum" and primary_fact.enum_values == ("high",)
    assert snapshot_fact.kind == "string" and snapshot_fact.enum_values == ()


def test_declared_absent_and_null_fields_preserve_presence_and_cardinality():
    bindings = FieldRoleBindings(object_descriptors={"task-1": (
        FieldDescriptor("missing", "string"),
        FieldDescriptor("nullable", "string"),
        FieldDescriptor("many", "integer", "many"),
    )})

    facts = {fact.name: fact for fact in field_facts_for_item(
        _item({"nullable": None, "many": [1, 2]}, bindings))}

    assert facts["missing"] == StyleFieldFact("missing", "string", False, None)
    assert facts["nullable"] == StyleFieldFact("nullable", "string", True, None)
    assert facts["many"].present and facts["many"].value is None
    assert facts["many"].cardinality == "many"


def test_legacy_fields_stay_opaque_and_scalar_runtime_types_are_not_inferred():
    bindings = FieldRoleBindings.from_project({"fieldRoles": {"flagRole": "flag"}})
    fields = {"flag": False, "count": 0, "ratio": 1.5, "labels": ["x"]}

    facts = {fact.name: fact for fact in field_facts_for_item(_item(fields, bindings))}

    assert facts["flag"] == StyleFieldFact("flag", None, True, False, aliases=("flagRole",))
    assert facts["count"] == StyleFieldFact("count", None, True, 0)
    assert facts["ratio"] == StyleFieldFact("ratio", None, True, 1.5)
    assert facts["labels"] == StyleFieldFact("labels", None, True, None)


def test_fact_snapshot_does_not_mutate_item_or_descriptor_inputs():
    enum_values = ["low", "high"]
    descriptor_list = [FieldDescriptor("risk", "enum", enum_values=enum_values)]
    bindings = FieldRoleBindings(object_descriptors={"task-1": descriptor_list})
    fields = {"risk": "high", "extra": {"nested": True}}
    before = dict(fields)

    facts = field_facts_for_item(_item(fields, bindings))

    assert fields == before
    assert facts[0].enum_values == ("low", "high")
    assert facts[1].value is None and facts[1].present
    enum_values.append("critical")
    descriptor_list.clear()
    assert facts[0].enum_values == ("low", "high")
    assert bindings.descriptors_for("task-1")
