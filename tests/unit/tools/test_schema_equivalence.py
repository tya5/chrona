"""Sensitivity, pass-case and coverage tests for the schema validation-equivalence gate (I662-S0)."""
from copy import deepcopy
import dataclasses
from pathlib import Path
import re
import shutil

import pytest
import yaml

from chrona import schema_diagnostics
from tools import schema_equivalence as gate
from tools.schema_inventory import validate_inventory


REPOSITORY = Path(__file__).resolve().parents[3]
SCHEMAS = REPOSITORY / "schemas"
# The pattern-edit sensitivity tests need a live schema that keeps one inline pattern and is referenced by no other schema.
PATTERN_SCHEMA = "example-registry-v0.1.schema.yaml"
PATTERN_POINTER = "/properties/examples/items/properties/path/pattern"
PATTERN_TEXT = "^examples/[a-z][a-z0-9-]*$"
STORE_CONFIG = "store-config-v0.1.schema.yaml"


def _copy_schemas(tmp_path: Path) -> Path:
    destination = tmp_path / "schemas"
    shutil.copytree(SCHEMAS, destination, ignore=shutil.ignore_patterns("__pycache__"))
    return destination


def _edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"{old!r} must occur once in {path.name}"
    path.write_text(text.replace(old, new), encoding="utf-8")


def _l1(base: dict, head: dict, deltas: list | None = None) -> dict[str, gate.L1Row]:
    rows = gate.compare_l1(gate.fingerprint_schemas(base), gate.fingerprint_schemas(head), deltas or [])
    return {row.schema: row for row in rows}


def _delta(pointer: str, before, after, schema: str = PATTERN_SCHEMA) -> gate.Delta:
    return gate.Delta("L1", schema, pointer, before, after, "test", "test_schema_equivalence")


@pytest.fixture(scope="module")
def base_schemas() -> dict:
    return gate.load_schema_dir(SCHEMAS)


@pytest.fixture(scope="module")
def committed() -> gate.GateReport:
    """One L2 plus L3 run over the committed tree; it is also the runtime record."""
    return gate.run_gate(REPOSITORY, layers=("L2", "L3"))


# --- the committed tree -----------------------------------------------------------------------

def test_gate_passes_on_the_committed_tree(committed, base_schemas):
    assert committed.failures == []
    report = gate.run_gate(REPOSITORY, layers=("L1",), base_schemas=base_schemas)
    assert report.failures == []
    assert {row.status for row in report.l1} == {"equal"}


def test_l2_and_l3_stay_inside_the_runtime_budget(committed):
    elapsed = committed.timings["L2"] + committed.timings["L3"]

    assert elapsed < gate.RUNTIME_BUDGET_SECONDS, f"L2+L3 took {elapsed:.1f}s"
    assert committed.corpus is not None and len(committed.corpus.records) >= 200


def test_every_live_kind_has_a_document_or_a_probe(committed):
    entries = validate_inventory(SCHEMAS, SCHEMAS / "schema-inventory-v0.1.yaml")

    assert gate._coverage_failures(entries, committed.corpus.records, gate.PROBE_SITES) == []
    assert not [failure for failure in committed.failures if "KIND_UNCOVERED" in failure]


def test_coverage_check_names_a_live_kind_that_loses_every_probe_and_document(committed):
    entries = validate_inventory(SCHEMAS, SCHEMAS / "schema-inventory-v0.1.yaml")
    sites = tuple(site for site in gate.PROBE_SITES if site.kind != "store-config")

    failures = gate._coverage_failures(entries, committed.corpus.records, sites)

    assert failures and all("store-config" in failure for failure in failures)


