# Diagnostic Actionability Design (#371)

## Decision

Diagnostic actionability remains owned by the product boundary that detects a
failed assertion.  Repository tooling measures and reports that ownership; it
does not format runtime diagnostics or introduce a second diagnostic model.

The existing bare-diagnostic policy changes atomically to a disposition model:

```yaml
- code: E_EXAMPLE
  disposition: sufficient | backlog
  reason: "..." # required only for sufficient
  nextAction: "..." # required only for backlog
```

`sufficient` means the identifier alone is the complete message at every
reachable bare site.  `backlog` is an explicit, non-exempted improvement item.
The generated inventory lists backlog codes with their reachable-site count and
next action before the complete source-site listing.  No legacy `reason`-only
entry remains.

## CLI reachability

The inventory derives module reachability from `chrona.app.cli` and
`chrona.__main__` using the import-resolution algorithm already used by the
module-reachability gate.  A construction is `user-facing-ingress` if its
module is reachable from either root; otherwise it is `internal`.  The report
retains the source path, but source directory is no longer a classification
authority.  Tool/conformance roots are excluded because they are maintainer
surfaces, not public product CLI ingress.

`presentation.model.projection` is therefore reachable through
`usecases.render_review`, and `E_ACTUAL_REQUIRED` enters the policy population.
The same rule deliberately expands the population beyond #370's 53
prefix-based codes: every CLI-reachable bare construction must be classified.
It is initially dispositioned explicitly unless its owning projection change
ships in the same slice.

## Detail ownership

The selected codes gain detail at their existing owners:

| Code | Owner | Required detail |
| --- | --- | --- |
| `E_CLOSURE_KIND` | closure/contract resolution | resource identity/reference, expected kind or contract type, found kind/type |
| `E_STORE_REFERENCE` | local reader and Project loader | reference identity/address, expected provider/store identity or Project kind, received/absent value |
| `E_MATERIALIZER_CONTEXT` | materializer closure-copy boundary | manifest/slide/context/reference location, expected closure member, found or missing value |

Details use the existing exception `detail` channel and are preserved by the
existing CLI failure adapter.  They do not expose host paths beyond an
author-provided reference address and do not derive alternative resource
resolution.  Repeated helpers are allowed only below the owner boundary; no
renderer or CLI-specific formatter may inspect closure/store/materializer
internals.

## Declared concurrency value

`baseRevision` in `apply_authoring_command` is `pinned-deliberately`: the
client asserts the revision it read.  Its producer remains `chrona workspace
revision`.  The policy correction makes the existing implementation and its
quality evidence agree; it does not alter compare-and-set behavior.

## Architecture review

| Boundary | Decision | Result |
| --- | --- | --- |
| Core/product diagnostics | Detector owns resource facts and constructs detail. | Preserved |
| Tool policy | Versioned conformance input only; no `src/chrona` runtime import. | Preserved |
| CLI | Public import roots classify reachability but do not own failure wording. | Preserved |
| Closure/store/materializer | Each retains its own reference semantics and detail vocabulary. | Preserved |
| Presentation | Reachability can reveal a user-visible projection error; no Layout/Scene/rendering responsibility changes. | Preserved |
| Identity | `baseRevision` stays an explicit immutable assertion with its existing producer. | Preserved |

Rejected alternatives are a directory-prefix ingress heuristic, generic
code-level detail injected by CLI, a policy allowlist with no backlog, and a
compatibility reader that changes a store error's meaning.

## Acceptance

- Policy validation rejects missing/unknown dispositions and invalid
  reason/next-action combinations; report output renders backlog separately.
- CLI graph reachability classifies `E_ACTUAL_REQUIRED` as user-facing.
- Each selected detail reports resource, expectation, and actual outcome in
  focused tests without a presentation or identity-policy change.
- The declared-value inventory records `baseRevision` as
  `pinned-deliberately` and validates its live producer.
