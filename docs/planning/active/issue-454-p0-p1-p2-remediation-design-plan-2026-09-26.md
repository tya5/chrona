# Design Plan — Priority-Board P0, P1, and P2 Remediation (#454)

**Board read:** #454 at 2026-09-26.  The board is reviewer-maintained; this
plan neither edits nor closes it.

## Scope and established facts

The preceding visible-fit and typography programme is complete: #400, #449,
and #410 closed with release review `39bcecdc`.  This plan covers the P0, P1,
and P2 work ordered by #454, not P3 or the Target-B expressiveness programme.

P0 defects are public-output correctness failures.  They must be corrected
before the Scene perceptibility gate (#446) establishes a baseline, so the
gate does not encode known defects as allowances.  P1 makes those corrections
structural and improves the invalid-input and CI feedback loops.  P2 starts
only after the public output used by the README is trustworthy.

The first design slice must audit current `main` against every issue's literal
acceptance list.  In particular, #410 introduced exact `(family, weight)`
catalog selection, so #448 must be classified as either already satisfied by
that public result or as the remaining draft `--system-fonts` multi-face
ingress work.  It must not be reimplemented from the historical problem
statement.

## Programme invariants

1. **Intent → Layout → Scene → adapter remains one-way.**  Layout owns
   geometry, host relationships, collision decisions, wrapping and text
   measurement.  Scene transports completed primitives and declared paint
   relations.  Adapters only serialize their supplied order and geometry.
2. **A paint relation is semantic data, not builder loop order.**  Text hosted
   by a mark or axis band declares its relative order before Scene projection.
   The Scene builder cannot infer or repair it.
3. **Presentation of a semantic value is finite and ingress-validated.**
   Boolean table data receives a declared finite representation; it is never
   converted with Python `str` at Layout or adapter time.
4. **Warnings and quality gates observe completed artifacts.**  The
   perceptibility checker reads Scene facts without rasterizer, font, or
   adapter-specific heuristics.  It does not replace Layout's local validity
   checks.
5. **Theme/Context closure remains reproducible.**  Contrast and font rules
   validate declared values or completed Scene paint at their proper boundary;
   no host-font or target fallback is introduced.
6. **No compatibility spelling preserves a rejected behaviour.**  Retired
   `diagnose` fit semantics, implicit text order, unformatted boolean text,
   and first-error-only presentation ingress may be removed atomically when
   their replacement is published.

## Design slices and dependency order

| Slice | Issues | Design decision to establish | Depends on | Publishable result |
| --- | --- | --- | --- | --- |
| D454-0 | all | Acceptance-to-current-state audit, existing-contract inventory, and generated-corpus baseline. | — | Audit and programme architecture review. |
| D454-1 | #439, #443 | Typed host-relative paint strata and cross-tier axis lane/collision ownership. | D454-0 | Axis/inside-label paint and rotated-lane design. |
| D454-2 | #435 | Closed boolean table presentation contract and migration of `missingActual`. | D454-0 | Boolean source presentation design. |
| D454-3 | #445 | Layout-owned wrapped side-panel text allocation, with completed bounds and explicit overflow disposition. | D454-0 | Detail-panel readability design. |
| D454-4 | #446 | Versioned Scene perceptibility findings, intentional host relation allowlist, CI and draft-warning integration. | D454-1–D454-3 | Perceptibility-gate design. |
| D454-5 | #451 | Non-short-circuit conformance reporting, stale-artifact diagnostics, independent test execution, and non-cancelling matrix. | D454-0 | CI feedback design. |
| D454-6 | #450 | Deterministically ordered aggregate schema and semantic presentation diagnostics. | D454-0 | Aggregate ingress-error design. |
| D454-7 | #438 | Literal issue-acceptance matrix and close-time disposition convention. | D454-0 | Review-template/process design. |
| D454-8 | #431 | Role-class composited-contrast contract, explicit absence, corpus palette migration, and report/gate relationship to #446. | D454-4 | Contrast-floor design. |
| D454-9 | #448 | Exact catalog acceptance audit; if needed, multi-face draft-system-font resolution without a default-face fallback. | D454-0 | Closure audit or residual system-font design. |
| D454-10 | #441 | Reachable corpus artifact topology and generated README hero contract. | D454-1 | ASTER cleanup design. |
| D454-11 | #376 | Minimal init source topology, explicit corpus example, hidden closure location, and executable beginner guide. | D454-0 and existing preset ingress | Minimal-init design. |
| D454-12 | #378 | Executable onboarding ladder assembled from minimal init, preset selection, bounded inheritance, and progressive guide examples. | D454-11 and shipped preset mechanisms | Onboarding architecture and implementation plan. |

The implementation order is D454-1, D454-2, D454-3, D454-4, D454-5 through
D454-9, then D454-10 through D454-12.  #451/#450/#438 may be implemented in
parallel *only after* their individual designs and architecture reviews have
been published; remote publication remains serial.

## Required design questions

### P0 visual and semantic correctness

- Define a finite paint-stratum relation for background decoration, marks,
  hosted text, and foreground annotations.  Identify the host from completed
  Layout placement rather than Scene list position, and decide how a text
  placement proves that its host relationship is intentional.
- Recompute rotated axis lane requirements from transformed text bounds and
  define one axis-label collision domain across tiers.  Preserve explicit
  visible-overflow policy without silently accepting ordinary intersections.
- Define boolean column presentation (`presence` or equivalent) at View
  ingress, including source/format compatibility, absent/present literals or
  icon semantics, accessibility text, and deterministic cell measurement.
- Decide wrapping/rail allocation for group detail and milestone digest as a
  Layout composition concern.  A new side-panel policy must not use target
  clipping or Scene-local line breaking.

### P1 structural prevention and feedback

- Specify exact Scene check inputs, paint compositing, tolerances, finding
  identities, intentional relation declarations, versioning, and ownership of
  baseline/allowlist data.  The gate must report *all* findings per corpus run
  and draft render must surface equivalent warning records without changing
  immutable evidence.
- Specify a conformance result protocol that collects every command outcome,
  preserves raw command output, produces bounded actionable stale-file diffs,
  and lets pytest run even when gates fail.  It must retain cross-platform
  coverage and avoid repeated local full-suite work.
- Define an aggregate diagnostic value and ordering rule that spans schema and
  independent semantic errors while preserving the old single-error text as
  the first item where callers require it.
- Make literal issue acceptance the authority for a release review.  A
  deferred/narrowed criterion is a recorded disposition, never a silently
  omitted row.
- Place contrast floors at the boundary with enough completed paint and ground
  information.  Distinguish required state text, optional decorations, and
  deliberately absent decoration; derive a checked per-purpose corpus report.
- Audit catalog-selected bold Scene identities and every draft-system-font
  request.  A residual fix may resolve multiple exact faces, but cannot select
  a neighbouring weight or allow an adapter to choose one.

### P2 reusable first-run experience

- Treat generated evidence, editable sources, and hidden revision/store
  machinery as distinct topologies.  README image references must be manifest
  reachable and reproducible.
- Define minimal-init files as editable user authority, with all defaults
  resolved through existing preset/closure contracts rather than copied
  HALCYON implementation detail.
- Treat the onboarding ladder as executable documentation.  Each rung must
  have a stable command sequence and source fixture; Theme/View inheritance,
  if still absent, requires its own design correction before implementation
  rather than enlarging the guided-authoring governance vocabulary.

## Verification and publication discipline

Each implementation slice names affected schemas, generated documents,
fixtures, and public materializers before code is written.  It runs focused
tests locally and batches regenerated public artifacts per slice.  Its release
gate is the existing three-OS CI full pytest/conformance/wheel/smoke matrix
plus the Python 3.12 public-materializer reproduction job; CI status is checked
only after a material change or expected completion, not polled repeatedly.

Before every serial push, fetch `origin/main`, compare the exact ahead/behind
state, review the staged diff and generated output, then publish one coherent
design, implementation, or acceptance unit.  Any discovered boundary breach
returns to the relevant design slice and architecture review before code
continues.