def test_expected_invalid_list_equals_the_baseline_invalid_documents():
    baseline = gate.load_baseline(REPOSITORY / gate.BASELINE)
    listed = gate.load_expected_invalid(REPOSITORY / gate.EXPECTED_INVALID)

    # The baseline names the schema a document mapped to at S0; a document re-pointed to a successor (I710-S-B)
    # is listed under the successor, which the inventory names. A predecessor retired since (#731) has no inventory
    # entry any more: it resolves to the live schema of its kind (the file name minus its version).
    entries = validate_inventory(SCHEMAS, SCHEMAS / "schema-inventory-v0.1.yaml")
    successor = {entry["file"]: entry.get("successor", entry["file"]) for entry in entries}
    live = {re.sub(r"-v\d+\.\d+\.schema\.yaml$", "", entry["file"]): entry["file"] for entry in entries if entry["state"] == "live"}

    def current(schema: str) -> str:
        return successor.get(schema) or live.get(re.sub(r"-v\d+\.\d+\.schema\.yaml$", "", schema), schema)

    invalid = {record["path"]: current(record["schema"]) for record in baseline["documents"] if not record["valid"]}

    assert invalid == {path: entry["schema"] for path, entry in listed.items()}
    assert set(baseline["diagnostics"]["invalidDocuments"]) == set(listed)
    assert all(entry["reason"].strip() for entry in listed.values())


def test_the_gate_reads_no_production_loader():
    source = (REPOSITORY / "tools" / "schema_equivalence.py").read_text(encoding="utf-8")
    imports = re.findall(r"^\s*(?:from|import)\s+(chrona[\w.]*)", source, flags=re.MULTILINE)

    assert "chrona.resources" not in imports
    assert not re.search(r"\b(schema_document|schema_resource|schema_registry|schema_validator)\(", source)
    # Production code is reached only by the L3 ingress functions, never by the schema-reading layers.
    layers_one_and_two = source.split("# L3: diagnostics through the production ingress functions")[0]
    assert not re.search(r"^\s*(?:from|import)\s+chrona", layers_one_and_two, flags=re.MULTILINE)


# --- the document-to-schema mapping -----------------------------------------------------------

def test_mapping_is_derived_from_version_constants_and_the_overrides_agree(base_schemas):
    derived = {}
    for name, schema in base_schemas.items():
        version = gate._declared_version(schema)
        if version is not None:
            derived.setdefault(version, []).append(name)

    mapping = gate.derive_version_map(base_schemas)

    assert mapping["timeline/v0.7"] == "project-v0.7.schema.yaml"
    assert mapping["chrona/view/v0.28"] == "view-v0.28.schema.yaml"
    for version, name in gate.VERSION_OVERRIDES.items():
        assert derived.get(version) == [name], f"the override for {version} contradicts the derivation"


def test_scene_documents_are_mapped_to_their_declared_versions(committed):
    # Completed endpoint identities select v0.7; legacy Scenes still select v0.6.
    schemas = {"scene-v0.6.schema.yaml", "scene-v0.7.schema.yaml"}
    scenes = [record for record in committed.corpus.records if record["schema"] in schemas]

    assert len(scenes) >= 29
    assert {record["schema"] for record in scenes} == schemas
    assert all(record["valid"] for record in scenes)


def test_scene_ingress_keeps_serialization_detail_out_of_the_diagnostic_code():
    document = {"version": "chrona/scene/v0.6", "kind": "bogus"}

    diagnostic = gate._ingress_scene(document, "scene-v0.6.schema.yaml")

    assert diagnostic is not None
    assert diagnostic == {"code": "E_SCENE_SERIALIZATION", "pointer": "", "rule": "", "message": ""}


def test_registry_holds_every_schema_id_and_resolves_urn_references(base_schemas):
    registry = gate.build_registry(base_schemas)

    for schema in base_schemas.values():
        assert registry.get(schema["$id"]) is not None
    assert gate.SchemaValidators(base_schemas).first_error("view-v0.28.schema.yaml", {"version": "chrona/view/v0.28"}) is not None


# --- sensitivity: each of these must fail the gate ---------------------------------------------

def test_editing_one_pattern_in_a_copied_schema_fails_l1_with_the_pointer(tmp_path, base_schemas):
    copied = _copy_schemas(tmp_path)
    _edit(copied / PATTERN_SCHEMA, f'"{PATTERN_TEXT}"', '"^examples/[a-z][a-z0-9-]{1}$"')

    report = gate.run_gate(REPOSITORY, layers=("L1",), base_schemas=base_schemas, schemas_dir=copied,
                           inventory_path=copied / "schema-inventory-v0.1.yaml")

    assert not report.passed
    assert any(PATTERN_SCHEMA in failure and PATTERN_POINTER in failure
               for failure in report.failures)


