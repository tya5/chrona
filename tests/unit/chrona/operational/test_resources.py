from chrona.operational.resources import OperationalResourceError, canonical_bytes, content_identity, parse_document


def test_intake_batch_parses_and_has_stable_identity_for_yaml_dates():
    value = parse_document(
        """version: chrona/actual-intake-batch/v0.1
batchId: batch-1
source: {system: supplier, contentIdentity: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa}
records:
  - externalKey: supplier-42
    actual: {finish: 2026-04-18}
""",
        "actual-intake-batch-v0.1.schema.yaml",
    )
    assert value["records"][0]["actual"]["finish"] == "2026-04-18"
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
