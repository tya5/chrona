# Issue #50 closure-integrity remediation design plan

## Trigger

External verification in Issue #50 established that the #49 semantic presentation-contract
refactor is structurally exercised, but not yet closed. It found three residual classes:

1. Scene fixtures omit a required `title` measurement and therefore fail with a bare
   `KeyError`;
2. three checked-in HALCYON contexts contain stale opt-in `contentIdentity` values; and
3. the public materializer rewrites authored references and font asset identities before the
   reader can validate them.

PR #51 refreshes generated SVG evidence only. It does not establish that the authored
immutable closures are self-consistent.

## Scope

This design closes the boundary from checked-in authored context to materialized evidence,
and the two directly exposed contract gaps in the Scene and snapshot tests. It does not
restore the deleted Settings/Theme contract, introduce mutable source resolution, or permit
hand-authored generated SVGs.

## Design sequence

1. Define authored-closure preservation and validation semantics.
2. Define the materializer's derived execution closure and provenance output.
3. Define mandatory measurement diagnostics and fixture obligations.
4. Record the distinct return contracts for snapshot documents and snapshot references.
5. Review the changes against Revision Store, Presentation Closure, Scene, evidence, and
   public CLI ownership.
6. Publish the implementation plan only after every decision is closed.

## Completion criteria

- An authored pin mismatch fails materialization in both check and `--write` modes.
- The copied context bytes are exactly the authored bytes; no YAML re-dump alters them.
- Font-asset pins are verified and never rewritten.
- Generated SVGs remain exclusively public-materializer output and reproduce byte-for-byte.
- Missing required measurements produce `E_PRESENTATION_MEASUREMENTS_REQUIRED`, never a
  language-level lookup exception.
- Tests assert snapshot references as flat resource references and snapshot documents as
  documents with `body`.