def test_making_a_valid_document_invalid_fails_l2():
    path = "conformance/calendar.yaml"
    content = (REPOSITORY / path).read_bytes() + b"unexpectedTopLevelKey: true\n"

    report = gate.run_gate(REPOSITORY, layers=("L2",), documents={path: content})

    assert not report.passed
    assert any(failure.startswith(f"L2 {path}: valid -> invalid") for failure in report.failures)


def test_a_new_invalid_document_that_is_not_listed_fails_l2():
    document = b"version: timeline/v0.7\nunexpectedTopLevelKey: true\n"

    report = gate.run_gate(REPOSITORY, layers=("L2",), documents={"docs/new-plan.yaml": document})

    assert any("docs/new-plan.yaml" in failure and "not listed in expected-invalid" in failure
               for failure in report.failures)


def test_a_listed_invalid_document_that_becomes_valid_fails_l2():
    path = "conformance/layout-profile-invalid-offset-v0.2.yaml"
    document = yaml.safe_load((REPOSITORY / path).read_text(encoding="utf-8"))
    del document["root"]["children"][0]["offsetX"]
    content = yaml.safe_dump(document).encode()

    report = gate.run_gate(REPOSITORY, layers=("L2",), documents={path: content})

    assert any(path in failure for failure in report.failures)


def test_changing_a_diagnostic_message_fails_l3(monkeypatch):
    sites = tuple(site for site in gate.PROBE_SITES
                  if site.source == "inline:authoring-command-task" and site.pointer == "/baseRevision")
    original = schema_diagnostics._explain

    def reworded(error):
        violation = original(error)
        return dataclasses.replace(violation, message=violation.message + " (reworded)")

    assert gate.run_gate(REPOSITORY, layers=("L3",), documents={}, sites=sites).failures == []
    monkeypatch.setattr(schema_diagnostics, "_explain", reworded)
    report = gate.run_gate(REPOSITORY, layers=("L3",), documents={}, sites=sites)

    assert not report.passed
    assert any(failure.startswith("L3 authoring-command|inline:authoring-command-task/baseRevision") and "reworded" in failure
               for failure in report.failures)


def test_removing_an_inventory_entry_fails_the_gate(tmp_path, base_schemas):
    copied = _copy_schemas(tmp_path)
    inventory = copied / "schema-inventory-v0.1.yaml"
    lines = inventory.read_text(encoding="utf-8").splitlines(keepends=True)
    kept = [line for line in lines if STORE_CONFIG not in line]
    assert len(kept) == len(lines) - 1
    inventory.write_text("".join(kept), encoding="utf-8")

    report = gate.run_gate(REPOSITORY, layers=("L1",), base_schemas=base_schemas, schemas_dir=copied,
                           inventory_path=inventory)

    assert not report.passed
    assert any("E_SCHEMA_INVENTORY_COVERAGE" in failure and STORE_CONFIG in failure for failure in report.failures)


def test_removing_a_schema_without_a_delta_fails_l1(base_schemas):
    head = {name: schema for name, schema in base_schemas.items() if name != STORE_CONFIG}

    assert _l1(base_schemas, head)[STORE_CONFIG].status == "changed"


# --- pass cases ---------------------------------------------------------------------------------

def test_an_added_optional_property_passes_l1(base_schemas):
    head = deepcopy(base_schemas)
    stores = head[STORE_CONFIG]["properties"]["stores"]["items"]
    stores["properties"]["label"] = {"description": "Optional display label.", "type": "string"}

    rows = _l1(base_schemas, head)

    assert rows[STORE_CONFIG].status == "additive"
    assert all(row.status == "equal" for name, row in rows.items() if name != STORE_CONFIG)


def test_an_added_required_property_fails_l1(base_schemas):
    head = deepcopy(base_schemas)
    stores = head[STORE_CONFIG]["properties"]["stores"]["items"]
    stores["properties"]["label"] = {"description": "Required label.", "type": "string"}
    stores["required"] = [*stores["required"], "label"]

    assert _l1(base_schemas, head)[STORE_CONFIG].status == "changed"


