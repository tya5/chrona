from chrona.operational.resources import OperationalResourceError, canonical_bytes, content_identity, parse_document


def test_intake_batch_parses_and_has_stable_identity_for_yaml_dates():
    value = parse_document(
        """version: chrona/actual-intake-batch/v0.2
kind: actual-intake-batch
id: batch-1
body:
  source: {system: supplier, contentIdentity: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa}
  records:
    - externalKey: supplier-42
      actual: {finish: 2026-04-18}
""",
        "actual-intake-batch-v0.2.schema.yaml",
    )
    assert value["body"]["records"][0]["actual"]["finish"] == "2026-04-18"
    assert content_identity(value).startswith("sha256:")
    assert canonical_bytes(value) == canonical_bytes(dict(value))


def test_command_v02_requires_a_complete_immutable_target_reference():
    payload = """version: chrona/command/v0.2
commandId: bad
type: captureSnapshot
target: {id: p, kind: project}
baseRevision: revision-1
expectedContentIdentity: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
payload: {snapshotId: baseline, registry: {id: r}}
"""
    try:
        parse_document(payload, "command-request-v0.2.schema.yaml")
    except OperationalResourceError as error:
        assert error.code == "E_OPERATIONAL_SCHEMA"
    else:
        raise AssertionError("expected schema rejection")


def test_operational_schema_error_uses_a_stable_pointer_and_explanation():
    try:
        parse_document("version: chrona/command/v0.2\ncommandId: bad\ntype: unknown\ntarget: {}\nbaseRevision: r\npayload: {}\n", "command-request-v0.2.schema.yaml")
    except OperationalResourceError as error:
        assert error.code == "E_OPERATIONAL_SCHEMA"
        assert "expected minProperties 1" in str(error)
        assert "should be non-empty" not in str(error)
    else:
        raise AssertionError("expected schema rejection")


def test_actual_set_v02_requires_provenance_for_external_facts():
    payload = """version: chrona/actual-set/v0.2
kind: actual-set
id: actuals
body:
  observations:
    - id: external-1
      sequence: 1
      externalIdentity: {system: supplier, key: 1}
      actual: {finish: '2026-04-18'}
"""
    try:
        parse_document(payload, "actual-set-v0.2.schema.yaml")
    except OperationalResourceError as error:
        assert error.code == "E_OPERATIONAL_SCHEMA"
    else:
        raise AssertionError("expected provenance rejection")
