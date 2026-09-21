# M26 Existing Contract Matrix — 2026-09-21

**Status:** Design evidence for M26; no product implementation is authorized by this
document.

## 1. Decision

UC-10, UC-11, and UC-12 will share one immutable-reference and compare-and-set path.
The existing v0.1 command document remains readable evidence for its already released
scope, but it is not extended. M26 introduces a successor command document and removes
the raw-path `propose-set` product surface when that successor is implemented.

External intake accepts a normalized, self-contained batch. Connector-specific parsing,
authentication, and fetching remain outside Chrona. A batch preserves source
provenance but gives no parser a hidden authority to select a Project or store tip.

## 2. Source-of-truth matrix

| Use case | Existing contract | Deficiency | M26 owning replacement |
|---|---|---|---|
| UC-10 intake | `presentation.model.actual_intake` converts already-parsed records and rejects non-exact Project IDs; Actual commands only have an in-memory CAS adapter | no persisted batch resource, replay identity, intake command, report, or CLI | `35` operational workflow specification; `actual-intake-batch/v0.1`; command v0.2 |
| UC-10 reconcile | `resolveActualObservation` only accepts a stable Project ID and preserves external identity | no operational request/result or deterministic import state | same command v0.2 request/result; exact-ID resolution remains the only reconciliation path |
| UC-11 automation | command v0.1 has a target path plus a separate revision string; `propose-set` reads a raw path and does not persist | the path can denote mutable working-tree state and no machine result closure exists | command v0.2 immutable `target` reference plus `automation-result/v0.1` and `command-check`/`command-apply` |
| UC-12 capture | `capture_snapshot` checks a project reference and publishes to an in-memory append-only store | no durable registry adapter or CLI contract | snapshot-ref v0.2, immutable resource registry protocol, `baseline-capture` |
| UC-12 compare | `review` accepts two project references; snapshot resources can name a Project | named baseline loading and result provenance are not a product contract | `baseline-compare`, which resolves a snapshot-ref and explicit candidate closure before semantic comparison |

## 3. Compatibility and replacement rules

1. `chrona/command/v0.1` remains valid only for its published legacy registry. M26
   MUST NOT add a v0.2 operation to it or reinterpret its `path` field as immutable.
2. `chrona/command/v0.2` is the sole input accepted by M26 automation commands. Its
   target is a complete `revision-store-resource-ref/v0.1`, and its base revision and
   content identity must agree with that reference.
3. The `propose-set` CLI command is removed, not retained as a compatibility alias.
   `command-check` gives a non-mutating validation result; `command-apply` is the only
   mutation path and delegates the declared CAS write to the named Store.
4. A batch deduplication key is `(source.system, externalKey)`. Replaying an identical
   observation is accepted as a no-op; changing its Actual content or source content
   identity is a conflict requiring an explicit edit command. Chrona never guesses a
   Project identity from a title.
5. A named baseline is append-only. Reusing its ID rejects, even if it would name the
   same Project bytes. Comparing a baseline resolves the stored immutable Project
   reference; it never substitutes a current branch, directory, or clock.

## 4. Required acceptance states

| Operation | Accepted | No-op | Rejected without write |
|---|---|---|---|
| Intake batch | one new Actual-set revision and intake report | all records match existing external facts exactly | duplicate input key, source mismatch, missing immutable target, conflicting fact, or invalid Project ID |
| Resolve observation | one new Actual-set revision | none | stale target, unknown observation/object, or observation not unmatched |
| Apply automation | declared Store produces exactly one new immutable revision | recorded identical request is returned as replay | stale revision/content identity, unknown operation, schema error, failed validation, or CAS conflict |
| Capture baseline | exactly one readable baseline reference | none | stale project, mutable reference, existing ID, or registry publication failure |
| Compare baseline | one deterministic report with both closures | none | unreadable/mismatched baseline or candidate closure |

## 5. Deliberate exclusions

M26 does not prescribe source connectors, automatic entity matching, persisted command
history retention policy, hosted CI credentials, or a generic filesystem mutation API.
Those concerns must be separately designed before becoming product behavior.