def test_a_listed_delta_applied_exactly_passes_and_a_wrong_after_fails(base_schemas):
    head = deepcopy(base_schemas)
    after = "^examples/[a-z][a-z0-9-]*(?![\\s\\S])"
    head[PATTERN_SCHEMA]["properties"]["examples"]["items"]["properties"]["path"]["pattern"] = after
    pointer, before = PATTERN_POINTER, PATTERN_TEXT

    exact = _delta(pointer, before, after)
    rows = _l1(base_schemas, head, [exact])
    assert rows[PATTERN_SCHEMA].status == "delta" and exact.used

    assert _l1(base_schemas, head)[PATTERN_SCHEMA].status == "changed"
    wrong = _delta(pointer, before, "^examples/[a-z][a-z0-9-]{2}$")
    assert _l1(base_schemas, head, [wrong])[PATTERN_SCHEMA].status == "changed"
    wrong_before = _delta(pointer, "^something-else$", after)
    assert _l1(base_schemas, head, [wrong_before])[PATTERN_SCHEMA].status == "changed"


def test_a_delta_that_already_landed_in_the_base_is_reported_unused_not_failed(base_schemas):
    landed = _delta(PATTERN_POINTER, "^old$", PATTERN_TEXT)

    assert _l1(base_schemas, deepcopy(base_schemas), [landed])[PATTERN_SCHEMA].status == "equal"


def test_a_pure_local_ref_replacement_of_an_identical_inline_definition_keeps_l1_equal(base_schemas):
    head = deepcopy(base_schemas)
    schema = head[STORE_CONFIG]
    stores = schema["properties"]["stores"]["items"]
    inline = stores["properties"]["identity"]
    schema["$defs"] = {"storeIdentity": {"description": "Shared definition.", "type": "string", "minLength": 1}}
    stores["properties"]["identity"] = {"$ref": "#/$defs/storeIdentity"}
    assert inline["type"] == "string" and inline["minLength"] == 1

    assert _l1(base_schemas, head)[STORE_CONFIG].status == "equal"


def test_a_pure_external_urn_ref_replacement_keeps_l1_equal_and_a_new_part_is_allowed(base_schemas):
    head = deepcopy(base_schemas)
    head["common-test-v0.1.schema.yaml"] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "urn:chrona:common-test-v0.1",
        "title": "Test part", "description": "A definitions-only part.",
        "$defs": {"nonEmpty": {"description": "Non-empty text.", "type": "string", "minLength": 1}}}
    stores = head[STORE_CONFIG]["properties"]["stores"]["items"]
    stores["properties"]["identity"] = {"$ref": "urn:chrona:common-test-v0.1#/$defs/nonEmpty",
                                        "description": "Stable Store identity."}

    rows = _l1(base_schemas, head)

    assert rows[STORE_CONFIG].status == "equal"
    assert rows["common-test-v0.1.schema.yaml"].status == "added"


def test_a_ref_with_a_sibling_constraint_is_not_folded_when_it_would_change_meaning(base_schemas):
    head = deepcopy(base_schemas)
    schema = head[STORE_CONFIG]
    schema["$defs"] = {"identity": {"type": "string", "minLength": 2}}
    schema["properties"]["stores"]["items"]["properties"]["identity"] = {"$ref": "#/$defs/identity", "minLength": 1}

    assert _l1(base_schemas, head)[STORE_CONFIG].status == "changed"


def test_an_unresolvable_reference_is_a_gate_error(base_schemas):
    head = deepcopy(base_schemas)
    head[STORE_CONFIG]["properties"]["stores"]["items"]["properties"]["identity"] = {"$ref": "urn:chrona:missing-v0.1"}

    with pytest.raises(gate.GateError, match="E_EQUIV_REF_UNRESOLVED"):
        gate.fingerprint_schemas(head)


