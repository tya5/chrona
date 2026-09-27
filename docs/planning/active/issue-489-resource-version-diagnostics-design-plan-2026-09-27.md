# Design Plan — Actionable Unsupported Resource Versions (#489)

**Source of truth:** [Issue #489](https://github.com/tya5/chrona/issues/489), read on 2026-09-27. **Public baseline:** `be2ceb6d` on `main`; no #489 design or implementation is published. The issue's copied-preset reproduction is a report to verify, not an accepted local artifact.

## Baseline and scope

`contracts/resources.py` selects one schema by `(kind, version)` and currently turns an unsupported version into `E_CLOSURE_KIND ... found dict`. The contract exception reaches `closure.py` without a source pointer, so CLI render reports `/`. The resolver already knows the resource kind, id and found version. `chrona preset copy` creates a local `preset.yaml` identifying a builtin catalogue preset; copied View, Theme and Layout Profile resources can become stale. Specification 34 requires a stale resource to diagnose, not be upgraded; Specification 56 and #477 establish structured author-facing diagnostics and pointer propagation. No implicit compatibility path is in scope.

Published facts: the current schema registry supports View v0.26, Theme v0.11 and Layout Profile v0.9. Unverified until focused tests: whether every draft load path preserves a typed unsupported-version error and whether a stale file reached through a render context, rather than a preset copy, has equivalent diagnostics.

## Literal acceptance ledger

1. “Rendering a preset copy with an older View version fails with a code and message that name the found and supported versions, with `sourceRef: /version`."
2. “For a builtin preset copy, the message tells the user to re-run `chrona preset copy <id>`."
3. “A CLI test covers a stale View, a stale Theme and a stale Layout Profile."

## Use cases and decisions to settle

- A copied builtin preset has an old View, Theme or Layout Profile: refuse it with the found/supported version, resource kind/id, resource-local `/version` pointer and an actionable copy-again remedy.
- An independently supplied or non-builtin resource is stale: refuse it with the same structured version evidence, but do not invent a builtin-copy command. Decide which stable specification or migration note the message should cite.
- A malformed or missing version, a wrong resource kind, or a schema-invalid *supported* version is not necessarily the same fault as an unsupported version. Define the diagnostic split and precedence without changing existing validation behavior accidentally.
- Decide where provenance is carried: the contract layer owns version detection, closure owns resource-path propagation, and the CLI owns command wording. A generic contract exception must not infer `chrona preset copy` from a resource id alone.
- Decide whether one supported version or a set is rendered in the message, derived from the registry rather than a duplicated constant.

## Design slices and reviews

1. **D489-1 — Version diagnostic contract.** Specify error identity, fields, `/version`, supported-version enumeration, malformed-version behavior and propagation through both single-resource and aggregate schema paths. Review against Specifications 34 and 56, #477's pointer fix, and the no-compatibility policy.
2. **D489-2 — Provenance and remedy.** Trace `chrona render --preset` through copy, draft closure and CLI. Define what evidence proves a builtin copy and the exact remedy; define generic-resource behavior. Review against preset package ownership and CLI override semantics.
3. **D489-3 — Whole-architecture review.** Check that resource contracts stay unaware of CLI commands, closure preserves structured evidence, CLI only presents it, no adapter/layout/scheduler behavior changes, and a stale version never silently renders. Publish the design and review before implementation planning.

## Implementation and acceptance evidence to plan after design

Separate contract/closure propagation from CLI-remedy publication if each can be independently tested and published without an unactionable interim diagnostic. Focused tests must exercise stale View, Theme and Layout Profile through the public CLI, a non-builtin stale resource, malformed version handling, and version refusal without implicit upgrade. Verify the current builtin preset copies still render, unaffected public materializers remain byte-identical, then use the CI matrix for full pytest/conformance. The final release review must repeat all three literal acceptance rows with direct output and CI evidence.
