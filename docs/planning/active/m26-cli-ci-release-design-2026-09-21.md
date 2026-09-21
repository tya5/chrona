# M26 CLI/CI Release Design — 2026-09-21

**Status:** Design complete; implementation is not authorized by this document.

## 1. Invocation and result contract

Every M26 CLI command takes exactly one explicit output destination, `--result PATH`.
The path must not exist. The process writes canonical JSON to a sibling temporary file,
flushes it where the platform supports flushing, and renames it to `PATH` once. A
failure before rename leaves no claimed result; an existing path rejects with
`E_AUTOMATION_OUTPUT_EXISTS` and exit `2`.

| Command | Required flags | Store permission | Exit 0 | Exit 2 |
|---|---|---|---|---|
| `command-check` | `--command`, `--store-config`, `--result` | read | valid non-mutating request | schema/closure/policy rejection |
| `command-apply` | `--command`, `--store-config`, `--result` | CAS write to target | accepted mutation or exact replay | stale/invalid/conflict rejection |
| `actual-intake` | same as apply | CAS write to Actual-set | accepted intake or exact replay | invalid batch/conflict/reconciliation rejection |
| `actual-resolve` | same as apply | CAS write to Actual-set | accepted resolution | invalid alignment/reference/conflict |
| `baseline-capture` | same as apply, `--baseline-registry` | registry create-if-absent | one new named baseline | pre-existing ID/invalid target/publish rejection |
| `baseline-compare` | `--baseline-reference`, `--candidate-reference`, `--store-config`, `--result` | read | verified semantic report | unreadable/mismatched closure |

Exit `3` is reserved for inability to read a requested local request/result file or
atomically publish the result after a command outcome is known. It is not a validation
or conflict response. Usage errors exit `64` before the operation begins and do not
claim a result.

## 2. CI containment

CI provides an immutable command/baseline/candidate document and Store configuration.
The configuration maps a declared `store.provider` and `store.identity` to an adapter;
it cannot replace a command's identity, address, revision, or digest. Environment
variables may supply adapter credentials but are never copied into a result. A CI job
must not use a default working directory, Git `HEAD`, branch name, or local clock to
fill any identity field.

The first product profile defines `chrona/store-config/v0.1`: a non-empty list of
unique `provider: local`, `identity`, and `root` mappings. It contains no credentials.
The selected entry must exactly match each resource reference's provider and identity;
unknown/duplicate mappings reject before reads or writes.

A writable local Actual Store uses immutable `<root>/<token>/actuals/<id>.yaml`
resources and an adapter-owned `actual-tips/<id>.json` CAS pointer. The pointer is not
a resource reference and cannot be supplied by CI; the command's target token is the
only expected-write value.

```yaml
name: chrona-baseline-review
steps:
  - run: chrona baseline-compare
      --baseline-reference ci/baselines/q2.ref.yaml
      --candidate-reference ci/refs/release-42.ref.yaml
      --store-config ci/stores.yaml
      --result out/baseline-review.json
  - run: test -s out/baseline-review.json
```

The example's files are transport locations only. Their parsed contents supply the
immutable closure. A job may upload the result as an artifact, but upload status does
not change Chrona's command result.

## 3. Observability and diagnostics

Results must include: operation, request content identity (or a synthesized canonical
comparison request identity), status, input closure, ordered diagnostics, artifact
references, and mutation target when accepted. Intake adds record dispositions;
comparison adds a deterministic semantic diff. Human console lines may summarize those
fields but cannot add undocumented diagnostics or change exit status.

The CLI redacts values identified by the adapter as credentials before any diagnostic
or JSON serialization. Source `locator` is retained only as the opaque audit string
already supplied in a batch and is never dereferenced.

## 4. Acceptance matrix

| ID | Scenario | Required proof |
|---|---|---|
| A26-01 | same intake is retried | second result is accepted replay/no-op; Actual-set revision unchanged |
| A26-02 | same external key has new observed fields | rejection, no Actual-set revision, `E_ACTUAL_EXTERNAL_CONFLICT` |
| A26-03 | unrecognized Project object is supplied | unmatched observation or explicit resolve rejection; no title matching |
| A26-04 | command target changes after inspection | `E_AUTOMATION_TARGET_CLOSURE` or base-revision rejection; no write |
| A26-05 | command ID is reused with different bytes | `E_COMMAND_ID_REUSE`; no write |
| A26-06 | result destination already exists | exit 2, original file unchanged |
| A26-07 | baseline ID exists | exit 2, existing baseline bytes unchanged |
| A26-08 | baseline/candidate are from different stores | accepted only when both complete references verify |
| A26-09 | CI has no checkout or `HEAD` | check/apply/compare work solely from configured immutable Stores |
| A26-10 | injected credentials appear in adapter config | result/diagnostics contain no credential value |

## 5. Release claim

M26 may claim UC-10, UC-11, and UC-12 only after all A26-01 through A26-10 have
automated evidence, schemas are registered in conformance, the legacy `propose-set`
surface is absent, and the final acceptance review confirms the result closure is
complete. This is an additive operational release; it makes no new GUI, connector,
renderer, or scheduling claim.