def test_l1_fingerprints_ignore_annotations_and_unused_defs(base_schemas):
    head = deepcopy(base_schemas)
    head[STORE_CONFIG]["description"] = "Reworded."
    head[STORE_CONFIG]["properties"]["stores"]["description"] = "Reworded too."
    head[STORE_CONFIG]["$defs"] = {"unused": {"type": "integer"}}

    assert _l1(base_schemas, head)[STORE_CONFIG].status == "equal"


# --- L2 and L3 record comparison ----------------------------------------------------------------

def test_a_listed_l2_delta_excuses_exactly_that_verdict_change():
    before = {"path": "a.yaml", "schema": "s", "valid": True, "error": None}
    after = {"path": "a.yaml", "schema": "s", "valid": False, "error": {"pointer": "/x", "rule": "pattern"}}
    excuse = gate.Delta("L2", "a.yaml", "", before, after, "test", "test_schema_equivalence")
    elsewhere = gate.Delta("L2", "b.yaml", "", before, after, "test", "test_schema_equivalence")

    failures, _ = gate.compare_records("L2", {"a.yaml": before}, {"a.yaml": after}, [excuse])
    assert failures == [] and excuse.used
    failures, _ = gate.compare_records("L2", {"a.yaml": before}, {"a.yaml": after}, [elsewhere])
    assert len(failures) == 1


def test_a_listed_l3_delta_excuses_exactly_that_message_change():
    before = {"code": "E", "pointer": "/x", "rule": "pattern", "message": "old"}
    after = {"code": "E", "pointer": "/x", "rule": "pattern", "message": "new"}
    wrong = {**after, "message": "other"}
    excuse = gate.Delta("L3", "probe-1", "", before, after, "test", "test_schema_equivalence")

    assert gate.compare_records("L3", {"probe-1": before}, {"probe-1": after}, [excuse])[0] == []
    assert gate.compare_records("L3", {"probe-1": before}, {"probe-1": wrong}, [excuse])[0]


# --- the probe matrix ---------------------------------------------------------------------------

def test_every_probe_base_document_is_valid_and_every_pointer_exists(committed):
    validators = gate.SchemaValidators(gate.load_schema_dir(SCHEMAS))
    documents = gate.tracked_documents(REPOSITORY)
    corpus = gate._load_corpus(documents, sorted({site.source for site in gate.PROBE_SITES
                                                  if not site.source.startswith("inline:")}))
    checked: set = set()
    for site in gate.PROBE_SITES:
        document = gate.probe_documents(site, corpus)
        gate._set_at(deepcopy(document), site.pointer, "x")  # the pointer names an existing value
        if (site.source, repr(site.repair)) in checked:
            continue
        checked.add((site.source, repr(site.repair)))
        schema = validators.version_map[document["version"]]
        assert validators.first_error(schema, document) is None, site.source
        assert gate.run_ingress(document, validators) is None, site.source


def test_probe_matrix_names_the_strings_the_design_lists():
    values = {family: {value for _, value in strings} for family, strings in gate.PROBE_STRINGS.items()}

    assert {"2026-13-45", "2026-02-30", "２０２６-09-30", "2026-09-30\n"} <= values["date"]
    assert {"sha256:" + "a" * 64 + "\n"} <= values["sha256"]
    assert {"../escape.yaml", "a\x00b.yaml", "a\\b.yaml", "a.yaml\n", "my plan.yaml", "計画.yaml"} <= values["path"]
    assert {"", "has space", "計画"} <= values["identifier"]
    assert len(values["endpoint"]) == 6 and {"finish", "end"} <= values["endpoint"]


def test_probe_ids_are_unique():
    identifiers = [gate.probe_id(site, label) for site in gate.PROBE_SITES for label, _ in gate.PROBE_STRINGS[site.family]]

    assert len(identifiers) == len(set(identifiers))


def test_baseline_records_accepted_and_rejected_probe_verdicts():
    probes = gate.load_baseline(REPOSITORY / gate.BASELINE)["diagnostics"]["probes"]

    assert any(record is None for record in probes.values())
    assert any(record is not None for record in probes.values())
    # An impossible date is accepted by every pattern-only date site today (design D2).
    impossible = [record for name, record in probes.items() if name.endswith("date:impossible-month")]
    assert impossible and all(record is None or record["rule"] != "pattern" for record in impossible)
